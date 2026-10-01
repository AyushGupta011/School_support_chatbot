from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models.erp import Attendance, Fee, Timetable, Mark, Enrollment, Course

class ERPRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_attendance_for_student(self, student_id: int):
        stmt = select(Attendance, Course).join(Course, Attendance.course_id == Course.id).where(Attendance.student_id == student_id)
        result = await self.session.execute(stmt)
        return result.all()
        
    async def get_fees_for_student(self, student_id: int):
        stmt = select(Fee).where(Fee.student_id == student_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
        
    async def get_timetable_for_student(self, student_id: int):
        stmt = select(Timetable, Course).join(Course, Timetable.course_id == Course.id).join(Enrollment, Enrollment.course_id == Course.id).where(Enrollment.student_id == student_id)
        result = await self.session.execute(stmt)
        return result.all()
        
    async def get_marks_for_student(self, student_id: int):
        stmt = select(Mark, Course).join(Course, Mark.course_id == Course.id).where(Mark.student_id == student_id)
        result = await self.session.execute(stmt)
        return result.all()
