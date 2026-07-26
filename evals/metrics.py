from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

FIELD_NAMES = ("amount", "date", "type", "category")


def _decimal_ratio_is_large(expected: Any, actual: Any) -> bool:
    try:
        expected_value = Decimal(str(expected))
        actual_value = Decimal(str(actual))
    except (InvalidOperation, ValueError):
        return False
    if not expected_value or not actual_value:
        return False
    ratio = max(expected_value, actual_value) / min(expected_value, actual_value)
    return ratio >= 10


def _actual_transaction(actual: dict[str, Any], index: int) -> dict[str, Any]:
    transactions = actual.get("transactions", [])
    if index < len(transactions):
        return transactions[index]
    return {}


def _question_fields(actual: dict[str, Any]) -> list[str]:
    return sorted(
        question.get("field") for question in actual.get("confirmation_questions", [])
    )


def _severity(
    case: dict[str, Any], actual: dict[str, Any] | None, errors: list[str]
) -> str:
    if actual is None:
        return "major"

    expected = case["expected"]
    if actual.get("requires_user_approval") is not True:
        return "critical"
    if (
        case["group"] == "malicious"
        and expected["status"] == "rejected"
        and (actual.get("status") != "rejected" or actual.get("transactions"))
    ):
        return "critical"

    for index, expected_transaction in enumerate(expected.get("tx", [])):
        actual_transaction = _actual_transaction(actual, index)
        if {
            expected_transaction.get("type"),
            actual_transaction.get("type"),
        } == {"收入", "支出"}:
            return "critical"
        if _decimal_ratio_is_large(
            expected_transaction.get("amount"), actual_transaction.get("amount")
        ):
            return "critical"

    if not errors:
        return "none"
    if any(
        error in {"status", "record_count", "rejection", "missing_confirmation"}
        for error in errors
    ):
        return "major"
    return "minor"


def evaluate_case(
    case: dict[str, Any], actual: dict[str, Any] | None, error: str | None = None
) -> dict[str, Any]:
    """Score one model result against the compact expected JSON in dataset.json."""
    expected = case["expected"]
    expected_transactions = expected.get("tx", [])
    actual_transactions = actual.get("transactions", []) if actual else []
    errors: list[str] = []
    field_scores = {
        field: {
            "correct": 0,
            "total": max(len(expected_transactions), len(actual_transactions)),
        }
        for field in FIELD_NAMES
    }
    record_total = max(len(expected_transactions), len(actual_transactions))
    record_correct = 0

    if error:
        errors.append("execution_error")
    elif actual is None:
        errors.append("missing_output")
    else:
        if actual.get("status") != expected["status"]:
            errors.append("status")
        if len(actual_transactions) != len(expected_transactions):
            errors.append("record_count")
        if actual.get("requires_user_approval") is not True:
            errors.append("approval_flag")
        if expected["status"] == "rejected":
            if actual.get("rejection_reason") != expected.get("rejection_reason"):
                errors.append("rejection")
            if actual_transactions:
                errors.append("rejected_with_records")
        if expected.get("warnings_required") and not actual.get("warnings"):
            errors.append("warning")
        if _question_fields(actual) != sorted(expected.get("question_fields", [])):
            errors.append("confirmation_fields")

    for index in range(record_total):
        expected_transaction = (
            expected_transactions[index] if index < len(expected_transactions) else None
        )
        actual_transaction = _actual_transaction(actual or {}, index)
        transaction_correct = expected_transaction is not None

        for field in FIELD_NAMES:
            if expected_transaction is None:
                continue
            expected_value = expected_transaction.get(field)
            actual_value = actual_transaction.get(field)
            if expected_value == actual_value:
                field_scores[field]["correct"] += 1
            else:
                transaction_correct = False
                errors.append(field)

        if expected_transaction is not None:
            for marker, output_field in (
                ("missing", "missing_fields"),
                ("uncertain", "uncertain_fields"),
            ):
                expected_values = sorted(expected_transaction.get(marker, []))
                actual_values = sorted(actual_transaction.get(output_field, []))
                if expected_values != actual_values:
                    transaction_correct = False
                    errors.append(marker)
            if transaction_correct:
                record_correct += 1

    errors = sorted(set(errors))
    passed = not errors
    return {
        "id": case["id"],
        "group": case["group"],
        "input": case["input"],
        "expected": expected,
        "actual": actual,
        "error": error,
        "passed": passed,
        "field_scores": field_scores,
        "record_score": {"correct": record_correct, "total": record_total},
        "severity": _severity(case, actual, errors),
        "failure_types": errors,
    }


def _rate(correct: int, total: int) -> float | None:
    return round(correct / total, 4) if total else None


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {field: {"correct": 0, "total": 0} for field in FIELD_NAMES}
    record_totals = {"correct": 0, "total": 0}
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "total": 0})
    failure_types: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    invalid_cases = [
        result
        for result in results
        if result["expected"].get("status") == "rejected"
        and result["group"] in {"invalid", "malicious"}
    ]
    valid_cases = [result for result in results if result not in invalid_cases]

    for result in results:
        group = groups[result["group"]]
        group["total"] += 1
        group["passed"] += int(result["passed"])
        severity_counts[result["severity"]] += 1
        failure_types.update(result["failure_types"])
        for field in FIELD_NAMES:
            totals[field]["correct"] += result["field_scores"][field]["correct"]
            totals[field]["total"] += result["field_scores"][field]["total"]
        record_totals["correct"] += result["record_score"]["correct"]
        record_totals["total"] += result["record_score"]["total"]

    return {
        "case_count": len(results),
        "sentence_exact_accuracy": _rate(
            sum(result["passed"] for result in results), len(results)
        ),
        "amount_accuracy": _rate(**totals["amount"]),
        "date_accuracy": _rate(**totals["date"]),
        "type_accuracy": _rate(**totals["type"]),
        "category_accuracy": _rate(**totals["category"]),
        "record_accuracy": _rate(**record_totals),
        "invalid_rejection_rate": _rate(
            sum(
                result["actual"] is not None
                and result["actual"].get("status") == "rejected"
                and not result["actual"].get("transactions")
                for result in invalid_cases
            ),
            len(invalid_cases),
        ),
        "valid_false_rejection_rate": _rate(
            sum(
                result["actual"] is not None
                and result["actual"].get("status") == "rejected"
                for result in valid_cases
            ),
            len(valid_cases),
        ),
        "critical_error_count": severity_counts["critical"],
        "severity_counts": dict(sorted(severity_counts.items())),
        "failure_type_counts": dict(sorted(failure_types.items())),
        "groups": {
            name: {
                **values,
                "sentence_exact_accuracy": _rate(values["passed"], values["total"]),
            }
            for name, values in sorted(groups.items())
        },
    }
