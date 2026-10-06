from datetime import UTC, datetime
from typing import Literal

EventStatus = Literal["started", "completed", "warning", "denied", "failed"]


def event(node: str, status: EventStatus, detail: str, **metadata: object) -> dict:
    payload: dict[str, object] = {"node": node, "status": status, "detail": detail, "timestamp": datetime.now(UTC).isoformat()}
    if metadata:
        payload["metadata"] = metadata
    return payload


def error(code: str, node: str, detail: str, retryable: bool = False) -> dict:
    return {"code": code, "node": node, "detail": detail, "retryable": retryable}
