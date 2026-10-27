import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import OpenAIEmbeddings

from app.core.db import AsyncSessionLocal
from app.rag.ingest import ingest_documents


async def main():
    # Setup dummy embeddings if API key is not present, for CI/CD
    class DummyEmbeddings:
        def embed_query(self, text): return [0.1]*1536
        def embed_documents(self, texts): return [[0.1]*1536 for _ in texts]
        
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        embeddings = OpenAIEmbeddings()
    else:
        embeddings = DummyEmbeddings()
        
    async with AsyncSessionLocal() as session:
        await ingest_documents(session, embeddings, "data/docs/")
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
