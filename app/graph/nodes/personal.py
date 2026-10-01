from langchain_core.messages import SystemMessage
from langsmith import traceable

from app.graph.state import GraphState
from app.tools.student_data import tools


@traceable(name="tool_agent_node")
async def tool_agent_node(state: GraphState, llm, config) -> dict:
    llm_with_tools = llm.bind_tools(tools)
    
    # The system prompt must instruct LLM to use tools
    sys_msg = SystemMessage(content="You are a university assistant. Use the provided tools to fetch student data.")
    
    messages = [sys_msg] + state["messages"]
    res = llm_with_tools.invoke(messages, config=config)
    
    # LangGraph will store this AIMessage. Then we execute tools.
    # For simplicity in this scaffold, we manually execute the tool call if present,
    # or just use LangGraph's ToolNode logic.
    return {"messages": [res]}

@traceable(name="execute_tools_node")
async def execute_tools_node(state: GraphState, config) -> dict:
    last_msg = state["messages"][-1]
    from langchain_core.messages import ToolMessage
    
    tool_msgs = []
    if hasattr(last_msg, "tool_calls"):
        tool_map = {t.name: t for t in tools}
        for call in last_msg.tool_calls:
            tool_func = tool_map.get(call["name"])
            if tool_func:
                # We pass config so the tool can access session and student_id
                res = await tool_func.ainvoke(call["args"], config=config)
                tool_msgs.append(ToolMessage(content=res, tool_call_id=call["id"]))
                
    return {"messages": tool_msgs}

@traceable(name="validate_output_node")
async def validate_output_node(state: GraphState, llm) -> dict:
    # Just let LLM synthesize the final answer from the tool results
    last_msg = state["messages"][-1]
    # If the last message is a ToolMessage, we need to generate the final text
    if getattr(last_msg, "type", "") == "tool":
        sys_msg = SystemMessage(content="Summarize the tool results into a friendly response.")
        res = llm.invoke([sys_msg] + state["messages"])
        return {"final_answer": res.content}
    else:
        return {"final_answer": last_msg.content}
