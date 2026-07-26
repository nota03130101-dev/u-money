from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models import MonthlySummaryRequest


def valid_payload() -> dict:
    return {
        "month": "2026-07",
        "statistics_period_start": "2026-07-01",
        "statistics_period_end": "2026-07-31",
        "currency": "CNY",
        "totals": {
            "income": "8000.00",
            "expense": "1200.00",
            "balance_change": "6800.00",
            "record_count": 4,
        },
        "expense_categories": [
            {"category": "餐饮", "amount": "600.00", "percentage": 50.0},
            {"category": "交通", "amount": "600.00", "percentage": 50.0},
        ],
        "comparison": {
            "previous_month": "2026-06",
            "available": True,
            "income_change": "500.00",
            "expense_change": "-100.00",
            "balance_change": "600.00",
        },
    }


def test_valid_monthly_summary_input_is_accepted() -> None:
    request = MonthlySummaryRequest.model_validate(valid_payload())

    assert request.month == "2026-07"
    assert request.totals.balance_change == request.totals.income - request.totals.expense
    assert len(request.expense_categories) == 2


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"month": "2026-13"}, "month"),
        ({"statistics_period_start": "2026-07-02"}, "统计时间"),
        ({"statistics_period_end": "2026-08-01"}, "统计时间"),
        ({"currency": "USD"}, "currency"),
        ({"totals.balance_change": "6700.00"}, "余额变化"),
        ({"expense_categories.0.amount": "500.00"}, "类别支出合计"),
        ({"expense_categories.0.percentage": 40.0}, "百分比"),
        ({"comparison.previous_month": "2026-05"}, "上一个月"),
        ({"comparison.expense_change": None}, "必须提供变化值"),
    ],
)
def test_inconsistent_summary_input_is_rejected(
    change: dict[str, object], message: str
) -> None:
    data = valid_payload()
    path, value = next(iter(change.items()))
    target = data
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[int(part)] if part.isdigit() else target[part]
    target[parts[-1]] = value

    with pytest.raises(ValidationError, match=message):
        MonthlySummaryRequest.model_validate(data)


def test_unavailable_comparison_cannot_contain_change_values() -> None:
    data = valid_payload()
    data["comparison"] = {
        "previous_month": "2026-06",
        "available": False,
        "income_change": "0.00",
        "expense_change": "0.00",
        "balance_change": "0.00",
    }

    with pytest.raises(ValidationError, match="不能提供变化值"):
        MonthlySummaryRequest.model_validate(data)


def test_empty_month_requires_zero_totals_and_no_categories() -> None:
    data = valid_payload()
    data["totals"]["record_count"] = 0

    with pytest.raises(ValidationError, match="没有记录"):
        MonthlySummaryRequest.model_validate(data)


def test_duplicate_categories_are_rejected() -> None:
    data = valid_payload()
    data["expense_categories"][1]["category"] = "餐饮"

    with pytest.raises(ValidationError, match="类别不能重复"):
        MonthlySummaryRequest.model_validate(data)


def test_full_records_and_identity_fields_are_rejected() -> None:
    for forbidden_field in ("records", "notes", "user_id", "email"):
        data = deepcopy(valid_payload())
        data[forbidden_field] = ["不应发送的完整账单"]

        with pytest.raises(ValidationError, match="Extra inputs"):
            MonthlySummaryRequest.model_validate(data)
