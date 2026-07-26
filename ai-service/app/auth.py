from __future__ import annotations

import hashlib
import hmac

import httpx
from fastapi import Header, Request

from .errors import ServiceError


class AuthenticatedUser:
    def __init__(self, user_id: str, log_hash_key: str) -> None:
        self.user_id = user_id
        self.log_hash_key = log_hash_key

    @property
    def log_id(self) -> str:
        key = self.log_hash_key or "development-log-hash-key"
        return hmac.new(
            key.encode("utf-8"), self.user_id.encode("utf-8"), hashlib.sha256
        ).hexdigest()[:16]


def _read_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ServiceError(401, "UNAUTHORIZED", "请先登录后再使用智能记账。")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ServiceError(401, "UNAUTHORIZED", "请先登录后再使用智能记账。")
    return token


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    token = _read_bearer_token(authorization)
    settings = request.app.state.settings
    if settings.mock_mode:
        return AuthenticatedUser("mock-local-user", settings.log_hash_key)
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise ServiceError(503, "AUTH_NOT_CONFIGURED", "智能服务尚未完成身份验证配置。")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.TimeoutException as error:
        raise ServiceError(
            503, "AUTH_UNAVAILABLE", "身份验证暂时不可用，请稍后重试。", True
        ) from error
    except httpx.HTTPError as error:
        raise ServiceError(
            503, "AUTH_UNAVAILABLE", "身份验证暂时不可用，请稍后重试。", True
        ) from error

    if response.status_code != 200:
        raise ServiceError(401, "UNAUTHORIZED", "登录状态已失效，请重新登录。")
    user_id = response.json().get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ServiceError(401, "UNAUTHORIZED", "登录状态已失效，请重新登录。")
    return AuthenticatedUser(user_id, settings.log_hash_key)
