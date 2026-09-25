from datetime import date, datetime, time

from pydantic import BaseModel

from app.models.enums import AttendanceStatus, CheckoutStatus, ScanOutcome
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeBrief


class AttendanceResponse(ORMModel):
    id: int
    employee: EmployeeBrief
    date: date
    check_in: datetime
    check_out: datetime | None
    status: AttendanceStatus
    checkout_status: CheckoutStatus
    late_minutes: int
    total_working_minutes: int | None
    expected_check_in: time
    expected_check_out: time
    explanation_letter_id: int | None
    created_at: datetime
    updated_at: datetime


class ScanResponse(BaseModel):
    outcome: ScanOutcome
    message: str
    attendance: AttendanceResponse | None


class DayOverviewResponse(BaseModel):
    """Everything the three HR views (dashboard cards, table, cards) need for one day.

    `on_time` and `late` are sorted by arrival time ascending, matching the
    specification's sorting requirement (section 6).
    """

    date: date
    total_employees: int
    present_count: int
    currently_working_count: int
    on_time: list[AttendanceResponse]
    late: list[AttendanceResponse]
    absent: list[EmployeeBrief]
    on_leave: list[EmployeeBrief]


class EmployeeAttendanceSummaryResponse(BaseModel):
    employee: EmployeeBrief
    period_start: date
    period_end: date
    on_time_count: int
    late_count: int
    absent_count: int
    on_leave_count: int
    total_working_minutes: int
    attendance_percentage: float
