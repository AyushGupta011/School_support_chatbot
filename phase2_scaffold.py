import os

with open("pyproject.toml", "r") as f:
    content = f.read()

# Replace passlib[bcrypt] with passlib[argon2]
content = content.replace('"passlib[bcrypt]==1.7.4",', '"passlib[argon2]==1.7.4",\n    "argon2-cffi>=23.0.0",\n    "python-multipart>=0.0.9",\n    "fakeredis>=2.21.3",')
with open("pyproject.toml", "w") as f:
    f.write(content)

# Update seed.py to use argon2
with open("scripts/seed.py", "r") as f:
    seed_content = f.read()

seed_content = seed_content.replace('from passlib.hash import bcrypt', 'from passlib.hash import argon2')
seed_content = seed_content.replace('bcrypt.hash', 'argon2.hash')

with open("scripts/seed.py", "w") as f:
    f.write(seed_content)

files = {
    "app/core/security.py": """from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_db
from app.models.erp import User, Student
from app.core.logging import logger

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], role: str, student_id: int | None = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    if student_id is not None:
        to_encode["student_id"] = student_id
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], role: str, student_id: int | None = None, jti: str = "") -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {"exp": expire, "sub": str(subject), "role": role, "type": "refresh", "jti": jti}
    if student_id is not None:
        to_encode["student_id"] = student_id
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    return encoded_jwt

async def get_current_user_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
        if payload.get("type") == "refresh":
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

async def get_current_user_payload(payload: dict = Depends(get_current_user_token_payload)) -> dict:
    return payload

def require_role(role: str):
    def role_checker(payload: dict = Depends(get_current_user_payload)):
        if payload.get("role") != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return payload
    return role_checker

async def get_current_student(payload: dict = Depends(require_role("student"))):
    student_id = payload.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="Student ID missing in token")
    return payload
""",
    "app/core/redis.py": """import time
import uuid
from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings

# This will be replaced with fakeredis during testing
_redis_client: Optional[Redis] = None

def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client

def set_redis(client: Redis):
    global _redis_client
    _redis_client = client

async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    redis = get_redis()
    now = time.time()
    
    # Use sliding window rate limit via ZSET
    pipeline = redis.pipeline()
    pipeline.zremrangebyscore(key, 0, now - window)
    pipeline.zadd(key, {str(uuid.uuid4()): now})
    pipeline.zcard(key)
    pipeline.expire(key, window)
    results = await pipeline.execute()
    
    count = results[2]
    return count <= limit

async def mark_login_failure(ip: str, enrollment_no: str):
    redis = get_redis()
    now = time.time()
    key_ip = f"login_failures:ip:{ip}"
    key_user = f"login_failures:user:{enrollment_no}"
    
    for key in [key_ip, key_user]:
        await redis.zremrangebyscore(key, 0, now - 300) # 5 minutes window
        await redis.zadd(key, {str(uuid.uuid4()): now})
        await redis.expire(key, 300)

async def check_lockout(ip: str, enrollment_no: str) -> bool:
    redis = get_redis()
    now = time.time()
    key_ip = f"login_failures:ip:{ip}"
    key_user = f"login_failures:user:{enrollment_no}"
    
    for key in [key_ip, key_user]:
        await redis.zremrangebyscore(key, 0, now - 300)
        count = await redis.zcard(key)
        if count >= 5: # Lockout after 5 failures in 5 mins
            return True
    return False

async def clear_login_failures(ip: str, enrollment_no: str):
    redis = get_redis()
    key_ip = f"login_failures:ip:{ip}"
    key_user = f"login_failures:user:{enrollment_no}"
    await redis.delete(key_ip, key_user)

async def is_refresh_token_used(jti: str) -> bool:
    redis = get_redis()
    key = f"used_refresh:{jti}"
    return await redis.exists(key) > 0

async def mark_refresh_token_used(jti: str, expires_in: int = 86400 * 7):
    redis = get_redis()
    key = f"used_refresh:{jti}"
    await redis.setex(key, expires_in, "1")
""",
    "app/core/middleware.py": """from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 5 * 1024 * 1024): # 5MB limit
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.headers.get('content-length'):
            try:
                content_length = int(request.headers['content-length'])
                if content_length > self.max_upload_size:
                    return JSONResponse(status_code=413, content={"detail": "Payload Too Large"})
            except ValueError:
                pass
        return await call_next(request)

def setup_middlewares(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # Should be loaded from env in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
""",
    "app/api/auth.py": """from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import uuid

from app.core.db import get_db
from app.models.erp import User, Student
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.redis import check_lockout, mark_login_failure, clear_login_failures, is_refresh_token_used, mark_refresh_token_used
from app.core.logging import logger
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "127.0.0.1"
    
    if await check_lockout(ip, form_data.username):
        logger.warning({"event": "auth.lockout", "ip": ip})
        raise HTTPException(status_code=429, detail="Too many failed attempts. Locked out.")

    stmt = select(User).where(User.enrollment_no == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        await mark_login_failure(ip, form_data.username)
        logger.warning({"event": "auth.failure", "ip": ip, "reason": "invalid_credentials"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect enrollment number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    await clear_login_failures(ip, form_data.username)
    
    student_id = None
    if user.role == "student":
        stmt_st = select(Student).where(Student.user_id == user.id)
        result_st = await db.execute(stmt_st)
        student = result_st.scalar_one_or_none()
        if student:
            student_id = student.id
            
    access_token = create_access_token(subject=user.enrollment_no, role=user.role, student_id=student_id)
    jti = str(uuid.uuid4())
    refresh_token = create_refresh_token(subject=user.enrollment_no, role=user.role, student_id=student_id, jti=jti)
    
    logger.info({"event": "auth.success", "ip": ip, "role": user.role})
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh")
async def refresh(request: Request, refresh_token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise credentials_exception
            
        jti = payload.get("jti")
        if not jti:
            raise credentials_exception
            
        if await is_refresh_token_used(jti):
            logger.warning({"event": "auth.refresh_reuse_detected"})
            # In a real app we might revoke all tokens for this user.
            raise credentials_exception
            
        await mark_refresh_token_used(jti)
        
        # Issue new tokens
        subject = payload.get("sub")
        role = payload.get("role")
        student_id = payload.get("student_id")
        
        new_access_token = create_access_token(subject=subject, role=role, student_id=student_id)
        new_jti = str(uuid.uuid4())
        new_refresh_token = create_refresh_token(subject=subject, role=role, student_id=student_id, jti=new_jti)
        
        return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
    except JWTError:
        raise credentials_exception
""",
    "app/api/me.py": """from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import get_db
from app.models.erp import Student
from app.core.security import get_current_student

router = APIRouter(prefix="/me", tags=["me"])

@router.get("/")
async def get_my_profile(payload: dict = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    student_id = payload.get("student_id")
    stmt = select(Student).where(Student.id == student_id)
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    
    if not student:
        return {"error": "Student not found"}
        
    return {
        "id": student.id,
        "name": student.name,
        "department": student.department,
        "semester": student.semester,
        "enrollment_no": payload.get("sub")
    }
""",
    "app/api/__init__.py": "",
    "tests/test_auth.py": """import pytest
import datetime
from httpx import AsyncClient, ASGITransport
import fakeredis.aioredis
from jose import jwt

from app.main import app
from app.core.redis import set_redis
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.base import Base
from app.models.erp import User, Student
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.db import get_db

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
        new_refresh = res2.json()["refresh_token"]
        
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
""",
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Scaffold Phase 2 files created.")
