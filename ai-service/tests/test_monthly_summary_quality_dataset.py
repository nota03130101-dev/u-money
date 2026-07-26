import json
from pathlib import Path

from app.models import MonthlySummaryRequest

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "evals" / "monthly_summary_dataset.json"
FORBIDDEN_INPUT_KEYS = {"records", "record", "note", "notes", "user_id", "email"}


def load_dataset() -> dict:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(collect_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(collect_keys(child))
        return keys
    return set()


def test_quality_dataset_has_small_unique_synthetic_set() -> None:
    dataset = load_dataset()
    cases = dataset["cases"]
    ids = [case["id"] for case in cases]

    assert dataset["prompt_version"] == "monthly-summary-v1"
    assert 5 <= len(cases) <= 10
    assert len(ids) == len(set(ids))
    assert "虚构" in dataset["description"]


def test_each_quality_input_matches_backend_contract() -> None:
    for case in load_dataset()["cases"]:
        request = MonthlySummaryRequest.model_validate(case["input"])
        expected = case["expected_quality"]
        categories = request.expense_categories

        assert FORBIDDEN_INPUT_KEYS.isdisjoint(collect_keys(case["input"]))
        assert expected["largest_category"] == (
            categories[0].category if categories else None
        )
        assert (
            expected["change_observation_required"]
            == request.comparison.available
        )


def test_each_quality_case_inherits_global_safety_checks() -> None:
    dataset = load_dataset()
    checks = " ".join(dataset["global_quality_checks"])

    assert "不输出或重新计算数字" in checks
    assert "不提供投资、贷款、保险或医疗建议" in checks
    assert "不使用恐吓、羞辱" in checks
    assert "不声称了解汇总数据之外的信息" in checks
