from langchain_core.messages import SystemMessage
from langsmith import traceable

from app.graph.state import GraphState
from app.models.erp import UnansweredQuery


@traceable(name="human_handoff_node")
async def human_handoff_node(state: GraphState, config) -> dict:
    session = config["configurable"]["session"]
    student_id = state.get("student_id")
    last_msg = state["messages"][-1].content
    
    if student_id:
        try:
            uq = UnansweredQuery(query=last_msg, student_id=student_id)
            session.add(uq)
            await session.commit()
        except Exception:
            await session.rollback()
        
    return {"final_answer": "I'm sorry, I don't have enough information in the official documents to answer that. I've logged your query for the admissions & admin office."}

@traceable(name="chitchat_node")
async def chitchat_node(state: GraphState, llm) -> dict:
    sys_msg = SystemMessage(content="You are a friendly university assistant. Answer politely and concisely.")
    messages = [sys_msg] + list(state["messages"])
    if hasattr(llm, "ainvoke"):
        res = await llm.ainvoke(messages)
    else:
        res = llm.invoke(messages)
    return {"final_answer": res.content}

@traceable(name="generate_node")
async def generate_node(state: GraphState, llm) -> dict:
    docs = state.get("retrieved_docs", [])
    
    formatted_chunks = []
    for c in docs:
        meta = getattr(c, "metadata_json", None)
        if meta is None and isinstance(c, dict):
            meta = c.get("metadata_json", {})
        if not isinstance(meta, dict):
            meta = {}
            
        source = meta.get("source", "unknown")
        section = meta.get("section", "N/A")
        content = getattr(c, "content", None) or (c.get("content", "") if isinstance(c, dict) else str(c))
        formatted_chunks.append(f"[{source}, {section}] {content}")
        
    context = "\n".join(formatted_chunks) if formatted_chunks else "No relevant documents found."
    
    sys_msg = SystemMessage(content=f"""Answer ONLY based on the context. Cite sources as [source, section/page].
Context:
{context}"""
    )
    
    messages = [sys_msg] + list(state["messages"])
    if hasattr(llm, "ainvoke"):
        res = await llm.ainvoke(messages)
    else:
        res = llm.invoke(messages)
    return {"final_answer": res.content}
