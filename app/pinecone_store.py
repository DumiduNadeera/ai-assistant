import asyncio
from app.core.config import settings
from app.retrieval import dense_embedding_async


class PineconeStore:
    """Optional Pinecone adapter; uses a 2048-dimensional feature-hash vector for POC wiring."""

    def __init__(self) -> None:
        if not settings.pinecone_api_key or not settings.pinecone_index:
            raise RuntimeError("Set PINECONE_API_KEY and PINECONE_INDEX to enable Pinecone.")
        from pinecone import Pinecone
        self.index = Pinecone(api_key=settings.pinecone_api_key).Index(settings.pinecone_index)
        self.namespace = settings.pinecone_namespace

    async def upsert(self, documents: list[dict]) -> None:
        vectors = await asyncio.gather(*(dense_embedding_async(doc["content"]) for doc in documents))
        records = [{"id": doc["chunk_id"], "values": vector, "metadata": doc}
                   for doc, vector in zip(documents, vectors)]
        await asyncio.to_thread(self.index.upsert, vectors=records, namespace=self.namespace)

    async def query(self, query: str, top_k: int = 5, role: str = "viewer", filters: dict | None = None) -> list[dict]:
        allowed = {"viewer": ["public", "internal"], "analyst": ["public", "internal", "confidential"],
                   "administrator": ["public", "internal", "confidential", "restricted"]}.get(role, [])
        filter_query: dict = {"access_level": {"$in": allowed}}
        filters = filters or {}
        if filters.get("document_type"):
            filter_query["document_type"] = {"$eq": filters["document_type"]}
        query_vector = await dense_embedding_async(query)
        response = await asyncio.to_thread(self.index.query, vector=query_vector, top_k=top_k,
                                           namespace=self.namespace, filter=filter_query, include_metadata=True)
        return [{"score": match.score, **(match.metadata or {})} for match in response.matches]
