from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_student
from app.models.erp import Student

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
