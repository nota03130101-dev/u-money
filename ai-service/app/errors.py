from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ServiceError(Exception):
    status_code: int
    code: str
    message: str
    retryable: bool = False


class ModelTimeoutError(ServiceError):
    def __init__(self) -> None:
        super().__init__(504, "MODEL_TIMEOUT", "智能解析响应超时，请稍后重试或手动记账。", True)


class ModelOutputError(ServiceError):
    def __init__(self) -> None:
        super().__init__(502, "MODEL_INVALID_OUTPUT", "暂时无法可靠识别，请修改描述或手动填写。")
