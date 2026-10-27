import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from langchain_core.messages import HumanMessage
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client as LangSmithClient
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.db import AsyncSessionLocal, get_db
from app.core.redis import check_rate_limit
from app.core.security import get_current_student
from app.graph.builder import build_graph
from app.models.erp import ChatMessage, ChatSession, Feedback

router = APIRouter(prefix="/chat", tags=["chat"])
ls_client = LangSmithClient() if os.environ.get("LANGCHAIN_API_KEY") else None

# In-memory checkpointer for stateful multi-turn conversation memory
checkpointer = MemorySaver()

class CreateSessionRequest(BaseModel):
    title: str = "New Conversation"

@router.get("/sessions")
async def list_sessions(payload: dict = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    student_id = payload.get("student_id")
    stmt = (
        select(ChatSession)
        .where(ChatSession.student_id == student_id)
        .order_by(ChatSession.updated_at.desc())
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]

@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest = CreateSessionRequest(),
    payload: dict = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    student_id = payload.get("student_id")
    new_session = ChatSession(
        id=str(uuid.uuid4()),
        student_id=student_id,
        title=body.title
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return {"id": new_session.id, "title": new_session.title}

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    payload: dict = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    student_id = payload.get("student_id")
    stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.student_id == student_id)
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
        
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.delete(session_obj)
    await db.commit()
    return {"status": "ok", "deleted_session_id": session_id}

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    payload: dict = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    student_id = payload.get("student_id")
    stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.student_id == student_id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")
        
    stmt_msgs = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    res_msgs = await db.execute(stmt_msgs)
    messages = res_msgs.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "run_id": m.run_id,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]

@router.get("/history")
async def chat_history(
    session_id: str | None = None,
    payload: dict = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    student_id = payload.get("student_id")
    target_session_id = session_id
    
    if not target_session_id:
        # Fetch the most recent session
        stmt = (
            select(ChatSession)
            .where(ChatSession.student_id == student_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        latest = res.scalar_one_or_none()
        if latest:
            target_session_id = latest.id
            
    if not target_session_id:
        return {"session_id": None, "messages": []}
        
    stmt_msgs = (
        select(ChatMessage)
        .where(ChatMessage.session_id == target_session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    res_msgs = await db.execute(stmt_msgs)
    messages = res_msgs.scalars().all()
    return {
        "session_id": target_session_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "run_id": m.run_id,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    }

@router.post("/")
async def chat_endpoint(request: Request, payload: dict = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    body = await request.json()
    msg = body.get("message", "").strip()
    session_id = body.get("session_id")
    student_id = payload.get("student_id")
    
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    if not await check_rate_limit(f"chat:{student_id}", limit=20, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a minute.")
        
    # Ensure active session exists
    if not session_id:
        # Check for recent session or create new
        stmt_sess = select(ChatSession).where(ChatSession.student_id == student_id).order_by(ChatSession.updated_at.desc()).limit(1)
        res_sess = await db.execute(stmt_sess)
        existing_sess = res_sess.scalar_one_or_none()
        if existing_sess:
            session_id = existing_sess.id
        else:
            new_sess = ChatSession(id=str(uuid.uuid4()), student_id=student_id, title=msg[:30] + ("..." if len(msg) > 30 else ""))
            db.add(new_sess)
            await db.commit()
            session_id = new_sess.id
    else:
        # Check title update if still default
        stmt_chk = select(ChatSession).where(ChatSession.id == session_id)
        res_chk = await db.execute(stmt_chk)
        sess_obj = res_chk.scalar_one_or_none()
        if sess_obj and (sess_obj.title == "New Conversation" or not sess_obj.title):
            sess_obj.title = msg[:35] + ("..." if len(msg) > 35 else "")
            await db.commit()

    # Save user message to database
    user_msg_record = ChatMessage(session_id=session_id, role="user", content=msg)
    db.add(user_msg_record)
    await db.commit()
    
    from app.core.llm import get_llm
    llm = get_llm()
    
    # Embeddings fallback
    embeddings = None
    if os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_API_KEY") != "your_openai_api_key":
        try:
            embeddings = OpenAIEmbeddings()
        except Exception:
            embeddings = None
            
    if not embeddings:
        from langchain_community.embeddings import FakeEmbeddings
        embeddings = FakeEmbeddings(size=1536)
    
    run_id = str(uuid.uuid4())
    
    async def event_generator():
        accumulated_tokens = []
        try:
            # Build graph with persistent checkpointer and thread_id
            graph = build_graph(llm, embeddings, checkpointer=checkpointer)
            config = {
                "configurable": {
                    "session": db,
                    "student_id": student_id,
                    "thread_id": str(session_id)
                },
                "run_id": run_id,
                "tags": ["chat"],
                "metadata": {"student_id": str(student_id), "session_id": str(session_id)}
            }
            
            yield {"event": "run_id", "data": json.dumps({"run_id": run_id, "session_id": session_id})}
            
            initial_input = {
                "messages": [HumanMessage(content=msg)],
                "student_id": student_id,
                "role": payload.get("role", "student")
            }
            
            async for event in graph.astream_events(initial_input, config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    # Only stream tokens from student-facing generation nodes (not internal query rewriter or grader)
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    if node_name in ["generate", "chitchat", "validate_output"]:
                        token = event["data"]["chunk"].content
                        if token:
                            accumulated_tokens.append(token)
                            yield {"event": "token", "data": json.dumps({"token": token})}
            
            state = await graph.aget_state(config)
            final_answer = state.values.get("final_answer")
            if not final_answer and accumulated_tokens:
                final_answer = "".join(accumulated_tokens)
            if not final_answer:
                final_answer = "I have processed your request."
                
            yield {"event": "done", "data": json.dumps({"final_answer": final_answer, "session_id": session_id})}
            
            # Persist assistant response to DB
            async with AsyncSessionLocal() as save_db:
                assistant_record = ChatMessage(session_id=session_id, role="assistant", content=final_answer, run_id=run_id)
                save_db.add(assistant_record)
                await save_db.commit()
                
        except Exception as e:
            err_msg = str(e)
            yield {"event": "error", "data": json.dumps({"error": err_msg})}
            # Persist fallback message
            try:
                async with AsyncSessionLocal() as save_db:
                    assistant_record = ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content="I encountered a technical issue while processing your request. Please try again or rephrase."
                    )
                    save_db.add(assistant_record)
                    await save_db.commit()
            except Exception:
                pass
            
    return EventSourceResponse(event_generator())

@router.post("/feedback")
async def submit_feedback(request: Request, payload: dict = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    body = await request.json()
    run_id = body.get("run_id")
    score = body.get("score")  # 1 for up, 0 for down
    
    if run_id and ls_client:
        try:
            ls_client.create_feedback(run_id, key="user_score", score=score)
        except Exception:
            pass
            
    fb = Feedback(
        query=body.get("query", ""),
        response=body.get("response", ""),
        rating=score,
        comments=body.get("comments", "")
    )
    db.add(fb)
    await db.commit()
    return {"status": "ok"}
