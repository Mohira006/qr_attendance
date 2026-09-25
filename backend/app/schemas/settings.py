from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


def _validate_working_days(cls, value):  # noqa: ARG001
    if isinstance(value, str):
        value = [int(part) for part in value.split(",") if part.strip()]
    if not value:
        raise ValueError("at least one working day is required")
    if len(set(value)) != len(value):
        raise ValueError("working days must be unique")
    if any(day < 1 or day > 7 for day in value):
        raise ValueError("working days must be ISO weekday numbers (1=Monday ... 7=Sunday)")
    return sorted(value)


class SettingsResponse(ORMModel):
    company_name: str
    timezone: str
    work_start_time: time
    work_end_time: time
    grace_period_minutes: int
    duplicate_event_window_seconds: int
    working_days: list[int]
    # Leave management (section 30 of the leave-module spec) - configured here
    # rather than on a separate settings endpoint, since it's the same underlying row.
    annual_leave_duration_days: int
    leave_normal_notice_days: int
    leave_force_majeure_notice_days: int
    leave_eligibility_after_months: int
    leave_next_cycle_after_months: int
    leave_reminder_30_days_enabled: bool
    leave_reminder_14_days_enabled: bool
    leave_reminder_7_days_enabled: bool
    updated_at: datetime

    _working_days = field_validator("working_days", mode="before")(_validate_working_days)


class SettingsUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    work_start_time: time | None = None
    work_end_time: time | None = None
    grace_period_minutes: int | None = Field(default=None, ge=0, le=240)
    duplicate_event_window_seconds: int | None = Field(default=None, ge=0, le=3600)
    working_days: list[int] | None = None
    annual_leave_duration_days: int | None = Field(default=None, ge=1, le=90)
    leave_normal_notice_days: int | None = Field(default=None, ge=0, le=180)
    leave_force_majeure_notice_days: int | None = Field(default=None, ge=0, le=90)
    leave_eligibility_after_months: int | None = Field(default=None, ge=0, le=36)
    leave_next_cycle_after_months: int | None = Field(default=None, ge=0, le=36)
    leave_reminder_30_days_enabled: bool | None = None
    leave_reminder_14_days_enabled: bool | None = None
    leave_reminder_7_days_enabled: bool | None = None

    @field_validator("company_name", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("working_days", mode="before")
    @classmethod
    def _working_days(cls, value):
        if value is None:
            return None
        return _validate_working_days(cls, value)
