from pydantic import BaseModel
from typing import List, Optional
import datetime

class AttendanceRecord(BaseModel):
    course_code: str
    course_name: str
    date: datetime.date
    status: str

class FeeStatus(BaseModel):
    term: str
    amount_due: float
    amount_paid: float
    due_date: datetime.date
    status: str

class TimetableSession(BaseModel):
    course_code: str
    course_name: str
    day_of_week: str
    start_time: str
    end_time: str
    room: str

class MarkRecord(BaseModel):
    course_code: str
    course_name: str
    exam_type: str
    score: float
    max_score: float
