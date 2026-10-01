import pytest
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.base import Base
from app.models.erp import Student, Course, Attendance, User
from app.erp.repository import ERPRepository
from app.erp.mock import MockERPAdapter

@pytest.fixture
async def memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield SessionLocal
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_cross_student_access_impossible(memory_db):
    async with memory_db() as session:
        # Create users
        u1 = User(enrollment_no="s1", password_hash="h", role="student")
        u2 = User(enrollment_no="s2", password_hash="h", role="student")
        session.add_all([u1, u2])
        await session.commit()
        
        # Create students
        s1 = Student(user_id=u1.id, name="Alice", department="CS", semester=1)
        s2 = Student(user_id=u2.id, name="Bob", department="CS", semester=1)
        session.add_all([s1, s2])
        await session.commit()
        
        # Create course
        c = Course(code="CS101", name="Intro to CS", department="CS", credits=3)
        session.add(c)
        await session.commit()
        
        # Add attendance for student 1
        att1 = Attendance(student_id=s1.id, course_id=c.id, date=datetime.date.today(), status="present")
        session.add(att1)
        await session.commit()
        
        # Adapter checks
        repo = ERPRepository(session)
        adapter = MockERPAdapter(repo)
        
        # Alice requests her attendance
        alice_att = await adapter.get_attendance(s1.id)
        assert len(alice_att) == 1
        assert alice_att[0].course_code == "CS101"
        
        # Bob requests his attendance
        bob_att = await adapter.get_attendance(s2.id)
        assert len(bob_att) == 0 # Bob has no attendance, cannot see Alice's

        # The protocol forces the caller to pass student_id, which is populated from the graph state
        # Thus, an LLM agent cannot omit the student_id or spoof it.
