import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.erp import Student, User


@pytest.fixture
async def setup_api_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_db():
        async with SessionLocal() as session:
            yield session
            
    app.dependency_overrides[get_db] = override_get_db
    
    async with SessionLocal() as session:
        u = User(enrollment_no="demo_student_1", password_hash=get_password_hash("demopass"), role="student")
        u2 = User(enrollment_no="admin1", password_hash=get_password_hash("adminpass"), role="admin")
        session.add_all([u, u2])
        await session.commit()
        s = Student(user_id=u.id, name="Demo Student", department="CS", semester=1)
        session.add(s)
        await session.commit()
        
    yield
    
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_admin_enforcement(setup_api_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # student login
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        token = res.json()["access_token"]
        
        # admin route should fail for student
        res2 = await client.post("/admin/ingest", headers={"Authorization": f"Bearer {token}"})
        assert res2.status_code == 403
        
        # admin login
        res3 = await client.post("/auth/login", data={"username": "admin1", "password": "adminpass"})
        admin_token = res3.json()["access_token"]
        
        # admin route succeeds
        res4 = await client.post("/admin/ingest", headers={"Authorization": f"Bearer {admin_token}"})
        assert res4.status_code == 200

@pytest.mark.asyncio
async def test_chat_rate_limit(setup_api_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        token = res.json()["access_token"]
        
        # exceed 20 limits
        for i in range(20):
             await client.post("/chat/", headers={"Authorization": f"Bearer {token}"}, json={"message": "hi"})
             
        # 21st should fail
        res2 = await client.post("/chat/", headers={"Authorization": f"Bearer {token}"}, json={"message": "hi"})
        assert res2.status_code == 429

@pytest.mark.asyncio
async def test_sse_streaming_and_feedback(setup_api_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        token = res.json()["access_token"]
        
        # Stream chat
        from httpx_sse import aconnect_sse
        async with aconnect_sse(client, "POST", "/chat/", headers={"Authorization": f"Bearer {token}"}, json={"message": "hello"}) as event_source:
            events = [e async for e in event_source.aiter_sse()]
            assert any(e.event == "run_id" for e in events)
            
        # Feedback
        res_fb = await client.post("/chat/feedback", headers={"Authorization": f"Bearer {token}"}, json={"run_id": "fake", "score": 1})
        assert res_fb.status_code == 200
