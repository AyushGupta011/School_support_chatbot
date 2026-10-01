import datetime

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db import get_db
from app.core.redis import set_redis
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.erp import Student, User


@pytest.fixture
async def setup_auth_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_db():
        async with SessionLocal() as session:
            yield session
            
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test user
    async with SessionLocal() as session:
        u = User(enrollment_no="demo_student_1", password_hash=get_password_hash("demopass"), role="student")
        session.add(u)
        await session.commit()
        s = Student(user_id=u.id, name="Demo Student", department="CS", semester=1)
        session.add(s)
        await session.commit()
        
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    set_redis(fake_redis)
    
    yield
    
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    await fake_redis.close()

@pytest.mark.asyncio
async def test_login_success(setup_auth_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

@pytest.mark.asyncio
async def test_wrong_password_and_lockout(setup_auth_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(5):
            res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "wrong"})
            assert res.status_code == 401
            
        # 6th attempt should be locked out
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "wrong"})
        assert res.status_code == 429
        assert "Locked out" in res.json()["detail"]
        
        # Even correct password fails if locked out
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        assert res.status_code == 429

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse(setup_auth_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        refresh_token = res.json()["refresh_token"]
        
        # Refresh success
        res2 = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        assert res2.status_code == 200
        _ = res2.json()["refresh_token"]
        
        # Reuse rejected
        res3 = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        assert res3.status_code == 401

@pytest.mark.asyncio
async def test_protected_me_endpoint(setup_auth_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        access_token = res.json()["access_token"]
        
        res2 = await client.get("/me/", headers={"Authorization": f"Bearer {access_token}"})
        assert res2.status_code == 200
        assert res2.json()["enrollment_no"] == "demo_student_1"
        assert res2.json()["name"] == "Demo Student"

@pytest.mark.asyncio
async def test_expired_token(setup_auth_db):
    # Create expired token manually
    expire = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    to_encode = {"exp": expire, "sub": "demo_student_1", "role": "student"}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/me/", headers={"Authorization": f"Bearer {encoded_jwt}"})
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_tampered_token(setup_auth_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        access_token = res.json()["access_token"]
        
        # Tamper token signature
        tampered = access_token[:-5] + "aaaaa"
        res2 = await client.get("/me/", headers={"Authorization": f"Bearer {tampered}"})
        assert res2.status_code == 401

@pytest.mark.asyncio
async def test_role_enforcement(setup_auth_db):
    # Create faculty token manually
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": "faculty_1", "role": "faculty"}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # /me is restricted to 'student' role
        res = await client.get("/me/", headers={"Authorization": f"Bearer {encoded_jwt}"})
        assert res.status_code == 403
        assert "Not enough permissions" in res.json()["detail"]
