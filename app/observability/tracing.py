import os
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import settings

F = TypeVar("F", bound=Callable[..., Any])


def configure_tracing() -> None:
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)


def traced(name: str, run_type: str = "chain"):
    """Use LangSmith's decorator when available; preserve local execution otherwise."""
    if not (settings.langchain_tracing_v2 and settings.langchain_api_key):
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
