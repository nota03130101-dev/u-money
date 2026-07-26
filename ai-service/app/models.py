from __future__ import annotations

import re
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParseTransactionsRequest(StrictModel):
    text: str = Field(min_length=1, max_length=1000)
    reference_date: date
    timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    currency: Literal["CNY"] = "CNY"

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("请输入一条记账描述。")
        return cleaned


class TransactionCandidate(StrictModel):
    candidate_id: str = Field(pattern=r"^candidate-[1-9][0-9]*$")
    date: date | None
    type: Literal["收入", "支出"] | None
    amount: str | None = None
    currency: Literal["CNY"] = "CNY"
    category: (
        Literal[
            "工资",
            "奖金",
            "兼职",
            "报销",
            "理财收益",
            "礼金收入",
            "退款",
            "其他收入",
            "餐饮",
            "交通",
            "住房",
            "水电燃气",
            "通讯",
            "购物",
            "医疗",
            "教育",
            "娱乐",
            "旅行",
            "人情支出",
            "宠物",
            "保险",
            "税费",
            "其他支出",
        ]
        | None
    )
    note: str | None = Field(default=None, max_length=200)
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[Literal["date", "type", "amount", "category"]] = Field(
        default_factory=list
    )
    uncertain_fields: list[Literal["date", "type", "amount", "category", "note"]] = Field(
        default_factory=list
    )
    assumptions: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"(0|[1-9][0-9]{0,7})(\.[0-9]{1,2})?", value):
            raise ValueError("金额格式不正确。")
        try:
            amount = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("金额格式不正确。") from error
        if amount <= 0 or amount > Decimal("99999999.99"):
            raise ValueError("金额必须大于 0 且不超过允许范围。")
        return f"{amount:.2f}"

    @field_validator("missing_fields", "uncertain_fields")
    @classmethod
    def validate_unique_fields(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("字段列表不能重复。")
        return value

    def required_fields_complete(self) -> bool:
        return all((self.date, self.type, self.amount, self.category))


class ConfirmationQuestion(StrictModel):
    candidate_id: str | None = None
    field: Literal["date", "type", "amount", "category", "transaction_count"]
    question: str = Field(min_length=1, max_length=120)

    @field_validator("candidate_id")
    @classmethod
    def validate_candidate_id(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"candidate-[1-9][0-9]*", value):
            raise ValueError("候选记录编号不正确。")
        return value


class ParserResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    prompt_version: Literal["transaction-parser-v1"] = "transaction-parser-v1"
    status: Literal["success", "needs_confirmation", "rejected"]
    requires_user_approval: Literal[True] = True
    needs_confirmation: bool
    transactions: list[TransactionCandidate] = Field(default_factory=list, max_length=20)
    confirmation_questions: list[ConfirmationQuestion] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=10)
    rejection_reason: (
        Literal["EMPTY_INPUT", "UNRELATED_INPUT", "UNSAFE_INPUT", "TOO_MANY_TRANSACTIONS"] | None
    ) = None

    @model_validator(mode="after")
    def validate_status(self) -> "ParserResult":
        if self.status == "rejected":
            if self.transactions or self.needs_confirmation or self.rejection_reason is None:
                raise ValueError("拒绝结果不能包含候选记录。")
            return self
        if self.rejection_reason is not None:
            raise ValueError("非拒绝结果不能包含拒绝原因。")
        if self.status == "success":
            if self.needs_confirmation or self.confirmation_questions:
                raise ValueError("成功结果不能包含确认问题。")
            if not self.transactions or any(
                not item.required_fields_complete() or item.missing_fields or item.uncertain_fields
                for item in self.transactions
            ):
                raise ValueError("成功结果必须包含完整且明确的候选记录。")
        if self.status == "needs_confirmation":
            if (
                not self.needs_confirmation
                or not self.transactions
                or not self.confirmation_questions
            ):
                raise ValueError("待确认结果必须包含候选记录和确认问题。")
        return self


class ParseTransactionsResponse(ParserResult):
    request_id: str
    elapsed_ms: int = Field(ge=0)


class MonthlyTotals(StrictModel):
    income: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    expense: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    balance_change: Decimal = Field(max_digits=10, decimal_places=2)
    record_count: int = Field(ge=0, le=100000)


class ExpenseCategorySummary(StrictModel):
    category: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    percentage: float = Field(gt=0, le=100)


class MonthComparison(StrictModel):
    previous_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    available: bool
    income_change: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    expense_change: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    balance_change: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def validate_available_values(self) -> "MonthComparison":
        values = (self.income_change, self.expense_change, self.balance_change)
        if self.available and any(value is None for value in values):
            raise ValueError("有上月数据时必须提供变化值。")
        if not self.available and any(value is not None for value in values):
            raise ValueError("没有上月数据时不能提供变化值。")
        return self


class MonthlySummaryRequest(StrictModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    statistics_period_start: date
    statistics_period_end: date
    currency: Literal["CNY"] = "CNY"
    totals: MonthlyTotals
    expense_categories: list[ExpenseCategorySummary] = Field(default_factory=list, max_length=20)
    comparison: MonthComparison

    @model_validator(mode="after")
    def validate_period(self) -> "MonthlySummaryRequest":
        year, month = (int(part) for part in self.month.split("-"))
        expected_start = date(year, month, 1)
        expected_end = date(year, month, monthrange(year, month)[1])
        if (
            self.statistics_period_start != expected_start
            or self.statistics_period_end != expected_end
        ):
            raise ValueError("统计时间必须覆盖所选月份的第一天到最后一天。")

        if self.totals.balance_change != self.totals.income - self.totals.expense:
            raise ValueError("余额变化必须等于收入减支出。")

        if len({item.category for item in self.expense_categories}) != len(
            self.expense_categories
        ):
            raise ValueError("支出类别不能重复。")

        category_amount = sum((item.amount for item in self.expense_categories), Decimal("0"))
        if category_amount != self.totals.expense:
            raise ValueError("类别支出合计必须等于总支出。")

        if self.totals.expense > 0:
            for item in self.expense_categories:
                expected_percentage = float(item.amount / self.totals.expense * 100)
                if abs(item.percentage - expected_percentage) > 0.05:
                    raise ValueError("支出类别百分比与金额不一致。")

        if self.totals.record_count == 0 and (
            self.totals.income != 0
            or self.totals.expense != 0
            or self.expense_categories
        ):
            raise ValueError("没有记录时，收入、支出和类别汇总必须为空。")

        previous_year = year if month > 1 else year - 1
        previous_month = month - 1 if month > 1 else 12
        expected_previous = f"{previous_year:04d}-{previous_month:02d}"
        if self.comparison.previous_month != expected_previous:
            raise ValueError("对比月份必须是所选月份的上一个月。")
        return self


class MonthlySummaryText(StrictModel):
    overview: str = Field(min_length=1, max_length=180)
    largest_category_observation: str | None = Field(default=None, max_length=160)
    change_observation: str | None = Field(default=None, max_length=160)
    neutral_observation: str = Field(min_length=1, max_length=160)
    suggestion: str | None = Field(default=None, max_length=160)

    @field_validator(
        "overview",
        "largest_category_observation",
        "change_observation",
        "neutral_observation",
        "suggestion",
    )
    @classmethod
    def validate_safe_language(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        if value is None:
            return None
        if re.search(r"[0-9¥%]", value):
            raise ValueError("总结文字不能重新给出或计算数字。")
        if info.field_name == "suggestion" and re.search(
            r"投资|股票|基金|贷款|借款|保险|医疗|诊断|药物|就医", value
        ):
            raise ValueError("总结文字不能提供受限制领域的建议。")
        if re.search(r"羞耻|愚蠢|糟糕透顶|浪费钱|必须|恐怖", value):
            raise ValueError("总结文字必须使用中性且非羞辱性的语言。")
        return value


class MonthlySummaryResponse(StrictModel):
    request_id: str
    elapsed_ms: int = Field(ge=0)
    prompt_version: Literal["monthly-summary-v1"] = "monthly-summary-v1"
    month: str
    statistics_period_start: date
    statistics_period_end: date
    data_status: Literal["available", "empty"]
    summary: MonthlySummaryText | None
    warnings: list[str] = Field(default_factory=list, max_length=3)


class ErrorDetail(StrictModel):
    code: str
    message: str
    retryable: bool
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["u-money-ai"] = "u-money-ai"
    version: Literal["0.1.0"] = "0.1.0"
