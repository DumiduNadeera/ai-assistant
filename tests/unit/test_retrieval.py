import math

import pytest

from app.retrieval import dense_embedding, hybrid_search, load_documents, tokenize


pytestmark = pytest.mark.unit


def test_tokenize_normalizes_words_and_numbers() -> None:
    assert tokenize("Payment-API retry #42") == ["payment", "api", "retry", "42"]


def test_local_documents_have_attribution_and_access_metadata() -> None:
    documents = load_documents()

    assert documents
    for document in documents:
        assert document["document_id"]
        assert document["title"]
        assert document["source_uri"].startswith("data/")
        assert document["access_level"] == "internal"


async def test_hybrid_search_is_ranked_bounded_and_grounded() -> None:
    results = await hybrid_search("payment pool saturation outage", role="viewer", top_k=2)

    assert 0 < len(results) <= 2
    assert results == sorted(results, key=lambda item: item["score"], reverse=True)
    assert all(result["score"] > 0 for result in results)
    assert all(result["content"] for result in results)


def test_dense_embedding_is_deterministic_and_normalized() -> None:
    first = dense_embedding("payment retry queue", dimensions=64)
    second = dense_embedding("payment retry queue", dimensions=64)

    assert first == second
    assert len(first) == 64
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)

