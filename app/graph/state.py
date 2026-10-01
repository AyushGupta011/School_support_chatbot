import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    student_id: int | None
    role: str
    intent: str | None
    retrieved_docs: list[Any]
    confidence: float
    tool_results: list[dict]
    retry_count: int
    cache_hit: bool
    final_answer: str
