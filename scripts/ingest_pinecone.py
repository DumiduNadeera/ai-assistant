import asyncio
from app.pinecone_store import PineconeStore
from app.retrieval import load_documents


async def main() -> None:
    store = PineconeStore()
    documents = load_documents()
    await store.upsert(documents)
    print(f"Upserted {len(documents)} documents into the configured namespace.")


if __name__ == "__main__":
    asyncio.run(main())
