import json

from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from app.erp.mock import MockERPAdapter
from app.erp.repository import ERPRepository


def get_adapter(config: RunnableConfig) -> MockERPAdapter:
    session = config["configurable"]["session"]
    return MockERPAdapter(ERPRepository(session))

def get_student_id(config: RunnableConfig) -> int:
    return config["configurable"]["student_id"]

@tool
async def get_attendance(config: RunnableConfig) -> str:
    """Get the attendance records for the current student."""
    try:
        adapter = get_adapter(config)
        sid = get_student_id(config)
        res = await adapter.get_attendance(sid)
        return json.dumps([r.model_dump() for r in res], default=str)
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"

@tool
async def get_fee_status(config: RunnableConfig) -> str:
    """Get the fee status and dues for the current student."""
    try:
        adapter = get_adapter(config)
        sid = get_student_id(config)
        res = await adapter.get_fee_status(sid)
        return json.dumps([r.model_dump() for r in res], default=str)
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"

@tool
async def get_timetable(config: RunnableConfig) -> str:
    """Get the weekly timetable for the current student's enrolled courses."""
    try:
        adapter = get_adapter(config)
        sid = get_student_id(config)
        res = await adapter.get_timetable(sid)
        return json.dumps([r.model_dump() for r in res], default=str)
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"

@tool
async def get_marks(config: RunnableConfig) -> str:
    """Get the exam marks for the current student."""
    try:
        adapter = get_adapter(config)
        sid = get_student_id(config)
        res = await adapter.get_marks(sid)
        return json.dumps([r.model_dump() for r in res], default=str)
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"

@tool
async def generate_fee_payment_link(term: str, config: RunnableConfig) -> str:
    """Generate a secure online payment portal link for any pending tuition or term fee dues."""
    try:
        session = config["configurable"]["session"]
        sid = get_student_id(config)
        adapter = get_adapter(config)
        fees = await adapter.get_fee_status(sid)
        matching = [f for f in fees if term.lower() in f.term.lower()]
        target = matching[0] if matching else (fees[0] if fees else None)
        
        if not target:
            return json.dumps({"status": "no_dues", "message": f"No fee record found for {term}."})
            
        due = target.amount_due - target.amount_paid
        if due <= 0:
            return json.dumps({"status": "already_paid", "message": f"Fees for {target.term} are already fully settled!"})
            
        invoice_id = f"INV-2026-{sid:03d}-{abs(hash(target.term)) % 10000}"
        pay_url = f"https://portal.apex-university.edu/pay?invoice={invoice_id}&amount={due:.2f}&term={target.term}"
        
        return json.dumps({
            "status": "success",
            "term": target.term,
            "amount_due": due,
            "invoice_id": invoice_id,
            "payment_url": pay_url,
            "message": f"Payment invoice {invoice_id} generated for {target.term} (${due:.2f})."
        })
    except Exception as e:  # noqa: BLE001
        return f"Error generating payment link: {e}"

@tool
async def submit_leave_application(start_date: str, end_date: str, reason: str, config: RunnableConfig) -> str:
    """Submit an official student leave of absence application to the academic office."""
    try:
        from app.models.erp import LeaveApplication
        session = config["configurable"]["session"]
        sid = get_student_id(config)
        
        leave = LeaveApplication(
            student_id=sid,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status="submitted"
        )
        session.add(leave)
        await session.commit()
        await session.refresh(leave)
        
        return json.dumps({
            "status": "success",
            "application_id": f"LV-{leave.id:04d}",
            "start_date": start_date,
            "end_date": end_date,
            "message": f"Leave application LV-{leave.id:04d} from {start_date} to {end_date} has been submitted for approval."
        })
    except Exception as e:  # noqa: BLE001
        return f"Error submitting leave application: {e}"

@tool
async def book_faculty_appointment(faculty_name: str, appointment_date: str, appointment_time: str, reason: str, config: RunnableConfig) -> str:
    """Book an academic counseling or office hours appointment with a faculty professor."""
    try:
        from app.models.erp import FacultyAppointment
        session = config["configurable"]["session"]
        sid = get_student_id(config)
        
        appointment = FacultyAppointment(
            student_id=sid,
            faculty_name=faculty_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status="confirmed"
        )
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        
        return json.dumps({
            "status": "success",
            "appointment_id": f"APT-{appointment.id:04d}",
            "faculty": faculty_name,
            "date": appointment_date,
            "time": appointment_time,
            "message": f"Appointment APT-{appointment.id:04d} with {faculty_name} confirmed for {appointment_date} at {appointment_time}."
        })
    except Exception as e:  # noqa: BLE001
        return f"Error booking faculty appointment: {e}"

tools = [
    get_attendance,
    get_fee_status,
    get_timetable,
    get_marks,
    generate_fee_payment_link,
    submit_leave_application,
    book_faculty_appointment
]
