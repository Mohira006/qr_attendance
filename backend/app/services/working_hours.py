from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.core.time import combine_local, local_date, truncate_to_minute
from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import AttendanceStatus
from app.models.settings import CompanySettings


@dataclass(frozen=True)
class WorkingHours:
    start: time
    end: time
    grace_minutes: int

    @property
    def is_overnight(self) -> bool:
        return self.end <= self.start


@dataclass(frozen=True)
class ArrivalEvaluation:
    status: AttendanceStatus
    late_minutes: int
    expected_start: datetime  # UTC
    allowed_until: datetime  # UTC, expected_start + grace


def resolve_working_hours(
    employee: Employee,
    department: Department | None,
    settings: CompanySettings,
) -> WorkingHours:
    """Precedence: employee override -> department override -> company settings."""
    start = employee.work_start_time
    if start is None and department is not None:
        start = department.work_start_time
    if start is None:
        start = settings.work_start_time

    end = employee.work_end_time
    if end is None and department is not None:
        end = department.work_end_time
    if end is None:
        end = settings.work_end_time

    return WorkingHours(
        start=start,
        end=end,
        grace_minutes=settings.grace_period_minutes,
    )


def evaluate_arrival(check_in: datetime, hours: WorkingHours, work_date: date | None = None) -> ArrivalEvaluation:
    """Classify an arrival.

    Rules (from the specification, resolved as agreed):
    - Arrival is evaluated at minute precision; seconds are ignored.
      09:15:45 counts as 09:15 -> on time; 09:16:00 -> late.
    - ON_TIME when arrival <= work start + grace period.
    - LATE otherwise; late_minutes is measured from work start (09:38 -> 38 min),
      matching the worked examples rather than the grace-adjusted wording.
    """
    if work_date is None:
        work_date = local_date(check_in)
    expected_start = combine_local(work_date, hours.start)
    allowed_until = expected_start + timedelta(minutes=hours.grace_minutes)
    arrival = truncate_to_minute(check_in)

    if arrival <= allowed_until:
        return ArrivalEvaluation(AttendanceStatus.ON_TIME, 0, expected_start, allowed_until)

    late_minutes = int((arrival - expected_start).total_seconds() // 60)
    return ArrivalEvaluation(AttendanceStatus.LATE, late_minutes, expected_start, allowed_until)


def expected_end(work_date: date, hours: WorkingHours) -> datetime:
    """UTC datetime the shift is expected to end; next calendar day for overnight shifts."""
    end_date = work_date + timedelta(days=1) if hours.is_overnight else work_date
    return combine_local(end_date, hours.end)


def working_minutes(check_in: datetime, check_out: datetime) -> int:
    return max(0, int((check_out - check_in).total_seconds() // 60))


def is_working_day(day: date, settings: CompanySettings) -> bool:
    return day.isoweekday() in settings.working_day_numbers


def attendance_working_hours(record: Attendance, settings: CompanySettings) -> WorkingHours:
    """Working hours snapshot stored on an attendance record (used for history and letters)."""
    return WorkingHours(
        start=record.expected_check_in,
        end=record.expected_check_out,
        grace_minutes=settings.grace_period_minutes,
    )
