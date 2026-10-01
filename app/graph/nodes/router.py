from pydantic import BaseModel, Field

from app.graph.state import GraphState


class IntentClassification(BaseModel):
    intent: str = Field(description="One of: personal_data, knowledge, chitchat, unknown")

async def classify_intent_node(state: GraphState, llm) -> dict:
    last_msg = state["messages"][-1].content
    
    prompt = f"""Classify the user's intent based on their message.
- personal_data: Queries about their own attendance, marks, fees, timetable.
- knowledge: Queries about university rules, fees structure, curriculum, infrastructure, faculty.
- chitchat: Greetings, thanks, or general conversation.
- unknown: Anything else not related to the university.

Message: {last_msg}
"""
    structured_llm = llm.with_structured_output(IntentClassification)
    res = structured_llm.invoke(prompt)
    return {"intent": res.intent}
