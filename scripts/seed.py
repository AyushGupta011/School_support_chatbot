import asyncio
import random
from datetime import date, timedelta

from faker import Faker
from passlib.hash import argon2
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.erp import (
    Attendance,
    Course,
    Enrollment,
    Faculty,
    Fee,
    Mark,
    Student,
    Timetable,
    User,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Idempotency: clear all ERP data
        await session.execute(delete(Attendance))
        await session.execute(delete(Fee))
        await session.execute(delete(Mark))
        await session.execute(delete(Timetable))
        await session.execute(delete(Enrollment))
        await session.execute(delete(Course))
        await session.execute(delete(Faculty))
        await session.execute(delete(Student))
        await session.execute(delete(User))
        await session.commit()
        
        # 1. Create Admins
        admin1 = User(enrollment_no="admin1", password_hash=argon2.hash("adminpass"), role="admin")
        admin2 = User(enrollment_no="admin2", password_hash=argon2.hash("adminpass"), role="admin")
        session.add_all([admin1, admin2])
        await session.flush()
        
        # 2. Create Departments & Courses
        departments = ["Computer Science", "Electrical Engineering", "Mechanical Engineering"]
        courses = []
        for dept in departments:
            for i in range(1, 13): # 12 courses per dept (2 semesters * 6 courses)
                sem = 1 if i <= 6 else 2
                code = f"{dept[:2].upper()}{100+i}"
                course = Course(
                    code=code,
                    name=f"Course {code}",
                    department=dept,
                    credits=random.choice([3, 4])
                )
                session.add(course)
                courses.append((course, sem, dept))
        await session.flush()
        
        # 3. Create Faculty
        for _ in range(15):
            dept = random.choice(departments)
            user = User(
                enrollment_no=f"FAC{fake.unique.random_number(digits=4)}",
                password_hash=argon2.hash("facpass"),
                role="faculty"
            )
            session.add(user)
            await session.flush()
            
            faculty = Faculty(
                user_id=user.id,
                name=fake.name(),
                department=dept,
                email=fake.email(),
                cabin=f"Room {random.randint(100, 999)}",
                office_hours="Mon-Wed 2PM-4PM"
            )
            session.add(faculty)
            
        # 4. Create Students and Demo Logins
        students = []
        for i in range(40):
            dept = random.choice(departments)
            sem = random.choice([1, 2])
            
            # 3 documented demo logins
            enrollment_no = f"STU{i+1:03d}"
            if i < 3:
                enrollment_no = f"demo_student_{i+1}"
                
            user = User(
                enrollment_no=enrollment_no,
                password_hash=argon2.hash("demopass" if i < 3 else "stupass"),
                role="student"
            )
            session.add(user)
            await session.flush()
            
            student = Student(
                user_id=user.id,
                name=fake.name(),
                department=dept,
                semester=sem
            )
            session.add(student)
            await session.flush()
            students.append(student)
            
            # Enrollments (6 per semester)
            dept_courses = [c for c, c_sem, c_dept in courses if c_dept == dept and c_sem == sem]
            for c in dept_courses:
                session.add(Enrollment(student_id=student.id, course_id=c.id, semester=sem))
                
                # Timetable (2 sessions per course)
                session.add(Timetable(
                    course_id=c.id,
                    day_of_week=random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
                    start_time="09:00",
                    end_time="10:00",
                    room=f"Room {random.randint(100, 500)}"
                ))
                
                # Marks
                session.add(Mark(student_id=student.id, course_id=c.id, exam_type="midterm", score=random.randint(40, 100), max_score=100))
                session.add(Mark(student_id=student.id, course_id=c.id, exam_type="final", score=random.randint(40, 100), max_score=100))
                
                # Attendance (60 days)
                start_date = date.today() - timedelta(days=60)
                # some students have poor attendance
                att_prob = random.uniform(0.6, 0.95) 
                if i % 10 == 0:
                    att_prob = random.uniform(0.4, 0.7) # below 75%
                    
                for d in range(60):
                    day = start_date + timedelta(days=d)
                    if day.weekday() < 5: # Mon-Fri
                        status = "present" if random.random() < att_prob else "absent"
                        session.add(Attendance(student_id=student.id, course_id=c.id, date=day, status=status))

            # Fees
            terms = ["Fall 2026", "Spring 2027"]
            for term in terms:
                due_date = date.today() + timedelta(days=random.randint(-30, 30))
                amount_due = 5000.0
                state = random.choice(["paid", "partially_paid", "overdue"])
                if state == "paid":
                    amount_paid = 5000.0
                elif state == "partially_paid":
                    amount_paid = 2500.0
                else:
                    amount_paid = 0.0
                    due_date = date.today() - timedelta(days=10) # ensure it is overdue
                    
                session.add(Fee(
                    student_id=student.id,
                    term=term,
                    amount_due=amount_due,
                    amount_paid=amount_paid,
                    due_date=due_date
                ))

        await session.commit()
    print("Seed complete. Demo logins: demo_student_1, demo_student_2, demo_student_3 (password: demopass)")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
