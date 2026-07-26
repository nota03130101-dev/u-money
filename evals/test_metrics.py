from evals.metrics import evaluate_case, summarize


def test_evaluate_case_scores_all_fields() -> None:
    case = {
        "id": "T01",
        "group": "normal",
        "input": "合成输入",
        "expected": {
            "status": "success",
            "tx": [
                {
                    "date": "2026-07-26",
                    "type": "支出",
                    "amount": "32.00",
                    "category": "餐饮",
                }
            ],
        },
    }
    actual = {
        "status": "success",
        "requires_user_approval": True,
        "transactions": [
            {
                "date": "2026-07-26",
                "type": "支出",
                "amount": "32.00",
                "category": "餐饮",
                "missing_fields": [],
                "uncertain_fields": [],
            }
        ],
        "confirmation_questions": [],
    }

    result = evaluate_case(case, actual)

    assert result["passed"] is True
    assert result["record_score"] == {"correct": 1, "total": 1}
    assert all(score["correct"] == 1 for score in result["field_scores"].values())


def test_malicious_non_rejection_is_critical() -> None:
    case = {
        "id": "T02",
        "group": "malicious",
        "input": "合成恶意输入",
        "expected": {
            "status": "rejected",
            "tx": [],
            "rejection_reason": "UNSAFE_INPUT",
        },
    }
    actual = {
        "status": "success",
        "requires_user_approval": True,
        "transactions": [
            {"date": "2026-07-26", "type": "支出", "amount": "1.00", "category": "餐饮"}
        ],
        "confirmation_questions": [],
        "rejection_reason": None,
    }

    assert evaluate_case(case, actual)["severity"] == "critical"


def test_summary_reports_invalid_rejection_rate() -> None:
    rejected = {
        "id": "T03",
        "group": "invalid",
        "input": "无关内容",
        "expected": {
            "status": "rejected",
            "tx": [],
            "rejection_reason": "UNRELATED_INPUT",
        },
    }
    actual = {
        "status": "rejected",
        "requires_user_approval": True,
        "transactions": [],
        "confirmation_questions": [],
        "rejection_reason": "UNRELATED_INPUT",
    }

    summary = summarize([evaluate_case(rejected, actual)])

    assert summary["invalid_rejection_rate"] == 1.0
