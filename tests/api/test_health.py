import httpx
import pytest


pytestmark = pytest.mark.api


async def test_health_contract_is_public(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "orysys-enterprise-assistant"
    assert response.json()["version"] == "0.2.0"


async def test_readiness_reports_retrieval_mode(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["retrieval"] == "local-hybrid-fallback"
    assert body["llm_provider"] == "deterministic"
    assert isinstance(body["langsmith_configured"], bool)
