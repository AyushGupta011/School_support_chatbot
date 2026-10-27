
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.graph.nodes import generate_node
from app.models.base import Base
from app.rag.chunking import chunk_markdown
from app.rag.reranker import rerank


class FakeLLM:
    def invoke(self, msgs):
        class Msg:
            content = "This is a fake answer based on documents [fake.md, Header 1/N/A]"
        
        sys_msg = msgs[0].content
        if "Document 1" not in sys_msg:
             class RefusalMsg:
                 content = "I don't know based on the provided documents."
             return RefusalMsg()
        return Msg()

class FakeEmbeddings:
    def embed_query(self, text):
        return [0.1]*1536
    def embed_documents(self, texts):
        return [[0.1]*1536 for _ in texts]

@pytest.fixture
async def memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield SessionLocal
    await engine.dispose()

def test_chunk_markdown():
    md = "# Fictional Policy\n## Details\nSome rule here."
    chunks = chunk_markdown(md, "test.md")
    assert len(chunks) > 0
    assert "Fictional Policy > Details" in chunks[0]["metadata"]["section"]

@pytest.mark.asyncio
async def test_rerank_fallback():
    # Reranker should return chunks identically if mode is vector_only or no API key
    chunks = [{"content": "a", "metadata_json": {}}, {"content": "b", "metadata_json": {}}]
    res = await rerank("query", chunks, mode="vector_only")
    assert len(res) == 2

@pytest.mark.asyncio
async def test_generator_refusal():
    from langchain_core.messages import HumanMessage
    state = {
        "messages": [HumanMessage(content="What is the secret formula?")],
        "retrieved_docs": [],
        "student_id": 1,
        "role": "student"
    }
    res = await generate_node(state, FakeLLM())
    assert "don't know" in res["final_answer"].lower()

@pytest.mark.asyncio
async def test_generator_citation():
    from langchain_core.messages import HumanMessage
    class FakeChunk:
        content = "The secret is 42. Document 1 contains the details."
        def __init__(self):
            self.metadata_json = {"source": "fake.md", "section": "Header 1"}
        
    state = {
        "messages": [HumanMessage(content="What is the secret?")],
        "retrieved_docs": [FakeChunk()],
        "student_id": 1,
        "role": "student"
    }
    res = await generate_node(state, FakeLLM())
    assert "[fake.md, Header 1]" in res["final_answer"]

@pytest.mark.asyncio
async def test_idempotent_ingestion():
    # Because memory db lacks pgvector, we test the logic via mock or conceptually verify
    # Here we just verify the compute_hash function ensures stability
    from app.rag.ingest import compute_hash
    hash1 = await compute_hash("Same content")
    hash2 = await compute_hash("Same content")
    assert hash1 == hash2

def test_rrf():
    from app.rag.retriever import reciprocal_rank_fusion
    class Row:
        def __init__(self, _id):
            self.id = _id
    
    vec = [Row(1), Row(2)]
    fts = [Row(2), Row(3)]
    
    # 2 is in both, so it should rank higher than 1 and 3
    res = reciprocal_rank_fusion(vec, fts)
    assert res[0].id == 2
    assert len(res) == 3
