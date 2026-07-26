from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_origins(value: str | None) -> tuple[str, ...]:
    default = (
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "https://nota03130101-dev.github.io",
    )
    if not value:
        return default
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    app_environment: str = "development"
    mock_mode: bool = False
    model_api_base_url: str = "https://api.openai.com/v1"
    model_api_key: str = ""
    model_name: str = ""
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "https://nota03130101-dev.github.io",
    )
    model_timeout_seconds: float = 15.0
    request_timeout_seconds: float = 20.0
    max_text_length: int = 1000
    log_hash_key: str = ""
    parse_per_minute_limit: int = 5
    parse_per_day_limit: int = 30
    monthly_summary_limit: int = 3
    monthly_summary_window_seconds: int = 600

    def validate_runtime(self) -> None:
        if self.app_environment not in {"development", "production"}:
            raise ValueError("APP_ENV must be development or production.")
        if self.parse_per_minute_limit < 1 or self.parse_per_day_limit < 1:
            raise ValueError("AI parse rate limits must be positive.")

        if self.app_environment != "production":
            return

        if self.mock_mode:
            raise ValueError("Production must set MOCK_MODE=false.")
        if not self.model_api_key or not self.model_name:
            raise ValueError("Production requires model API configuration.")
        if not self.supabase_url or not self.supabase_publishable_key:
            raise ValueError("Production requires Supabase Auth configuration.")
        if not self.model_api_base_url.startswith("https://"):
            raise ValueError("Production model API URL must use HTTPS.")
        if not self.log_hash_key:
            raise ValueError("Production requires LOG_HASH_KEY.")
        if not self.allowed_origins or "*" in self.allowed_origins:
            raise ValueError("Production CORS origins must be explicit.")
        if any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("Production CORS origins must use HTTPS.")

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            app_environment=os.getenv("APP_ENV", "development").strip().lower(),
            mock_mode=_as_bool(os.getenv("MOCK_MODE"), False),
            model_api_base_url=os.getenv("MODEL_API_BASE_URL", "https://api.openai.com/v1"),
            model_api_key=os.getenv("MODEL_API_KEY", ""),
            model_name=os.getenv("MODEL_NAME", ""),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
            allowed_origins=_as_origins(os.getenv("ALLOWED_ORIGINS")),
            model_timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "15")),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
            max_text_length=int(os.getenv("MAX_TEXT_LENGTH", "1000")),
            log_hash_key=os.getenv("LOG_HASH_KEY", ""),
            parse_per_minute_limit=int(os.getenv("PARSE_PER_MINUTE_LIMIT", "5")),
            parse_per_day_limit=int(os.getenv("PARSE_PER_DAY_LIMIT", "30")),
            monthly_summary_limit=int(os.getenv("MONTHLY_SUMMARY_LIMIT", "3")),
            monthly_summary_window_seconds=int(
                os.getenv("MONTHLY_SUMMARY_WINDOW_SECONDS", "600")
            ),
        )
