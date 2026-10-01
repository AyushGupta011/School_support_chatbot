from typing import Protocol

from app.erp.schemas import AttendanceRecord, FeeStatus, MarkRecord, TimetableSession


class ERPAdapter(Protocol):
    async def get_attendance(self, student_id: int) -> list[AttendanceRecord]:
        ...
    
    async def get_fee_status(self, student_id: int) -> list[FeeStatus]:
        ...
        
    async def get_timetable(self, student_id: int) -> list[TimetableSession]:
        ...
        
    async def get_marks(self, student_id: int) -> list[MarkRecord]:
        ...
