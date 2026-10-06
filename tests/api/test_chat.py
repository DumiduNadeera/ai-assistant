import asyncio

import httpx
import pytest

import app.api as api_module


pytestmark = pytest.mark.api


async def test_chat_returns_grounded_answer_and_citations(
    client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/chat",
        headers=viewer_headers,
        json={"session_id": "grounded-chat", "message": "What caused the payment service outage?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "grounded-chat"
    assert body["answer"]
    assert body["citations"]
    assert body["execution"]["route"] == "retrieval"
    assert {"validate_evidence", "validate_response", "response_agent"}.issubset(body["execution"]["nodes"])
    for citation in body["citations"]:
        assert set(citation) == {"document_id", "title", "section", "source_uri"}
        assert not citation["source_uri"].startswith(("/", "\\"))


async def test_analyst_research_route_invokes_bounded_analysis(
    client: httpx.AsyncClient,
    analyst_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/chat",
        headers=analyst_headers,
        json={
            "session_id": "research-chat",
            "message": "Summarize all payment incidents and identify recurring root causes.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution"]["route"] == "research"
    assert "python_analysis" in body["execution"]["nodes"]
    assert "Research workflow" in body["answer"]


async def test_event_stream_emits_activity_before_answer(
    client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/chat/stream",
        headers=viewer_headers,
        json={"session_id": "stream-chat", "message": "Explain the payment runbook."},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "activity"' in response.text
    assert '"type": "answer.completed"' in response.text
    assert response.text.index('"type": "activity"') < response.text.index('"type": "answer.completed"')


async def test_timeout_is_mapped_to_gateway_timeout(
    client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def time_out(*args: object, **kwargs: object) -> None:
        raise asyncio.TimeoutError

    monkeypatch.setattr(api_module, "execute_chat", time_out)
    response = await client.post(
        "/api/v1/chat",
        headers=viewer_headers,
        json={"session_id": "timeout-chat", "message": "Find an incident."},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "Assistant execution timed out. Please retry."
