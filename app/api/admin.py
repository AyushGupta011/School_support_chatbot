import os

from fastapi import APIRouter, BackgroundTasks, Depends
from langchain_openai import OpenAIEmbeddings

from app.core.db import AsyncSessionLocal
from app.core.security import require_role
from app.rag.ingest import ingest_documents

router = APIRouter(prefix="/admin", tags=["admin"])

async def background_ingest():
    class DummyEmbeddings:
        def embed_query(self, text): return [0.1]*1536
        def embed_documents(self, texts): return [[0.1]*1536 for _ in texts]
    
    key = os.environ.get("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings() if key else DummyEmbeddings()
    
    async with AsyncSessionLocal() as session:
        await ingest_documents(session, embeddings, "data/docs/")

@router.post("/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks, payload: dict = Depends(require_role("admin"))):
    background_tasks.add_task(background_ingest)
    return {"status": "Ingestion started in background"}
