from typing import Protocol, List
from app.erp.schemas import AttendanceRecord, FeeStatus, TimetableSession, MarkRecord

class ERPAdapter(Protocol):
    async def get_attendance(self, student_id: int) -> List[AttendanceRecord]:
        ...
    
    async def get_fee_status(self, student_id: int) -> List[FeeStatus]:
        ...
        
    async def get_timetable(self, student_id: int) -> List[TimetableSession]:
        ...
        
    async def get_marks(self, student_id: int) -> List[MarkRecord]:
        ...
