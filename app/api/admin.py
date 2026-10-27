import datetime
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal, get_db
from app.core.security import require_role
from app.models.erp import Chunk, Document, Feedback, Student, UnansweredQuery
from app.rag.ingest import compute_hash, ingest_documents

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

@router.get("/unanswered")
async def list_unanswered_queries(
    status_filter: str = Query("pending", alias="status"),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_role("admin"))
):
    stmt = select(UnansweredQuery)
    if status_filter != "all":
        stmt = stmt.where(UnansweredQuery.status == status_filter)
    stmt = stmt.order_by(UnansweredQuery.created_at.desc())
    
    result = await db.execute(stmt)
    queries = result.scalars().all()
    
    return [
        {
            "id": q.id,
            "query": q.query,
            "student_id": q.student_id,
            "status": q.status,
            "resolution": q.resolution,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "resolved_at": q.resolved_at.isoformat() if q.resolved_at else None,
        }
        for q in queries
    ]

class ResolveQueryRequest(BaseModel):
    resolution: str
    add_to_knowledge_base: bool = False

@router.post("/unanswered/{query_id}/resolve")
async def resolve_unanswered_query(
    query_id: int,
    body: ResolveQueryRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_role("admin"))
):
    stmt = select(UnansweredQuery).where(UnansweredQuery.id == query_id)
    res = await db.execute(stmt)
    uq = res.scalar_one_or_none()
    
    if not uq:
        raise HTTPException(status_code=404, detail="Unanswered query not found")
        
    uq.status = "resolved"
    uq.resolution = body.resolution
    uq.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    
    # Human-in-the-loop learning: auto-ingest Q&A pair into knowledge base
    if body.add_to_knowledge_base:
        doc_title = f"FAQ_Resolution_{uq.id}.md"
        content = f"# Frequently Asked Question: {uq.query}\n\n**Official Answer:** {body.resolution}\n"
        
        doc = Document(title=doc_title, content=content)
        db.add(doc)
        await db.flush()
        
        # Ingest chunk
        class DummyEmbeddings:
            def embed_query(self, text): return [0.1]*1536
        key = os.environ.get("OPENAI_API_KEY")
        embeddings = OpenAIEmbeddings() if key else DummyEmbeddings()
        
        emb = embeddings.embed_query(content)
        chunk_hash = await compute_hash(content)
        chunk = Chunk(
            document_id=doc.id,
            content=content,
            embedding=emb,
            metadata_json={"source": doc_title, "section": "Admin Resolution", "hash": chunk_hash}
        )
        db.add(chunk)
        await db.commit()
        await db.execute(text("UPDATE chunks SET tsv = to_tsvector('english', content) WHERE id = :cid"), {"cid": chunk.id})
    else:
        await db.commit()
        
    return {"status": "ok", "message": "Query resolved successfully", "added_to_kb": body.add_to_knowledge_base}

@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_role("admin"))
):
    student_count = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    chunk_count = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0
    unanswered_pending = (await db.execute(select(func.count(UnansweredQuery.id)).where(UnansweredQuery.status == "pending"))).scalar() or 0
    feedback_avg = (await db.execute(select(func.avg(Feedback.rating)))).scalar() or 1.0
    
    return {
        "students": student_count,
        "documents": doc_count,
        "chunks": chunk_count,
        "pending_queries": unanswered_pending,
        "satisfaction_score": round(float(feedback_avg) * 100, 1)
    }
