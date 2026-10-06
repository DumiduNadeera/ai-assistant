from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    message: str = Field(min_length=3, max_length=4000)


class Citation(BaseModel):
    document_id: str
    title: str
    section: str
    source_uri: str


class ActivityEvent(BaseModel):
    node: str
    status: Literal["started", "completed", "warning", "denied", "failed"]
    detail: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionSummary(BaseModel):
    run_id: str
    route: str
    intent: str
    nodes: list[str]
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    execution: ExecutionSummary
    activity: list[ActivityEvent]
