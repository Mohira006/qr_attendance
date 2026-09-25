from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import LeaveCycleStatus, LeaveRequestStatus, LeaveRequestType
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeBrief


class LeaveRequestCreate(BaseModel):
    requested_start_date: date
    request_type: LeaveRequestType
    employee_comment: str | None = Field(default=None, max_length=2000)

    @field_validator("employee_comment", mode="before")
    @classmethod
    def _strip(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class HrLeaveRequestCreate(LeaveRequestCreate):
    """HR creating/submitting a request on an employee's behalf. `override_reason`
    is required and, when present, bypasses the eligibility/notice-period checks
    (never the cannot-start-in-the-past check, which is a data-integrity rule,
    not a notice-period rule)."""

    employee_id: int
    override_reason: str = Field(min_length=1, max_length=2000)


class LeaveRequestReview(BaseModel):
    """HR approving or rejecting; comment is optional either way."""

    hr_comment: str | None = Field(default=None, max_length=2000)

    @field_validator("hr_comment", mode="before")
    @classmethod
    def _strip(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class LeaveCommentUpdate(BaseModel):
    hr_comment: str = Field(min_length=1, max_length=2000)

    @field_validator("hr_comment")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("comment cannot be empty")
        return value


class LeaveDurationUpdate(BaseModel):
    """HR override of duration on a still-pending request. Capped higher than the
    company default (see SettingsUpdate.annual_leave_duration_days, max 90) since
    this is a deliberate case-by-case exception, not the standard policy value."""

    duration_days: int = Field(ge=1, le=365)


class LeaveRequestResponse(BaseModel):
    """Denormalized for direct table display (spec section 15): pulls the work-period
    and eligibility fields from the request's cycle so the frontend doesn't need a
    second lookup. Built explicitly in leave_service, not via plain model_validate,
    since these fields live on a related object, not on LeaveRequest itself."""

    id: int
    employee: EmployeeBrief
    cycle_number: int
    work_period_start: date
    work_period_end: date
    eligibility_date: date
    requested_start_date: date
    requested_end_date: date
    duration_days: int
    request_type: LeaveRequestType
    status: LeaveRequestStatus
    employee_comment: str | None
    hr_comment: str | None
    submitted_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None
    cancelled_at: datetime | None
    reviewed_by_user_id: int | None
    is_hr_override: bool
    override_reason: str | None
    created_at: datetime
    updated_at: datetime


class LeaveEligibilityResponse(BaseModel):
    employee: EmployeeBrief
    employment_start_date: date
    annual_leave_duration_days: int
    cycle_number: int
    work_period_start: date
    work_period_end: date
    eligibility_date: date
    is_eligible: bool
    cycle_status: LeaveCycleStatus
    current_request: LeaveRequestResponse | None
    previous_leave: LeaveRequestResponse | None
    next_eligibility_date: date | None


class LeaveSettingsFields(BaseModel):
    """Mixin-style fields merged into the existing settings response/update schemas
    in app/schemas/settings.py, rather than a parallel leave-settings endpoint."""

    annual_leave_duration_days: int
    leave_normal_notice_days: int
    leave_force_majeure_notice_days: int
    leave_eligibility_after_months: int
    leave_next_cycle_after_months: int
    leave_reminder_30_days_enabled: bool
    leave_reminder_14_days_enabled: bool
    leave_reminder_7_days_enabled: bool
