from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app
from app.models import MonthlySummaryText


def make_client() -> TestClient:
    return TestClient(create_app(Settings(mock_mode=True)))


def headers() -> dict[str, str]:
    return {"Authorization": "Bearer mock-test-token"}


def payload(record_count: int = 3) -> dict:
    if record_count == 0:
        return {
            "month": "2026-07",
            "statistics_period_start": "2026-07-01",
            "statistics_period_end": "2026-07-31",
            "currency": "CNY",
            "totals": {
                "income": "0.00",
                "expense": "0.00",
                "balance_change": "0.00",
                "record_count": 0,
            },
            "expense_categories": [],
            "comparison": {
                "previous_month": "2026-06",
                "available": False,
                "income_change": None,
                "expense_change": None,
                "balance_change": None,
            },
        }

    return {
        "month": "2026-07",
        "statistics_period_start": "2026-07-01",
        "statistics_period_end": "2026-07-31",
        "currency": "CNY",
        "totals": {
            "income": "8000.00",
            "expense": "1200.00",
            "balance_change": "6800.00",
            "record_count": record_count,
        },
        "expense_categories": [
            {"category": "餐饮", "amount": "600.00", "percentage": 50.0},
            {"category": "交通", "amount": "600.00", "percentage": 50.0},
        ],
        "comparison": {
            "previous_month": "2026-06",
            "available": True,
            "income_change": "0.00",
            "expense_change": "100.00",
            "balance_change": "-100.00",
        },
    }


def test_monthly_summary_returns_safe_mock_draft() -> None:
    response = make_client().post("/ai/monthly-summary", headers=headers(), json=payload())
    body = response.json()

    assert response.status_code == 200
    assert body["data_status"] == "available"
    assert body["prompt_version"] == "monthly-summary-v1"
    assert body["summary"]["largest_category_observation"] == "支出主要集中在餐饮类别。"
    assert "1200" not in " ".join(value for value in body["summary"].values() if value)


def test_monthly_summary_without_records_skips_ai() -> None:
    response = make_client().post("/ai/monthly-summary", headers=headers(), json=payload(0))
    body = response.json()

    assert response.status_code == 200
    assert body["data_status"] == "empty"
    assert body["summary"] is None


def test_monthly_summary_rate_limit_is_enforced() -> None:
    client = make_client()
    for _ in range(3):
        assert client.post("/ai/monthly-summary", headers=headers(), json=payload()).status_code == 200

    response = client.post("/ai/monthly-summary", headers=headers(), json=payload())

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "SUMMARY_RATE_LIMITED"


def test_monthly_summary_text_rejects_restricted_advice() -> None:
    with pytest.raises(ValidationError):
        MonthlySummaryText(
            overview="本月统计已整理。",
            largest_category_observation=None,
            change_observation=None,
            neutral_observation="这份内容只根据汇总数据生成。",
            suggestion="建议投资股票。",
        )


def test_monthly_summary_allows_factual_insurance_category() -> None:
    summary = MonthlySummaryText(
        overview="本月统计已整理。",
        largest_category_observation="保险是本月最大的支出类别。",
        change_observation=None,
        neutral_observation="这份内容只根据汇总数据生成。",
        suggestion=None,
    )

    assert summary.largest_category_observation == "保险是本月最大的支出类别。"


def test_monthly_totals_are_decimal_values() -> None:
    assert Decimal(payload()["totals"]["expense"]) == Decimal("1200.00")
