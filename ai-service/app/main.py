from __future__ import annotations

import asyncio
import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import AuthenticatedUser, get_current_user
from .config import Settings
from .errors import ModelTimeoutError, ServiceError
from .model_client import ModelClient
from .models import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    MonthlySummaryRequest,
    MonthlySummaryResponse,
    ParseTransactionsRequest,
    ParseTransactionsResponse,
)
from .rate_limit import InMemoryRateLimiter

logger = logging.getLogger("u_money_ai")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_environment()
    active_settings.validate_runtime()
    app = FastAPI(title="U Money AI Service", version="0.1.0")
    app.state.settings = active_settings
    app.state.model_client = ModelClient(active_settings)
    app.state.parse_minute_limiter = InMemoryRateLimiter(
        limit=active_settings.parse_per_minute_limit, window_seconds=60
    )
    app.state.parse_daily_limiter = InMemoryRateLimiter(
        limit=active_settings.parse_per_day_limit, window_seconds=24 * 60 * 60
    )
    app.state.monthly_summary_limiter = InMemoryRateLimiter(
        limit=active_settings.monthly_summary_limit,
        window_seconds=active_settings.monthly_summary_window_seconds,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        # The allowed origin remains explicit. Browsers may add harmless
        # request headers during preflight, so do not reject those requests.
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id_and_limit_body(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        content_length = request.headers.get("content-length")
        try:
            request_size = int(content_length) if content_length else 0
        except ValueError:
            request_size = -1
        if request_size < 0 or request_size > 8 * 1024:
            error = ErrorResponse(
                error=ErrorDetail(
                    code="REQUEST_TOO_LARGE",
                    message="输入内容太长，请分成几次记录。",
                    retryable=False,
                    request_id=_request_id(request),
                )
            )
            return JSONResponse(error.model_dump(), status_code=413)
        response = await call_next(request)
        response.headers["X-Request-ID"] = _request_id(request)
        if request.url.path.startswith("/ai/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ServiceError)
    async def handle_service_error(request: Request, error: ServiceError):
        payload = ErrorResponse(
            error=ErrorDetail(
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                request_id=_request_id(request),
            )
        )
        return JSONResponse(payload.model_dump(), status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _error: RequestValidationError):
        payload = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="请求内容不符合要求，请检查日期、金额和输入长度。",
                retryable=False,
                request_id=_request_id(request),
            )
        )
        return JSONResponse(payload.model_dump(), status_code=422)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/ai/parse-transactions", response_model=ParseTransactionsResponse)
    async def parse_transactions(
        body: ParseTransactionsRequest,
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> ParseTransactionsResponse:
        if not request.app.state.parse_minute_limiter.allow(user.log_id):
            raise ServiceError(
                429,
                "PARSE_RATE_LIMITED",
                "智能记账请求过于频繁，请稍后再试。",
                True,
            )
        if not request.app.state.parse_daily_limiter.allow(user.log_id):
            raise ServiceError(
                429,
                "PARSE_DAILY_LIMIT_REACHED",
                "今天的智能记账次数已用完，请使用普通手动记账。",
                False,
            )

        started = time.perf_counter()
        try:
            async with asyncio.timeout(active_settings.request_timeout_seconds):
                result = await request.app.state.model_client.parse(body)
        except TimeoutError as error:
            raise ModelTimeoutError() from error

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ai_parse_complete request_id=%s user_hash=%s elapsed_ms=%s prompt_version=%s status=%s candidates=%s",
            _request_id(request),
            user.log_id,
            elapsed_ms,
            result.prompt_version,
            result.status,
            len(result.transactions),
        )
        return ParseTransactionsResponse(
            request_id=_request_id(request),
            elapsed_ms=elapsed_ms,
            **result.model_dump(),
        )

    @app.post("/ai/monthly-summary", response_model=MonthlySummaryResponse)
    async def monthly_summary(
        body: MonthlySummaryRequest,
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> MonthlySummaryResponse:
        if body.totals.record_count == 0:
            return MonthlySummaryResponse(
                request_id=_request_id(request),
                elapsed_ms=0,
                month=body.month,
                statistics_period_start=body.statistics_period_start,
                statistics_period_end=body.statistics_period_end,
                data_status="empty",
                summary=None,
                warnings=["这个月还没有记录，普通统计仍然可用。"],
            )

        if not request.app.state.monthly_summary_limiter.allow(user.log_id):
            raise ServiceError(
                429,
                "SUMMARY_RATE_LIMITED",
                "重新生成次数较多，请十分钟后再试。",
                True,
            )

        started = time.perf_counter()
        try:
            async with asyncio.timeout(active_settings.request_timeout_seconds):
                summary = await request.app.state.model_client.summarize(body)
        except TimeoutError as error:
            raise ModelTimeoutError() from error

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ai_monthly_summary_complete request_id=%s user_hash=%s elapsed_ms=%s "
            "prompt_version=%s",
            _request_id(request),
            user.log_id,
            elapsed_ms,
            "monthly-summary-v1",
        )
        return MonthlySummaryResponse(
            request_id=_request_id(request),
            elapsed_ms=elapsed_ms,
            month=body.month,
            statistics_period_start=body.statistics_period_start,
            statistics_period_end=body.statistics_period_end,
            data_status="available",
            summary=summary,
            warnings=["AI 生成内容仅供参考，不构成财务建议。"],
        )

    return app


app = create_app()
