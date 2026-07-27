from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx
from pydantic import ValidationError

from .config import Settings
from .errors import ModelOutputError, ModelTimeoutError, ServiceError
from .mock_service import MockMonthlySummary, MockTransactionParser
from .models import (
    MonthlySummaryRequest,
    MonthlySummaryText,
    ParserResult,
    ParseTransactionsRequest,
)

logger = logging.getLogger(__name__)


def _log_model_output_rejection(operation: str, error: Exception) -> None:
    """Record only the failure category, never the model response itself."""
    reason = "unexpected_response_shape"
    if isinstance(error, ValidationError):
        details = error.errors()
        reason = (
            "invalid_json"
            if details and details[0].get("type") == "json_invalid"
            else "schema_validation"
        )
    logger.warning(
        "Model output rejected: operation=%s reason=%s error_type=%s",
        operation,
        reason,
        type(error).__name__,
    )


def _load_system_prompt(prompt_name: str) -> str:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / prompt_name
    text = prompt_path.read_text(encoding="utf-8")
    match = re.search(r"## System Prompt\s+```text\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        raise RuntimeError("Transaction parser prompt is missing.")
    return match.group(1)


class ModelClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mock_parser = MockTransactionParser()
        self.mock_monthly_summary = MockMonthlySummary()

    def _uses_deepseek(self) -> bool:
        return "api.deepseek.com" in self.settings.model_api_base_url

    async def parse(self, request: ParseTransactionsRequest) -> ParserResult:
        if self.settings.mock_mode:
            return await self.mock_parser.parse(request)
        return await self._parse_with_model(request)

    async def summarize(self, request: MonthlySummaryRequest) -> MonthlySummaryText:
        if self.settings.mock_mode:
            return await self.mock_monthly_summary.summarize(request)
        return await self._summarize_with_model(request)

    async def _parse_with_model(self, request: ParseTransactionsRequest) -> ParserResult:
        if not self.settings.model_api_key or not self.settings.model_name:
            raise ServiceError(503, "MODEL_NOT_CONFIGURED", "智能服务尚未完成模型配置。")

        payload = {
            "model": self.settings.model_name,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _load_system_prompt("transaction-parser.md")},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "reference_date": request.reference_date.isoformat(),
                            "timezone": request.timezone,
                            "currency": request.currency,
                            "user_text": request.text,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            # The provider returns a JSON object. Pydantic
            # validates that JSON below before anything reaches the frontend.
            "response_format": {"type": "json_object"},
        }
        if self._uses_deepseek():
            payload["thinking"] = {"type": "disabled"}
        url = f"{self.settings.model_api_base_url.rstrip('/')}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.settings.model_timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.settings.model_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ModelTimeoutError() from error
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Model API request failed: status=%s provider_request_id=%s",
                error.response.status_code,
                error.response.headers.get("x-request-id")
                or error.response.headers.get("x-dashscope-request-id"),
            )
            raise ServiceError(
                503, "MODEL_UNAVAILABLE", "智能服务暂时不可用，请稍后重试。", True
            ) from error
        except httpx.HTTPError as error:
            raise ServiceError(
                503, "MODEL_UNAVAILABLE", "智能服务暂时不可用，请稍后重试。", True
            ) from error

        try:
            content = response.json()["choices"][0]["message"]["content"]
            return ParserResult.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as error:
            _log_model_output_rejection("parse_transactions", error)
            raise ModelOutputError() from error

    async def _summarize_with_model(self, request: MonthlySummaryRequest) -> MonthlySummaryText:
        if not self.settings.model_api_key or not self.settings.model_name:
            raise ServiceError(503, "MODEL_NOT_CONFIGURED", "智能服务尚未完成模型配置。")

        payload = {
            "model": self.settings.model_name,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _load_system_prompt("monthly-summary.md")},
                {
                    "role": "user",
                    "content": json.dumps(
                        request.model_dump(mode="json"), ensure_ascii=False
                    ),
                },
            ],
            # Keep the model output simple and validate it on our own server.
            "response_format": {"type": "json_object"},
        }
        if self._uses_deepseek():
            payload["thinking"] = {"type": "disabled"}
        url = f"{self.settings.model_api_base_url.rstrip('/')}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.settings.model_timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.settings.model_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ModelTimeoutError() from error
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Model API request failed: status=%s provider_request_id=%s",
                error.response.status_code,
                error.response.headers.get("x-request-id")
                or error.response.headers.get("x-dashscope-request-id"),
            )
            raise ServiceError(
                503, "MODEL_UNAVAILABLE", "智能服务暂时不可用，请稍后重试。", True
            ) from error
        except httpx.HTTPError as error:
            raise ServiceError(
                503, "MODEL_UNAVAILABLE", "智能服务暂时不可用，请稍后重试。", True
            ) from error

        try:
            content = response.json()["choices"][0]["message"]["content"]
            return MonthlySummaryText.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as error:
            _log_model_output_rejection("monthly_summary", error)
            raise ModelOutputError() from error
