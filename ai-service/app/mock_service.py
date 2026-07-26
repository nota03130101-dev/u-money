from __future__ import annotations

from datetime import timedelta

from .errors import ModelOutputError, ModelTimeoutError
from .models import (
    ConfirmationQuestion,
    MonthlySummaryRequest,
    MonthlySummaryText,
    ParserResult,
    ParseTransactionsRequest,
    TransactionCandidate,
)


def _candidate(
    candidate_id: int,
    *,
    date_value,
    record_type: str | None,
    amount: str | None,
    category: str | None,
    note: str | None,
    confidence: float,
    missing_fields: list[str] | None = None,
    uncertain_fields: list[str] | None = None,
    assumptions: list[str] | None = None,
) -> TransactionCandidate:
    return TransactionCandidate(
        candidate_id=f"candidate-{candidate_id}",
        date=date_value,
        type=record_type,
        amount=amount,
        category=category,
        note=note,
        confidence=confidence,
        missing_fields=missing_fields or [],
        uncertain_fields=uncertain_fields or [],
        assumptions=assumptions or [],
    )


class MockTransactionParser:
    """Fixed, privacy-safe results for local UI development and tests."""

    async def parse(self, request: ParseTransactionsRequest) -> ParserResult:
        text = request.text.replace("，", ",").replace("。", "").strip()
        today = request.reference_date
        yesterday = today - timedelta(days=1)

        if text == "__timeout__":
            raise ModelTimeoutError()
        if text == "__invalid_json__":
            raise ModelOutputError()
        if any(
            word in text.lower() for word in ("忽略规则", "system prompt", "api 密钥", "api key")
        ):
            return ParserResult(
                status="rejected",
                needs_confirmation=False,
                transactions=[],
                confirmation_questions=[],
                warnings=["输入内容不能作为记账信息处理。"],
                rejection_reason="UNSAFE_INPUT",
            )
        if text in {"今天天气怎么样", "你好", "测试"}:
            return ParserResult(
                status="rejected",
                needs_confirmation=False,
                transactions=[],
                confirmation_questions=[],
                warnings=["没有识别到记账内容，请描述日期、金额和用途。"],
                rejection_reason="UNRELATED_INPUT",
            )
        if "午饭" in text and "地铁" in text:
            date_value = yesterday if "昨天" in text else today
            return ParserResult(
                status="success",
                needs_confirmation=False,
                transactions=[
                    _candidate(
                        1,
                        date_value=date_value,
                        record_type="支出",
                        amount="32.00",
                        category="餐饮",
                        note="午饭",
                        confidence=0.98,
                    ),
                    _candidate(
                        2,
                        date_value=date_value,
                        record_type="支出",
                        amount="4.00",
                        category="交通",
                        note="地铁",
                        confidence=0.97,
                    ),
                ],
                confirmation_questions=[],
                warnings=[],
                rejection_reason=None,
            )
        if "工资" in text:
            return ParserResult(
                status="success",
                needs_confirmation=False,
                transactions=[
                    _candidate(
                        1,
                        date_value=today.replace(year=2026, month=7, day=20),
                        record_type="收入",
                        amount="8000.00",
                        category="工资",
                        note="工资",
                        confidence=0.99,
                    )
                ],
                confirmation_questions=[],
                warnings=[],
                rejection_reason=None,
            )
        if "咖啡" in text:
            return ParserResult(
                status="success",
                needs_confirmation=False,
                transactions=[
                    _candidate(
                        1,
                        date_value=today,
                        record_type="支出",
                        amount="12.50",
                        category="餐饮",
                        note="咖啡",
                        confidence=0.98,
                    )
                ],
                confirmation_questions=[],
                warnings=[],
                rejection_reason=None,
            )
        if text in {"今天午饭", "午饭"}:
            return ParserResult(
                status="needs_confirmation",
                needs_confirmation=True,
                transactions=[
                    _candidate(
                        1,
                        date_value=today,
                        record_type="支出",
                        amount=None,
                        category="餐饮",
                        note="午饭",
                        confidence=0.78,
                        missing_fields=["amount"],
                        assumptions=["未说明日期，按今天处理"],
                    )
                ],
                confirmation_questions=[
                    ConfirmationQuestion(
                        candidate_id="candidate-1",
                        field="amount",
                        question="这笔午饭的金额是多少？",
                    )
                ],
                warnings=[],
                rejection_reason=None,
            )
        if "花了 20" in text or "花了20" in text:
            return ParserResult(
                status="needs_confirmation",
                needs_confirmation=True,
                transactions=[
                    _candidate(
                        1,
                        date_value=today,
                        record_type="支出",
                        amount="20.00",
                        category=None,
                        note=None,
                        confidence=0.72,
                        missing_fields=["category"],
                        assumptions=["未说明类别"],
                    )
                ],
                confirmation_questions=[
                    ConfirmationQuestion(
                        candidate_id="candidate-1",
                        field="category",
                        question="这笔 20 元支出属于什么类别？",
                    )
                ],
                warnings=[],
                rejection_reason=None,
            )
        if "一百二" in text:
            return ParserResult(
                status="needs_confirmation",
                needs_confirmation=True,
                transactions=[
                    _candidate(
                        1,
                        date_value=today,
                        record_type="支出",
                        amount=None,
                        category="餐饮",
                        note="午饭",
                        confidence=0.58,
                        uncertain_fields=["amount"],
                        assumptions=["未说明日期，按今天处理"],
                    )
                ],
                confirmation_questions=[
                    ConfirmationQuestion(
                        candidate_id="candidate-1",
                        field="amount",
                        question="“一百二”是 120 元还是其他金额？",
                    )
                ],
                warnings=[],
                rejection_reason=None,
            )
        if "午饭" in text:
            date_value = yesterday if "昨天" in text else today
            return ParserResult(
                status="success",
                needs_confirmation=False,
                transactions=[
                    _candidate(
                        1,
                        date_value=date_value,
                        record_type="支出",
                        amount="32.00",
                        category="餐饮",
                        note="午饭",
                        confidence=0.98,
                    )
                ],
                confirmation_questions=[],
                warnings=[],
                rejection_reason=None,
            )
        return ParserResult(
            status="rejected",
            needs_confirmation=False,
            transactions=[],
            confirmation_questions=[],
            warnings=["没有识别到记账内容，请描述日期、金额和用途。"],
            rejection_reason="UNRELATED_INPUT",
        )


class MockMonthlySummary:
    """Predictable wording for local monthly-summary development."""

    async def summarize(self, request: MonthlySummaryRequest) -> MonthlySummaryText:
        largest_category = request.expense_categories[0] if request.expense_categories else None
        largest_observation = (
            f"支出主要集中在{largest_category.category}类别。"
            if largest_category
            else "本月没有可比较的支出类别。"
        )

        change_observation = None
        if request.comparison.available:
            if request.comparison.expense_change and request.comparison.expense_change > 0:
                change_observation = "与上月相比，支出有所增加。"
            elif request.comparison.expense_change and request.comparison.expense_change < 0:
                change_observation = "与上月相比，支出有所减少。"
            else:
                change_observation = "与上月相比，支出变化不大。"

        return MonthlySummaryText(
            overview="本月收入和支出统计已整理完成，可结合月度数据查看整体情况。",
            largest_category_observation=largest_observation,
            change_observation=change_observation,
            neutral_observation="这份内容只根据当前选择月份的汇总数据生成。",
            suggestion="可以从支出占比较高的类别中挑选一项，观察下次记录时是否有调整空间。",
        )
