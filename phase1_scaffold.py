import os

# Update pyproject.toml
with open("pyproject.toml", "r") as f:
    content = f.read()

if "alembic" not in content:
    content = content.replace('"structlog==24.4.0",', '"structlog==24.4.0",\n    "alembic>=1.13.0",\n    "pgvector>=0.2.0",\n    "faker>=20.0.0",')
    with open("pyproject.toml", "w") as f:
        f.write(content)

files = {
    "alembic.ini": """[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = check --fix --unsafe-fixes %(script)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""",
    "alembic/env.py": """import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.core.config import settings
from app.models.base import Base
from app.models import erp # noqa

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",
    "alembic/script.py.mako": '\"\"\"${message}\n\nRevision ID: ${up_revision}\nRevises: ${down_revision | comma,n}\nCreate Date: ${create_date}\n\n\"\"\"\nfrom typing import Sequence, Union\n\nfrom alembic import op\nimport sqlalchemy as sa\n${imports if imports else ""}\n\n# revision identifiers, used by Alembic.\nrevision: str = ${repr(up_revision)}\ndown_revision: Union[str, None] = ${repr(down_revision)}\nbranch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}\ndepends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}\n\n\ndef upgrade() -> None:\n    ${upgrades if upgrades else "pass"}\n\n\ndef downgrade() -> None:\n    ${downgrades if downgrades else "pass"}\n',
    "app/core/db.py": """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
    "app/models/__init__.py": "",
    "app/models/base.py": """from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
""",
    "app/models/erp.py": """from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
import datetime
import os

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
""",
    "app/erp/__init__.py": "",
    "app/erp/schemas.py": """from pydantic import BaseModel
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
""",
    "app/erp/adapter.py": """from typing import Protocol, List
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
""",
    "app/erp/repository.py": """from sqlalchemy.ext.asyncio import AsyncSession
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
""",
    "app/erp/mock.py": """from typing import List
from app.erp.adapter import ERPAdapter
from app.erp.schemas import AttendanceRecord, FeeStatus, TimetableSession, MarkRecord
from app.erp.repository import ERPRepository

class MockERPAdapter(ERPAdapter):
    def __init__(self, repository: ERPRepository):
        self.repository = repository
        
    async def get_attendance(self, student_id: int) -> List[AttendanceRecord]:
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
        
    async def get_fee_status(self, student_id: int) -> List[FeeStatus]:
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
        
    async def get_timetable(self, student_id: int) -> List[TimetableSession]:
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
        
    async def get_marks(self, student_id: int) -> List[MarkRecord]:
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
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Scaffold Phase 1 files created.")
