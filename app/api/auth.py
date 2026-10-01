import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.logging import logger
from app.core.redis import (
    check_lockout,
    clear_login_failures,
    is_refresh_token_used,
    mark_login_failure,
    mark_refresh_token_used,
)
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.erp import Student, User

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
