import re

from langchain_core.messages import HumanMessage


def guardrails_in(messages: list) -> bool:
    if not messages:
        return True
    last_msg = messages[-1]
    if isinstance(last_msg, HumanMessage):
        content = last_msg.content
        if len(content) > 1000:
             raise ValueError("Input too long")
             
        # Simple injection pattern checks
        injection_patterns = [
            r"(?i)ignore previous instructions",
            r"(?i)system prompt",
            r"(?i)you are now",
            r"(?i)bypass guardrails"
        ]
        for p in injection_patterns:
            if re.search(p, content):
                raise ValueError("Potential prompt injection detected")
    return True

def guardrails_out(answer: str, current_student_id: int | None) -> bool:
    # Ensure answer does not contain other student IDs
    # In our mock, IDs are like STU001
    matches = re.findall(r"STU\d{3}", answer)
    if matches:
        # If it found ANY ID, it's risky. But to be safe, we just block if it finds one that isn't the current student's?
        # Since student_id is int, maybe format it:
        sid_str = f"STU{current_student_id:03d}" if current_student_id else ""
        for m in matches:
            if m != sid_str:
                return False
                
    leaked_system_text = ["You are a university assistant", "Context:"]
    for t in leaked_system_text:
        if t in answer:
            return False
            
    return True
