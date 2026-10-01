import hashlib

from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.state import GraphState
from app.rag.reranker import rerank
from app.rag.retriever import retrieve_chunks


@traceable(name="retrieve_node")
async def retrieve_node(state: GraphState, session: AsyncSession, embeddings: Embeddings, config: dict):
    # Hash student ID for safe tracing
    if state.get("student_id"):
         _safe_id = hashlib.sha256(str(state["student_id"]).encode()).hexdigest()
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
        context += f"\n\n--- Document {idx+1} [{source}, {section}/{page}] ---\n{c.content}"

    system_prompt = f"""You are a university assistant. Answer ONLY based on the context below. 
If the context does not contain the answer, say "I don't know based on the provided documents."
When you answer, you MUST cite the source exactly as [source, section/page] at the end of the sentence.

Context:
{context}
"""
    
    msg = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=state["question"])])
    return {"answer": msg.content}
