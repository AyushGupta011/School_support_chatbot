from langchain_core.messages import HumanMessage
from langsmith import traceable
from pydantic import BaseModel, Field

from app.graph.cache import semantic_search_cache
from app.graph.state import GraphState
from app.rag.reranker import rerank
from app.rag.retriever import retrieve_chunks


@traceable(name="cache_lookup_node")
async def cache_lookup_node(state: GraphState, embeddings, config) -> dict:
    last_msg = state["messages"][-1].content
    threshold = float(config.get("configurable", {}).get("cache_threshold", 0.9))
    answer = await semantic_search_cache(last_msg, embeddings, threshold)
    if answer:
        return {"cache_hit": True, "final_answer": answer}
    return {"cache_hit": False}

@traceable(name="retrieve_node")
async def retrieve_node(state: GraphState, embeddings, config) -> dict:
    session = config["configurable"]["session"]
    last_msg = state["messages"][-1].content
    chunks = await retrieve_chunks(session, last_msg, embeddings)
    return {"retrieved_docs": chunks}

@traceable(name="rerank_node")
async def rerank_node(state: GraphState, config) -> dict:
    mode = config.get("configurable", {}).get("rerank_mode", "vector_only")
    last_msg = state["messages"][-1].content
    reranked = await rerank(last_msg, state["retrieved_docs"], mode)
    return {"retrieved_docs": reranked}

class GradeOutput(BaseModel):
    confidence: float = Field(description="Confidence score from 0.0 to 1.0 that the documents contain the answer")

@traceable(name="grade_node")
async def grade_node(state: GraphState, llm) -> dict:
    docs = state.get("retrieved_docs", [])
    if not docs:
        return {"confidence": 0.0}
        
    last_msg = state["messages"][-1].content
    chunk_texts = []
    for c in docs:
        txt = getattr(c, "content", None) or (c.get("content", "") if isinstance(c, dict) else str(c))
        chunk_texts.append(txt)
    context = "\n".join(chunk_texts)
    
    prompt = f"Does the following context contain the answer to the user's question? Context:\n{context}\nQuestion: {last_msg}"
    
    try:
        structured_llm = llm.with_structured_output(GradeOutput)
        if hasattr(structured_llm, "ainvoke"):
            res = await structured_llm.ainvoke(prompt)
        else:
            res = structured_llm.invoke(prompt)
        return {"confidence": getattr(res, "confidence", 0.8)}
    except Exception:
        # Graceful fallback if structured output fails
        return {"confidence": 0.8}

@traceable(name="rewrite_node")
async def rewrite_node(state: GraphState, llm) -> dict:
    last_msg = state["messages"][-1].content
    prompt = (
        "You are an internal database search query optimizer. "
        "Given the user question, output ONLY the concise search keywords for document retrieval. "
        "Do NOT provide explanations. Do NOT provide tips. Do NOT output multiple choices or options. "
        f"Question: {last_msg}\n"
        "Optimized query:"
    )
    if hasattr(llm, "ainvoke"):
        res = await llm.ainvoke(prompt)
    else:
        res = llm.invoke(prompt)
    
    clean_query = str(res.content).strip().split("\n")[0].replace('"', '').strip()
    if ":" in clean_query and len(clean_query.split(":")[0]) < 25:
        clean_query = clean_query.split(":", 1)[1].strip()
        
    # We replace the last message to trigger retrieval again
    new_messages = list(state["messages"][:-1]) + [HumanMessage(content=clean_query or last_msg)]
    retry_count = state.get("retry_count", 0) + 1
    
    return {"messages": new_messages, "retry_count": retry_count}

