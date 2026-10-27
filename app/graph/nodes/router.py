from pydantic import BaseModel, Field

from app.graph.state import GraphState
from app.graph.guardrails import guardrails_in

class IntentClassification(BaseModel):
    intent: str = Field(description="One of: personal_data, knowledge, chitchat, unknown")

async def classify_intent_node(state: GraphState, llm) -> dict:
    guardrails_in(state["messages"])
    
    last_msg = state["messages"][-1].content
    
    prompt = f"""Classify the user's intent based on their message.
- personal_data: Queries about their own attendance, marks, fees, timetable, or student actions (leave, fee receipts, appointments).
- knowledge: Queries about university rules, fees structure, curriculum, infrastructure, faculty.
- chitchat: Greetings, thanks, or general conversation.
- unknown: Anything else not related to the university.

Message: {last_msg}
"""
    try:
        structured_llm = llm.with_structured_output(IntentClassification)
        if hasattr(structured_llm, "ainvoke"):
            res = await structured_llm.ainvoke(prompt)
        else:
            res = structured_llm.invoke(prompt)
        return {"intent": getattr(res, "intent", "knowledge")}
    except Exception:
        # Fallback keyword-based routing if LLM structured output fails
        lower_msg = str(last_msg).lower()
        if any(w in lower_msg for w in ["attendance", "fee", "fees", "mark", "marks", "timetable", "schedule", "leave", "appointment"]):
            return {"intent": "personal_data"}
        elif any(w in lower_msg for w in ["hi", "hello", "hey", "good morning", "thanks", "thank you"]):
            return {"intent": "chitchat"}
        return {"intent": "knowledge"}
