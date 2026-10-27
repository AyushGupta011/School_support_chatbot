from langchain_core.messages import SystemMessage
from langsmith import traceable

from app.graph.state import GraphState
from app.tools.student_data import tools


@traceable(name="tool_agent_node")
async def tool_agent_node(state: GraphState, llm, config) -> dict:
    llm_with_tools = llm.bind_tools(tools)
    
    # The system prompt must instruct LLM to use tools
    sys_msg = SystemMessage(content="You are a university assistant. Use the provided tools to fetch student data.")
    
    messages = [sys_msg] + list(state["messages"])
    if hasattr(llm_with_tools, "ainvoke"):
        res = await llm_with_tools.ainvoke(messages, config=config)
    else:
        res = llm_with_tools.invoke(messages, config=config)
    
    return {"messages": [res]}

@traceable(name="execute_tools_node")
async def execute_tools_node(state: GraphState, config) -> dict:
    last_msg = state["messages"][-1]
    from langchain_core.messages import ToolMessage
    
    tool_msgs = []
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        tool_map = {t.name: t for t in tools}
        for call in last_msg.tool_calls:
            tool_func = tool_map.get(call["name"])
            if tool_func:
                # We pass config so the tool can access session and student_id
                res = await tool_func.ainvoke(call["args"], config=config)
                tool_msgs.append(ToolMessage(content=str(res), tool_call_id=call["id"]))
                
    return {"messages": tool_msgs}

@traceable(name="validate_output_node")
async def validate_output_node(state: GraphState, llm) -> dict:
    # Just let LLM synthesize the final answer from the tool results
    last_msg = state["messages"][-1]
    # If the last message is a ToolMessage, we need to generate the final text
    if getattr(last_msg, "type", "") == "tool" or (hasattr(last_msg, "tool_call_id") and last_msg.tool_call_id):
        sys_msg = SystemMessage(content="Summarize the tool results into a friendly, clear response for the student.")
        messages = [sys_msg] + list(state["messages"])
        if hasattr(llm, "ainvoke"):
            res = await llm.ainvoke(messages)
        else:
            res = llm.invoke(messages)
        return {"final_answer": res.content}
    else:
        return {"final_answer": getattr(last_msg, "content", str(last_msg))}
