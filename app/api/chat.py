import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.db import get_db
from app.core.security import get_current_student
from app.graph.builder import build_graph

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
async def chat_endpoint(request: Request, payload: dict = Depends(get_current_student), db = Depends(get_db)):
    body = await request.json()
    msg = body.get("message", "")
    
    student_id = payload.get("student_id")
    
    llm = ChatOpenAI(temperature=0, streaming=True)
    embeddings = OpenAIEmbeddings()
    
    graph = build_graph(llm, embeddings)
    
    config = {
        "configurable": {
            "session": db,
            "student_id": student_id,
            "thread_id": str(student_id) # Example checkpointer thread
        },
        "tags": ["intent_pending", "env_prod", "route_chat"],
        "metadata": {
            "student_hash": str(hash(student_id))
        }
    }
    
    async def event_generator():
        try:
            async for event in graph.astream_events({"messages": [HumanMessage(content=msg)], "student_id": student_id, "role": payload.get("role")}, config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    yield json.dumps({"token": event["data"]["chunk"].content}) + "\n"
            
            state = await graph.aget_state(config)
            yield json.dumps({"final_answer": state.values.get("final_answer")}) + "\n"
        except Exception as e:  # noqa: BLE001
            yield json.dumps({"error": str(e)}) + "\n"
            
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
