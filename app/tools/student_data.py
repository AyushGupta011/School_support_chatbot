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

tools = [get_attendance, get_fee_status, get_timetable, get_marks]
