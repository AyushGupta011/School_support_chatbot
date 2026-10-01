from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str | Any, role: str, student_id: int | None = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    if student_id is not None:
        to_encode["student_id"] = student_id
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    return encoded_jwt

def create_refresh_token(subject: str | Any, role: str, student_id: int | None = None, jti: str = "") -> str:
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
