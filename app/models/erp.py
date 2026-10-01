import datetime
import os

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    enrollment_no: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    role: Mapped[str]  # 'student', 'admin', 'faculty'

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str]
    department: Mapped[str]
    semester: Mapped[int]
    
    user = relationship("User")

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    department: Mapped[str]
    credits: Mapped[int]

class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    semester: Mapped[int]

class Attendance(Base):
    __tablename__ = "attendance"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    date: Mapped[datetime.date]
    status: Mapped[str] # 'present', 'absent'

class Fee(Base):
    __tablename__ = "fees"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    term: Mapped[str]
    amount_due: Mapped[float]
    amount_paid: Mapped[float]
    due_date: Mapped[datetime.date]

class Timetable(Base):
    __tablename__ = "timetable"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    day_of_week: Mapped[str]
    start_time: Mapped[str]
    end_time: Mapped[str]
    room: Mapped[str]

class Mark(Base):
    __tablename__ = "marks"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    exam_type: Mapped[str] # 'midterm', 'final', 'assignment'
    score: Mapped[float]
    max_score: Mapped[float]

class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str]
    department: Mapped[str]
    email: Mapped[str]
    cabin: Mapped[str]
    office_hours: Mapped[str]

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(int(os.environ.get("EMBEDDING_DIMENSION", "1536"))))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default={})
    tsv = mapped_column(TSVECTOR)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    query: Mapped[str]
    response: Mapped[str]
    rating: Mapped[int]
    comments: Mapped[str | None]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UnansweredQuery(Base):
    __tablename__ = "unanswered_queries"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    query: Mapped[str]
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
