import json
import logging

import pytest

from app.core.config import settings
from app.core.logging import JsonFormatter
from app.mcp_server import get_service_catalog, search_employee_directory
from app.pinecone_store import PineconeStore


pytestmark = pytest.mark.unit


def test_json_formatter_emits_structured_context() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "chat_completed", (), None)
    record.session_id = "session-1"
    record.user_id = "viewer@example.com"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "chat_completed"
    assert payload["level"] == "INFO"
    assert payload["session_id"] == "session-1"
    assert payload["user_id"] == "viewer@example.com"
    assert payload["timestamp"].endswith("+00:00")


def test_pinecone_adapter_fails_closed_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "pinecone_api_key", "")
    monkeypatch.setattr(settings, "pinecone_index", "")

    with pytest.raises(RuntimeError, match="PINECONE_API_KEY"):
        PineconeStore()


def test_mcp_dummy_data_is_queryable_without_real_employee_data() -> None:
    services = get_service_catalog()
    employees = search_employee_directory("site reliability")

    assert services
    assert employees == [{"name": "Sam Patel", "team": "Site Reliability", "title": "On-call Lead"}]

