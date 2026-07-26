from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE = ROOT / "ai-service"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AI_SERVICE))

from app.config import Settings
from app.errors import ServiceError
from app.model_client import ModelClient
from app.models import ParseTransactionsRequest

from evals.metrics import evaluate_case, summarize


def load_dataset(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def prompt_sha256() -> str:
    prompt_path = ROOT / "prompts" / "transaction-parser.md"
    return hashlib.sha256(prompt_path.read_bytes()).hexdigest()


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    rows = [
        "# U Money 自然语言记账评测报告",
        "",
        f"- 运行模式：{report['mode']}",
        f"- 模型：{report['model_name']}",
        f"- Prompt 版本：{', '.join(report['prompt_versions']) or '未返回'}",
        f"- 数据集：{report['dataset_version']}，共 {summary['case_count']} 条合成样例",
        f"- 运行时间：{report['started_at']}",
        "",
        "## 总体结果",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
    ]
    for label, key in (
        ("整句完全正确率", "sentence_exact_accuracy"),
        ("金额准确率", "amount_accuracy"),
        ("日期准确率", "date_accuracy"),
        ("类型准确率", "type_accuracy"),
        ("类别准确率", "category_accuracy"),
        ("整条记录准确率", "record_accuracy"),
        ("无效输入拒绝率", "invalid_rejection_rate"),
        ("有效输入误拒绝率", "valid_false_rejection_rate"),
    ):
        value = summary[key]
        rows.append(f"| {label} | {'不适用' if value is None else f'{value:.2%}'} |")
    rows.extend(
        [
            f"| 严重错误数 | {summary['critical_error_count']} |",
            "",
            "## 分组结果",
            "",
            "| 组别 | 通过 / 总数 | 整句完全正确率 |",
            "|---|---:|---:|",
        ]
    )
    for name, group in summary["groups"].items():
        rows.append(
            f"| {name} | {group['passed']} / {group['total']} | "
            f"{group['sentence_exact_accuracy']:.2%} |"
        )
    rows.extend(
        [
            "",
            "## 失败案例",
            "",
            "| ID | 组别 | 严重程度 | 失败类型 |",
            "|---|---|---|---|",
        ]
    )
    failures = [result for result in report["cases"] if not result["passed"]]
    for result in failures:
        failure_types = ", ".join(result["failure_types"]) or "未知"
        rows.append(
            f"| {result['id']} | {result['group']} | {result['severity']} | {failure_types} |"
        )
    if not failures:
        rows.append("| 无 | - | - | - |")
    rows.extend(
        [
            "",
            "## 结论",
            "",
            (
                "本报告只给出当前版本的基线结果，不会自动修改 Prompt。"
                "请先阅读失败案例和严重错误，再决定是否进行 Prompt 优化。"
            ),
            "",
        ]
    )
    return "\n".join(rows)


async def run_evaluation(dataset: dict[str, Any], settings: Settings) -> dict[str, Any]:
    client = ModelClient(settings)
    results: list[dict[str, Any]] = []
    prompt_versions: set[str] = set()
    started_at = datetime.now(timezone.utc).isoformat()

    for case in dataset["cases"]:
        request = ParseTransactionsRequest(
            text=case["input"],
            reference_date=dataset["reference_date"],
            timezone=dataset["timezone"],
            currency=dataset["currency"],
        )
        started = time.perf_counter()
        try:
            result = await client.parse(request)
            actual = result.model_dump(mode="json")
            actual["latency_ms"] = int((time.perf_counter() - started) * 1000)
            prompt_versions.add(result.prompt_version)
            results.append(evaluate_case(case, actual))
        except ServiceError as error:
            results.append(evaluate_case(case, None, f"{error.code}: {error.message}"))
        except Exception as error:  # noqa: BLE001 - One failed case must not hide later results.
            results.append(
                evaluate_case(case, None, f"UNEXPECTED_ERROR: {type(error).__name__}")
            )

    summary = summarize(results)
    latencies = [
        result["actual"]["latency_ms"]
        for result in results
        if result["actual"] is not None and "latency_ms" in result["actual"]
    ]
    summary["average_latency_ms"] = (
        round(sum(latencies) / len(latencies), 2) if latencies else None
    )
    summary["p95_latency_ms"] = (
        sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else None
    )
    return {
        "evaluation_version": "1.0",
        "dataset_version": dataset["dataset_version"],
        "prompt_sha256": prompt_sha256(),
        "prompt_versions": sorted(prompt_versions),
        "model_name": "mock" if settings.mock_mode else settings.model_name,
        "mode": "mock" if settings.mock_mode else "real",
        "reference_date": dataset["reference_date"],
        "started_at": started_at,
        "summary": summary,
        "cases": results,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run U Money transaction parser offline evaluation."
    )
    parser.add_argument(
        "--real", action="store_true", help="Call the configured real model."
    )
    parser.add_argument(
        "--confirm-real-model",
        action="store_true",
        help="Required with --real because model requests may create costs.",
    )
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals" / "dataset.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "evals" / "results")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    if args.real and not args.confirm_real_model:
        print(
            "未运行真实模型：真实模型调用可能产生费用。请确认后使用 --real --confirm-real-model。"
        )
        return 2

    settings = Settings.from_environment()
    if args.real:
        if not settings.model_api_key or not settings.model_name:
            print(
                "未运行真实模型：请在服务端环境变量中配置 MODEL_API_KEY 和 MODEL_NAME。"
            )
            return 2
        settings = Settings(**{**settings.__dict__, "mock_mode": False})
        print(f"即将调用真实模型 {settings.model_name}，这可能产生费用。")
    else:
        settings = Settings(**{**settings.__dict__, "mock_mode": True})

    dataset = load_dataset(args.dataset)
    report = asyncio.run(run_evaluation(dataset, settings))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{report['mode']}-{timestamp}.json"
    markdown_path = args.output_dir / f"{report['mode']}-{timestamp}.md"
    markdown = markdown_report(report)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown_path.write_text(markdown, encoding="utf-8")
    (ROOT / "docs" / "ai-evaluation-report.md").write_text(markdown, encoding="utf-8")
    print(f"JSON 报告：{json_path}")
    print(f"Markdown 报告：{markdown_path}")
    print(f"当前报告：{ROOT / 'docs' / 'ai-evaluation-report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
