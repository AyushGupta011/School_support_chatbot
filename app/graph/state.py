from typing import Any, TypedDict


class GraphState(TypedDict):
    question: str
    student_id: int | None
    role: str
    chunks: list[Any]
    answer: str
