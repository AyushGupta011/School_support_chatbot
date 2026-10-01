from functools import partial

from langchain_core.embeddings import Embeddings
from langgraph.graph import END, StateGraph

from app.graph.nodes import generate_node, rerank_node, retrieve_node
from app.graph.state import GraphState


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
