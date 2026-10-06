from collections.abc import AsyncIterator, Iterator
import os

import httpx
import pytest
import pytest_asyncio

# Keep the test suite deterministic, offline, and free of external telemetry.
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ["PINECONE_API_KEY"] = ""
os.environ["PINECONE_INDEX"] = ""

import app.api as api_module  # noqa: E402
from app.memory import memory_store  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_runtime_state() -> Iterator[None]:
    """Prevent in-memory sessions and token buckets from leaking across tests."""
    original_limiter = api_module.limiter
    memory_store.reset()
    original_limiter._buckets.clear()
    yield
    memory_store.reset()
    api_module.limiter = original_limiter
    original_limiter._buckets.clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=api_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-viewer-token"}


@pytest.fixture
def analyst_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-analyst-token"}


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-admin-token"}
