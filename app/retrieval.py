import asyncio
import hashlib
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
METADATA_RE = re.compile(r"^(Document ID|Department|Document type|Access level|Created date):\s*(.+)$", re.I)
ROLE_ACCESS = {
    "viewer": {"public", "internal"},
    "analyst": {"public", "internal", "confidential"},
    "administrator": {"public", "internal", "confidential", "restricted"},
}


def tokenize(text: str) -> list[str]:
    return [word.casefold() for word in TOKEN_RE.findall(text)]


def _metadata_key(label: str) -> str:
    return label.casefold().replace(" ", "_")


def _parse_document(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), path.stem)
    metadata: dict[str, str] = {}
    for line in lines:
        match = METADATA_RE.match(line.strip())
        if match:
            metadata[_metadata_key(match.group(1))] = match.group(2).strip()
    document_id = metadata.get("document_id", path.stem)
    document_type = metadata.get("document_type", path.parent.name.rstrip("s")).casefold()
    base = {
        "document_id": document_id,
        "title": title,
        "department": metadata.get("department", "engineering").casefold(),
        "document_type": document_type,
        "access_level": metadata.get("access_level", "internal").casefold(),
        "created_date": metadata.get("created_date", "1970-01-01"),
        "source_uri": str(path.relative_to(DATA_DIR.parent)).replace("\\", "/"),
    }
    chunks: list[dict] = []
    section = "Overview"
    body: list[str] = []

    def emit() -> None:
        content = "\n".join(line for line in body if line.strip()).strip()
        if not content:
            return
        section_slug = re.sub(r"[^a-z0-9]+", "-", section.casefold()).strip("-") or "overview"
        chunks.append({**base, "section": section, "chunk_id": f"{document_id}#{section_slug}#01", "content": content})

    for line in lines:
        if line.startswith("## "):
            emit()
            section = line[3:].strip()
            body = []
        elif not line.startswith("# ") and not METADATA_RE.match(line.strip()):
            body.append(line)
    emit()
    return chunks


@lru_cache(maxsize=1)
def load_documents() -> list[dict]:
    return [chunk for path in sorted(DATA_DIR.rglob("*.md")) for chunk in _parse_document(path)]


def _bm25_scores(query_terms: list[str], documents: list[dict]) -> list[float]:
    corpus = [tokenize(document["content"]) for document in documents]
    if not corpus:
        return []
    average_length = sum(map(len, corpus)) / len(corpus) or 1.0
    document_frequency = Counter(term for terms in corpus for term in set(terms))
    k1, b = 1.5, 0.75
    scores = []
    for terms in corpus:
        counts = Counter(terms)
        score = 0.0
        for term in set(query_terms):
            frequency = counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (len(corpus) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + k1 * (1 - b + b * len(terms) / average_length)
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        scores.append(score)
    return scores


def dense_embedding(text: str, dimensions: int | None = None) -> list[float]:
    """Credential-free local fallback; production mode uses the configured embedding API."""
    size = dimensions or settings.embedding_dimensions
    vector = [0.0] * size
    for token in tokenize(text):
        index = int.from_bytes(hashlib.blake2s(token.encode(), digest_size=4).digest(), "big") % size
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


async def dense_embedding_async(text: str) -> list[float]:
    if settings.llm_provider.casefold() == "openai" and settings.openai_api_key:
        from openai import AsyncOpenAI
        response = await AsyncOpenAI(api_key=settings.openai_api_key).embeddings.create(
            model=settings.embedding_model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
        return [float(value) for value in response.data[0].embedding]
    return await asyncio.to_thread(dense_embedding, text)


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lower, upper = min(scores), max(scores)
    if math.isclose(lower, upper):
        return [1.0 if upper > 0 else 0.0 for _ in scores]
    return [(score - lower) / (upper - lower) for score in scores]


def _query_filters(query: str) -> dict[str, str]:
    lowered = query.casefold()
    filters: dict[str, str] = {}
    if any(word in lowered for word in ("incident", "outage", "failure")):
        filters["document_type"] = "incident"
    elif "runbook" in lowered:
        filters["document_type"] = "runbook"
    year = re.search(r"\b20\d{2}\b", query)
    if year:
        filters["created_year"] = year.group(0)
    return filters


def _authorized_documents(role: str, query: str) -> list[dict]:
    allowed = ROLE_ACCESS.get(role, set())
    filters = _query_filters(query)
    documents = [document for document in load_documents() if document["access_level"] in allowed]
    if "document_type" in filters:
        documents = [document for document in documents if document["document_type"] == filters["document_type"]]
    if "created_year" in filters:
        documents = [document for document in documents if document["created_date"].startswith(filters["created_year"])]
    return documents


async def hybrid_search(query: str, role: str, top_k: int = 5) -> list[dict]:
    documents = _authorized_documents(role, query)
    if not documents:
        return []
    query_terms = tokenize(query)
    sparse_scores = _bm25_scores(query_terms, documents)
    query_vector = await dense_embedding_async(query)
    local_vectors = await asyncio.gather(*(dense_embedding_async(document["content"]) for document in documents))
    dense_scores = [_cosine(query_vector, vector) for vector in local_vectors]

    pinecone_scores: dict[str, float] = {}
    try:
        from app.pinecone_store import PineconeStore
        external = await PineconeStore().query(query, top_k=max(top_k * 2, 10), role=role, filters=_query_filters(query))
        pinecone_scores = {item["chunk_id"]: float(item.get("score", 0.0)) for item in external if item.get("chunk_id")}
    except Exception:
        # The local dense path is the documented graceful-degradation mode.
        pass

    if pinecone_scores:
        dense_scores = [pinecone_scores.get(document["chunk_id"], score) for document, score in zip(documents, dense_scores)]
    dense_normalized = _normalize(dense_scores)
    sparse_normalized = _normalize(sparse_scores)
    alpha = min(max(settings.hybrid_dense_weight, 0.0), 1.0)
    ranked = []
    for document, dense_score, sparse_score in zip(documents, dense_normalized, sparse_normalized):
        score = alpha * dense_score + (1 - alpha) * sparse_score
        if score > 0:
            ranked.append({**document, "score": score, "dense_score": dense_score, "sparse_score": sparse_score})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]
