from functools import partial

from langgraph.graph import END, StateGraph

from app.graph.cache import store_in_cache
from app.graph.guardrails import guardrails_in, guardrails_out
from app.graph.nodes.general import chitchat_node, generate_node, human_handoff_node
from app.graph.nodes.knowledge import (
    cache_lookup_node,
    grade_node,
    rerank_node,
    retrieve_node,
    rewrite_node,
)
from app.graph.nodes.personal import execute_tools_node, tool_agent_node, validate_output_node
from app.graph.nodes.router import classify_intent_node
from app.graph.state import GraphState


def route_intent(state: GraphState):
    intent = state.get("intent")
    if intent == "personal_data": return "tool_agent"
    if intent == "knowledge": return "cache_lookup"
    if intent == "chitchat": return "chitchat"
    return "human_handoff"

def route_cache(state: GraphState):
    if state.get("cache_hit"): return "guardrails_out"
    return "retrieve"

def route_grade(state: GraphState):
    if state.get("confidence") >= 0.7:
        return "generate"
    if state.get("retry_count", 0) < 1:
        return "rewrite"
    return "human_handoff"

def route_tools(state: GraphState):
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "execute_tools"
    return "validate_output"

def build_graph(llm, embeddings, checkpointer=None):
    workflow = StateGraph(GraphState)
    
    # Input Guardrails wrapper
    async def guardrails_in_node(state: GraphState):
        guardrails_in(state["messages"])
        return {}
        
    workflow.add_node("guardrails_in", guardrails_in_node)
    
    workflow.add_node("classify_intent", partial(classify_intent_node, llm=llm))
    
    # Personal
    workflow.add_node("tool_agent", partial(tool_agent_node, llm=llm))
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("validate_output", partial(validate_output_node, llm=llm))
    
    # Knowledge
    workflow.add_node("cache_lookup", partial(cache_lookup_node, embeddings=embeddings))
    workflow.add_node("retrieve", partial(retrieve_node, embeddings=embeddings))
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("grade", partial(grade_node, llm=llm))
    workflow.add_node("rewrite", partial(rewrite_node, llm=llm))
    
    # General
    workflow.add_node("chitchat", partial(chitchat_node, llm=llm))
    workflow.add_node("human_handoff", human_handoff_node)
    workflow.add_node("generate", partial(generate_node, llm=llm))
    
    # Output guardrails and cache
    async def final_node(state: GraphState, config):
        ans = state["final_answer"]
        sid = state.get("student_id")
        if not guardrails_out(ans, sid):
            ans = "I cannot provide this answer due to safety guardrails."
            
        # Store in cache only if it was knowledge and high confidence
        if state.get("intent") == "knowledge" and state.get("confidence", 0) >= 0.7 and not state.get("cache_hit"):
            last_msg = state["messages"][0].content if state["messages"] else ""
            await store_in_cache(last_msg, ans, embeddings)
            
        return {"final_answer": ans}
        
    workflow.add_node("guardrails_out", final_node)

    # Edges
    workflow.set_entry_point("guardrails_in")
    workflow.add_edge("guardrails_in", "classify_intent")
    
    workflow.add_conditional_edges("classify_intent", route_intent, {
        "tool_agent": "tool_agent",
        "cache_lookup": "cache_lookup",
        "chitchat": "chitchat",
        "human_handoff": "human_handoff"
    })
    
    # Personal path
    workflow.add_conditional_edges("tool_agent", route_tools, {
        "execute_tools": "execute_tools",
        "validate_output": "validate_output"
    })
    workflow.add_edge("execute_tools", "validate_output") # Simplified loop: single turn
    workflow.add_edge("validate_output", "guardrails_out")
    
    # Knowledge path
    workflow.add_conditional_edges("cache_lookup", route_cache, {
        "guardrails_out": "guardrails_out",
        "retrieve": "retrieve"
    })
    
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "grade")
    workflow.add_conditional_edges("grade", route_grade, {
        "generate": "generate",
        "rewrite": "rewrite",
        "human_handoff": "human_handoff"
    })
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", "guardrails_out")
    
    # Others
    workflow.add_edge("chitchat", "guardrails_out")
    workflow.add_edge("human_handoff", "guardrails_out")
    workflow.add_edge("guardrails_out", END)
    
    return workflow.compile(checkpointer=checkpointer)
