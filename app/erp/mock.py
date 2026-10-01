
from app.erp.adapter import ERPAdapter
from app.erp.repository import ERPRepository
from app.erp.schemas import AttendanceRecord, FeeStatus, MarkRecord, TimetableSession


class MockERPAdapter(ERPAdapter):
    def __init__(self, repository: ERPRepository):
        self.repository = repository
        
    async def get_attendance(self, student_id: int) -> list[AttendanceRecord]:
        records = await self.repository.get_attendance_for_student(student_id)
        return [
            AttendanceRecord(
                course_code=course.code,
                course_name=course.name,
                date=att.date,
                status=att.status
            )
            for att, course in records
        ]
        
    async def get_fee_status(self, student_id: int) -> list[FeeStatus]:
        fees = await self.repository.get_fees_for_student(student_id)
        return [
            FeeStatus(
                term=fee.term,
                amount_due=fee.amount_due,
                amount_paid=fee.amount_paid,
                due_date=fee.due_date,
                status="Paid" if fee.amount_paid >= fee.amount_due else ("Overdue" if fee.due_date < fee.due_date.__class__.today() else "Pending")
            )
            for fee in fees
        ]
        
    async def get_timetable(self, student_id: int) -> list[TimetableSession]:
        sessions = await self.repository.get_timetable_for_student(student_id)
        return [
            TimetableSession(
                course_code=course.code,
                course_name=course.name,
                day_of_week=tt.day_of_week,
                start_time=tt.start_time,
                end_time=tt.end_time,
                room=tt.room
            )
            for tt, course in sessions
        ]
        
    async def get_marks(self, student_id: int) -> list[MarkRecord]:
        marks = await self.repository.get_marks_for_student(student_id)
        return [
            MarkRecord(
                course_code=course.code,
                course_name=course.name,
                exam_type=mark.exam_type,
                score=mark.score,
                max_score=mark.max_score
            )
            for mark, course in marks
        ]
