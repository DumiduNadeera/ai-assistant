import os
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import settings

F = TypeVar("F", bound=Callable[..., Any])


def configure_tracing() -> None:
    if settings.tracing_enabled and settings.tracing_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.tracing_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.tracing_project
        if settings.langsmith_endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint.rstrip("/")
        if settings.langsmith_workspace_id:
            os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id


def traced(name: str, run_type: str = "chain"):
    """Use LangSmith's decorator when available; preserve local execution otherwise."""
    if not (settings.tracing_enabled and settings.tracing_api_key):
        def passthrough(func: F) -> F:
            return func
        return passthrough
    try:
        from langsmith import traceable
        return traceable(name=name, run_type=run_type)
    except ImportError:
        def passthrough(func: F) -> F:
            return func
        return passthrough
