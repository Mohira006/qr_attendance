from fastapi import APIRouter

from app.api.deps import DB, HRUser
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.models.enums import EmploymentStatus
from app.schemas.attendance import AttendanceResponse
from app.schemas.employee import EmployeeBrief
from app.schemas.simulator import SimulatorEmployeeOption, SimulatorTriggerRequest, SimulatorTriggerResponse
from app.services import attendance_service, employee_service

router = APIRouter(prefix="/simulator", tags=["simulator"])


def _require_enabled() -> None:
    if not get_settings().SIMULATOR_ENABLED:
        raise ForbiddenError("The Face ID simulator is disabled on this deployment", code="simulator_disabled")


@router.get("/employees", response_model=list[SimulatorEmployeeOption])
async def list_simulator_employees(db: DB, _: HRUser) -> list[SimulatorEmployeeOption]:
    """Active employees for the simulator's picker UI."""
    _require_enabled()
    items, _total = await employee_service.list_employees(
        db, search=None, department_id=None, status=EmploymentStatus.ACTIVE, page=1, page_size=500
    )
    return [SimulatorEmployeeOption.model_validate(item) for item in items]


@router.post("/trigger", response_model=SimulatorTriggerResponse)
async def trigger_event(payload: SimulatorTriggerRequest, db: DB, _: HRUser) -> SimulatorTriggerResponse:
    """Simulates a Face ID device pushing an event, through the identical code path
    a real device's request takes (app/services/attendance_service.process_face_event).

    Unlike the device endpoints, this never raises for UNKNOWN_EMPLOYEE / REJECTED -
    it always returns 200 with the outcome, since a testing tool should report what
    happened rather than surface it as an HTTP error.
    """
    _require_enabled()
    result = await attendance_service.process_face_event(
        db,
        identifier=payload.identifier,
        timestamp=payload.timestamp,
        requested_type=payload.requested_type,
        device_id="simulator",
        confidence=1.0,
    )
    return SimulatorTriggerResponse(
        outcome=result.outcome,
        message=result.message,
        face_event_id=result.face_event.id,
        employee=EmployeeBrief.model_validate(result.employee) if result.employee else None,
        attendance=AttendanceResponse.model_validate(result.attendance) if result.attendance else None,
    )
