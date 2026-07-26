import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(mock_mode=True, max_text_length=1000)))


def headers() -> dict[str, str]:
    return {"Authorization": "Bearer mock-test-token"}


def parse(client: TestClient, text: str, reference_date: str = "2026-07-26"):
    return client.post(
        "/ai/parse-transactions",
        headers=headers(),
        json={
            "text": text,
            "reference_date": reference_date,
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
        },
    )


def test_health() -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_requires_login_token() -> None:
    response = make_client().post(
        "/ai/parse-transactions",
        json={"text": "今天午饭 32 元", "reference_date": "2026-07-26"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_single_expense_today() -> None:
    response = parse(make_client(), "今天午饭 32 元")
    payload = response.json()
    assert response.status_code == 200
    assert payload["requires_user_approval"] is True
    assert payload["transactions"][0]["date"] == "2026-07-26"
    assert payload["transactions"][0]["amount"] == "32.00"


def test_multiple_expenses_yesterday() -> None:
    response = parse(make_client(), "昨天午饭 32 元，坐地铁 4 元")
    payload = response.json()
    assert response.status_code == 200
    assert len(payload["transactions"]) == 2
    assert {item["category"] for item in payload["transactions"]} == {"餐饮", "交通"}
    assert all(item["date"] == "2026-07-25" for item in payload["transactions"])


def test_income_with_explicit_date() -> None:
    response = parse(make_client(), "2026年7月20日收到工资 8000 元")
    transaction = response.json()["transactions"][0]
    assert response.status_code == 200
    assert transaction["type"] == "收入"
    assert transaction["date"] == "2026-07-20"
    assert transaction["amount"] == "8000.00"


def test_decimal_amount() -> None:
    response = parse(make_client(), "今天咖啡 12.5 元")
    assert response.status_code == 200
    assert response.json()["transactions"][0]["amount"] == "12.50"


def test_missing_amount_needs_confirmation() -> None:
    response = parse(make_client(), "今天午饭")
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "needs_confirmation"
    assert payload["transactions"][0]["amount"] is None
    assert payload["confirmation_questions"][0]["field"] == "amount"


def test_ambiguous_category_needs_confirmation() -> None:
    response = parse(make_client(), "今天花了 20 元")
    payload = response.json()
    assert response.status_code == 200
    assert payload["transactions"][0]["category"] is None
    assert payload["confirmation_questions"][0]["field"] == "category"


def test_unrelated_input_is_rejected() -> None:
    response = parse(make_client(), "今天天气怎么样")
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "rejected"
    assert payload["transactions"] == []


def test_too_long_input_is_rejected() -> None:
    response = parse(make_client(), "记账" * 600)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_model_timeout_returns_clear_error() -> None:
    response = parse(make_client(), "__timeout__")
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "MODEL_TIMEOUT"


def test_invalid_model_json_is_not_converted_to_records() -> None:
    response = parse(make_client(), "__invalid_json__")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MODEL_INVALID_OUTPUT"


def test_parse_rate_limit_is_enforced() -> None:
    settings = Settings(
        mock_mode=True,
        parse_per_minute_limit=2,
        parse_per_day_limit=10,
    )
    client = TestClient(create_app(settings))

    assert parse(client, "今天午饭 32 元").status_code == 200
    assert parse(client, "今天午饭 32 元").status_code == 200

    response = parse(client, "今天午饭 32 元")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "PARSE_RATE_LIMITED"


def test_ai_response_is_not_cacheable() -> None:
    response = parse(make_client(), "今天午饭 32 元")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_production_rejects_mock_mode() -> None:
    with pytest.raises(ValueError, match="MOCK_MODE=false"):
        create_app(Settings(app_environment="production", mock_mode=True))
