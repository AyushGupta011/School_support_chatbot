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
        uq = UnansweredQuery(query=last_msg, student_id=student_id)
        session.add(uq)
        await session.commit()
        
    return {"final_answer": "I'm sorry, I don't have enough information to answer that. I've logged your query for the admin office."}

@traceable(name="chitchat_node")
async def chitchat_node(state: GraphState, llm) -> dict:
    res = llm.invoke([SystemMessage(content="You are a friendly university assistant. Answer politely.")] + state["messages"])
    return {"final_answer": res.content}

@traceable(name="generate_node")
async def generate_node(state: GraphState, llm) -> dict:
    docs = state["retrieved_docs"]
    context = "\n".join([f"[{c.metadata_json.get('source', 'unknown')}, {c.metadata_json.get('section', 'N/A')}] {c.content if hasattr(c, 'content') else c['content']}" for c in docs])
    
    sys_msg = SystemMessage(content=f"""Answer ONLY based on the context. Cite sources as [source, section/page].
Context:
{context}"""
    )
    
    res = llm.invoke([sys_msg] + state["messages"])
    return {"final_answer": res.content}
