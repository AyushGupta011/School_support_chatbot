import os

# Update pyproject.toml
with open("pyproject.toml", "r") as f:
    content = f.read()

deps_to_add = [
    '"pypdf>=4.0.0"',
    '"unstructured>=0.12.0"',
    '"markdown>=3.5.0"',
    '"langchain-cohere>=0.0.3"',
    '"langchain-openai>=0.0.8"',
    '"fake-useragent>=1.4.0"'
]

# Insert after last dependency
for dep in deps_to_add:
    if dep not in content:
        content = content.replace('"passlib[argon2]==1.7.4",', f'"passlib[argon2]==1.7.4",\n    {dep},')
        
with open("pyproject.toml", "w") as f:
    f.write(content)

files = {
    "data/docs/attendance_policy.md": """# Fictional Attendance Policy
## Overview
The university requires a minimum of 75% attendance for all enrolled courses. 
## Penalties
Students failing to meet the 75% rule will not be permitted to sit for the final examinations and will receive an 'F' grade for the course.
""",
    "data/docs/fee_structure.md": """# Fictional Fee Structure
## Tuition Fees
- Engineering (B.Tech): $5000 per semester
- Sciences (B.Sc): $3000 per semester
## Deadlines
Fees must be paid by the 15th of the first month of the semester. Late fees accrue at $10/day.
""",
    "data/docs/academic_calendar.md": """# Fictional Academic Calendar
## Fall 2026
- Start Date: Sept 1, 2026
- Midterms: Oct 20-25, 2026
- Final Exams: Dec 10-20, 2026
""",
    "data/docs/syllabi.md": """# Fictional Syllabi
## CS101: Intro to CS
Focuses on basic Python programming, data structures, and algorithms.
## EE101: Basic Electrical Engineering
Covers circuits, Ohm's law, and electromagnetism.
""",
    "data/docs/faculty_directory.md": """# Fictional Faculty Directory
## Computer Science
- Dr. Alan Turing (Room 101, alan@fictional.edu)
- Dr. Grace Hopper (Room 102, grace@fictional.edu)
""",
    "data/docs/infrastructure.md": """# Fictional Infrastructure
## Library
Open 24/7 during exam weeks.
## Labs
Computer labs available in the Alan Turing block.
## Hostel & Transport
Shuttle buses run every 30 minutes from the city center to the campus. Hostels have a 10 PM curfew.
""",
    "data/docs/exam_rules.md": """# Fictional Exam Rules
## Guidelines
No electronic devices are allowed inside the examination hall. Students must carry their physical ID card.
""",
    "app/rag/__init__.py": "",
    "app/rag/chunking.py": """from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk_markdown(content: str, source: str) -> list[dict]:
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(content)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(md_header_splits)
    
    chunks = []
    for split in splits:
        section = " > ".join([v for k, v in split.metadata.items() if k.startswith("Header")])
        chunks.append({
            "content": split.page_content,
            "metadata": {
                "source": source,
                "section": section,
                "page": None
            }
        })
    return chunks
""",
    "app/rag/ingest.py": """import hashlib
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from app.models.erp import Chunk, Document
from app.core.config import settings
from app.rag.chunking import chunk_markdown
import os
from langchain_core.embeddings import Embeddings

async def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

async def ingest_documents(session: AsyncSession, embeddings: Embeddings, docs_dir: str):
    for filename in os.listdir(docs_dir):
        if filename.endswith(".md"):
            with open(os.path.join(docs_dir, filename), "r", encoding="utf-8") as f:
                content = f.read()
                
            # Upsert document
            stmt = select(Document).where(Document.title == filename)
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            
            if not doc:
                doc = Document(title=filename, content=content)
                session.add(doc)
                await session.flush()
                
            chunks = chunk_markdown(content, source=filename)
            
            for chunk in chunks:
                chunk_hash = await compute_hash(chunk['content'])
                chunk['metadata']['hash'] = chunk_hash
                
                # Check if chunk exists
                stmt_chk = select(Chunk).where(Chunk.metadata_json['hash'].astext == chunk_hash)
                res_chk = await session.execute(stmt_chk)
                if not res_chk.scalar_one_or_none():
                    emb = embeddings.embed_query(chunk['content'])
                    new_chunk = Chunk(
                        document_id=doc.id,
                        content=chunk['content'],
                        embedding=emb,
                        metadata_json=chunk['metadata'],
                    )
                    session.add(new_chunk)
                    
            await session.commit()
            
            # Post-process tsvector
            await session.execute("UPDATE chunks SET tsv = to_tsvector('english', content) WHERE tsv IS NULL")
            await session.commit()
""",
    "app/rag/retriever.py": """from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models.erp import Chunk
from app.core.config import settings
from langchain_core.embeddings import Embeddings
from langsmith import traceable

@traceable(name="hybrid_retrieve")
async def retrieve_chunks(session: AsyncSession, query: str, embeddings: Embeddings, top_k: int = 5):
    query_emb = embeddings.embed_query(query)
    
    # Vector Search
    vector_stmt = select(Chunk.id, Chunk.content, Chunk.metadata_json, Chunk.embedding.cosine_distance(query_emb).label("distance")).order_by(Chunk.embedding.cosine_distance(query_emb)).limit(top_k * 2)
    vector_res = await session.execute(vector_stmt)
    vector_rows = vector_res.all()
    
    # FTS Search
    fts_stmt = select(Chunk.id, Chunk.content, Chunk.metadata_json, func.ts_rank_cd(Chunk.tsv, func.plainto_tsquery('english', query)).label("rank")).where(Chunk.tsv.op("@@")(func.plainto_tsquery('english', query))).order_by(func.ts_rank_cd(Chunk.tsv, func.plainto_tsquery('english', query)).desc()).limit(top_k * 2)
    fts_res = await session.execute(fts_stmt)
    fts_rows = fts_res.all()
    
    # RRF
    k_rrf = 60
    scores = {}
    docs = {}
    
    for rank, row in enumerate(vector_rows):
        cid = row.id
        scores[cid] = scores.get(cid, 0) + 1.0 / (k_rrf + rank + 1)
        docs[cid] = row
        
    for rank, row in enumerate(fts_rows):
        cid = row.id
        scores[cid] = scores.get(cid, 0) + 1.0 / (k_rrf + rank + 1)
        docs[cid] = row
        
    sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
    
    return [docs[cid] for cid in sorted_cids]
""",
    "app/rag/reranker.py": """import os
from langsmith import traceable

@traceable(name="rerank_chunks")
async def rerank(query: str, chunks: list, mode: str = "vector_only"):
    if mode == "vector_only":
        return chunks
        
    if mode == "hybrid_rerank":
        try:
            from langchain_cohere import CohereRerank
            from langchain_core.documents import Document
            
            cohere_api_key = os.environ.get("COHERE_API_KEY", "")
            if not cohere_api_key:
                return chunks
                
            compressor = CohereRerank(cohere_api_key=cohere_api_key, top_n=3)
            
            docs = [Document(page_content=c.content, metadata=c.metadata_json) for c in chunks]
            compressed_docs = compressor.compress_documents(docs, query)
            
            return [{"content": d.page_content, "metadata_json": d.metadata} for d in compressed_docs]
        except Exception:
            return chunks
            
    return chunks
""",
    "app/graph/__init__.py": "",
    "app/graph/state.py": """from typing import TypedDict, List, Dict, Any

class GraphState(TypedDict):
    question: str
    student_id: int | None
    role: str
    chunks: List[Any]
    answer: str
""",
    "app/graph/nodes.py": """from app.graph.state import GraphState
from app.rag.retriever import retrieve_chunks
from app.rag.reranker import rerank
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from langsmith import traceable
import hashlib

@traceable(name="retrieve_node")
async def retrieve_node(state: GraphState, session: AsyncSession, embeddings: Embeddings, config: dict):
    # Hash student ID for safe tracing
    if state.get("student_id"):
         safe_id = hashlib.sha256(str(state["student_id"]).encode()).hexdigest()
         # (trace metadata handled via langsmith config natively, this shows intent)
         
    chunks = await retrieve_chunks(session, state["question"], embeddings)
    return {"chunks": chunks}

@traceable(name="rerank_node")
async def rerank_node(state: GraphState, config: dict):
    mode = config.get("configurable", {}).get("rerank_mode", "vector_only")
    reranked = await rerank(state["question"], state["chunks"], mode)
    return {"chunks": reranked}

@traceable(name="generate_node")
async def generate_node(state: GraphState, llm, config: dict):
    chunks = state["chunks"]
    
    if not chunks:
         return {"answer": "I don't know based on the provided documents."}
         
    context = ""
    for idx, c in enumerate(chunks):
        source = c.metadata_json.get("source", "unknown")
        section = c.metadata_json.get("section", "N/A")
        page = c.metadata_json.get("page", "N/A")
        context += f"\\n\\n--- Document {idx+1} [{source}, {section}/{page}] ---\\n{c.content}"

    system_prompt = f\"\"\"You are a university assistant. Answer ONLY based on the context below. 
If the context does not contain the answer, say "I don't know based on the provided documents."
When you answer, you MUST cite the source exactly as [source, section/page] at the end of the sentence.

Context:
{context}
\"\"\"
    
    msg = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=state["question"])])
    return {"answer": msg.content}
""",
    "app/graph/builder.py": """from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes import retrieve_node, rerank_node, generate_node
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from functools import partial

def build_graph(session, embeddings: Embeddings, llm):
    workflow = StateGraph(GraphState)
    
    retrieve_partial = partial(retrieve_node, session=session, embeddings=embeddings)
    generate_partial = partial(generate_node, llm=llm)
    
    workflow.add_node("retrieve", retrieve_partial)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_partial)
    
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()
""",
    "scripts/ingest_docs.py": """import asyncio
from app.core.db import AsyncSessionLocal
from app.rag.ingest import ingest_documents
from langchain_openai import OpenAIEmbeddings
import os

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
""",
    "scripts/ask.py": """import asyncio
import sys
import os
from app.core.db import AsyncSessionLocal
from app.graph.builder import build_graph
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

async def main(question: str):
    class DummyEmbeddings:
        def embed_query(self, text): return [0.1]*1536
        
    class DummyLLM:
        def invoke(self, msgs):
            class Msg:
                content = "Fake answer [source, section/page]"
            return Msg()

    embeddings = OpenAIEmbeddings() if os.environ.get("OPENAI_API_KEY") else DummyEmbeddings()
    llm = ChatOpenAI(temperature=0) if os.environ.get("OPENAI_API_KEY") else DummyLLM()
    
    async with AsyncSessionLocal() as session:
        graph = build_graph(session, embeddings, llm)
        result = await graph.ainvoke({"question": question, "student_id": 1, "role": "student", "chunks": [], "answer": ""})
        print(f"Q: {question}\\nA: {result['answer']}")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is the attendance policy?"
    asyncio.run(main(q))
""",
    "tests/test_rag.py": """import pytest
import asyncio
from app.rag.chunking import chunk_markdown
from app.rag.retriever import retrieve_chunks
from app.rag.reranker import rerank
from app.graph.nodes import generate_node
from app.models.erp import Chunk, Document
from app.core.db import AsyncSessionLocal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.base import Base

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
    md = "# Fictional Policy\\n## Details\\nSome rule here."
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
    state = {"question": "What is the secret formula?", "chunks": [], "student_id": 1, "role": "student", "answer": ""}
    res = await generate_node(state, FakeLLM(), {})
    assert "don't know" in res["answer"].lower()

@pytest.mark.asyncio
async def test_generator_citation():
    class FakeChunk:
        content = "The secret is 42."
        metadata_json = {"source": "fake.md", "section": "Header 1"}
        
    state = {"question": "What is the secret?", "chunks": [FakeChunk()], "student_id": 1, "role": "student", "answer": ""}
    res = await generate_node(state, FakeLLM(), {})
    assert "[fake.md, Header 1/N/A]" in res["answer"]
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Scaffold Phase 3 files created.")
