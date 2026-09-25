import calendar
from datetime import date, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from app.core.exceptions import NotFoundError
from app.core.time import today_local
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.enums import AttendanceStatus, CheckoutStatus, EmploymentStatus, LeaveStatus, UserRole
from app.models.leave import Leave
from app.models.user import User
from app.schemas.attendance import AttendanceResponse, DayOverviewResponse, EmployeeAttendanceSummaryResponse
from app.schemas.employee import EmployeeBrief
from app.services import employee_service, settings_service
from app.services.working_hours import is_working_day


async def get_attendance(db: AsyncSession, attendance_id: int) -> Attendance:
    """Single-record fetch with the eager-loads the explanation-letter request flow
    needs: .explanation_letter (duplicate check) and .employee.user (notification)."""
    record = (
        await db.execute(
            select(Attendance)
            .options(
                selectinload(Attendance.explanation_letter),
                selectinload(Attendance.employee).selectinload(Employee.user),
            )
            .where(Attendance.id == attendance_id)
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError("Attendance record not found", code="attendance_not_found")
    return record


async def get_day_overview(db: AsyncSession, target_date: date, department_id: int | None = None) -> DayOverviewResponse:
    settings = await settings_service.get_or_create(db)
    employee_filters = [Employee.status == EmploymentStatus.ACTIVE]
    if department_id is not None:
        employee_filters.append(Employee.department_id == department_id)

    total_employees = (await db.execute(select(func.count(Employee.id)).where(*employee_filters))).scalar_one()

    attendance_rows = (
        await db.execute(
            select(Attendance)
            .join(Attendance.employee)
            .options(selectinload(Attendance.explanation_letter))
            .where(Attendance.date == target_date, *employee_filters)
            .order_by(Attendance.check_in.asc())
        )
    ).unique().scalars().all()
    on_time = [a for a in attendance_rows if a.status == AttendanceStatus.ON_TIME]
    late = [a for a in attendance_rows if a.status == AttendanceStatus.LATE]
    present_ids = {a.employee_id for a in attendance_rows}

    leave_rows = (
        await db.execute(
            select(Leave)
            .join(Leave.employee)
            .where(
                Leave.status == LeaveStatus.APPROVED,
                Leave.start_date <= target_date,
                Leave.end_date >= target_date,
                *employee_filters,
            )
        )
    ).unique().scalars().all()
    on_leave = [leave.employee for leave in leave_rows if leave.employee_id not in present_ids]
    excluded_ids = present_ids | {leave.employee_id for leave in leave_rows}

    absent: list[Employee] = []
    if is_working_day(target_date, settings):
        absent_filters = list(employee_filters)
        if excluded_ids:
            absent_filters.append(Employee.id.not_in(excluded_ids))
        absent = (
            await db.execute(
                select(Employee)
                .join(Employee.department)
                .options(contains_eager(Employee.department))
                .where(*absent_filters)
                .order_by(Employee.last_name, Employee.first_name)
            )
        ).unique().scalars().all()

    currently_working = sum(1 for a in attendance_rows if a.checkout_status == CheckoutStatus.PENDING)

    return DayOverviewResponse(
        date=target_date,
        total_employees=total_employees,
        present_count=len(attendance_rows),
        currently_working_count=currently_working,
        on_time=[AttendanceResponse.model_validate(a) for a in on_time],
        late=[AttendanceResponse.model_validate(a) for a in late],
        absent=[EmployeeBrief.model_validate(e) for e in absent],
        on_leave=[EmployeeBrief.model_validate(e) for e in on_leave],
    )


def _history_query(
    *,
    viewer: User,
    employee_id: int | None,
    department_id: int | None,
    status: AttendanceStatus | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[Select, list]:
    filters = []
    if viewer.role != UserRole.HR:
        filters.append(Attendance.employee_id == viewer.employee_id)
    elif employee_id is not None:
        filters.append(Attendance.employee_id == employee_id)
    if department_id is not None:
        filters.append(Employee.department_id == department_id)
    if status is not None:
        filters.append(Attendance.status == status)
    if date_from is not None:
        filters.append(Attendance.date >= date_from)
    if date_to is not None:
        filters.append(Attendance.date <= date_to)

    base = (
        select(Attendance)
        .join(Attendance.employee)
        .options(contains_eager(Attendance.employee), selectinload(Attendance.explanation_letter))
    )
    return base, filters


async def get_history(
    db: AsyncSession,
    *,
    viewer: User,
    employee_id: int | None,
    department_id: int | None,
    status: AttendanceStatus | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
) -> tuple[list[Attendance], int]:
    base, filters = _history_query(
        viewer=viewer, employee_id=employee_id, department_id=department_id, status=status, date_from=date_from, date_to=date_to
    )
    total = (
        await db.execute(select(func.count(Attendance.id)).select_from(Attendance).join(Attendance.employee).where(*filters))
    ).scalar_one()
    rows = (
        await db.execute(
            base.where(*filters)
            .order_by(Attendance.date.desc(), Attendance.check_in.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).unique().scalars().all()
    return list(rows), total


def _month_bounds(month: str | None) -> tuple[date, date]:
    """Parses 'YYYY-MM' into (first day, last day) of that month. Defaults to the current month."""
    if month:
        year, month_num = (int(part) for part in month.split("-"))
    else:
        today = today_local()
        year, month_num = today.year, today.month
    last_day = calendar.monthrange(year, month_num)[1]
    return date(year, month_num, 1), date(year, month_num, last_day)


async def get_employee_summary(db: AsyncSession, employee_id: int, month: str | None) -> EmployeeAttendanceSummaryResponse:
    employee = await employee_service.get_employee(db, employee_id)
    settings = await settings_service.get_or_create(db)
    period_start, period_end = _month_bounds(month)

    rows = (
        await db.execute(
            select(Attendance).where(
                Attendance.employee_id == employee_id, Attendance.date >= period_start, Attendance.date <= period_end
            )
        )
    ).scalars().all()
    on_time_count = sum(1 for r in rows if r.status == AttendanceStatus.ON_TIME)
    late_count = sum(1 for r in rows if r.status == AttendanceStatus.LATE)
    total_working_minutes = sum(r.total_working_minutes or 0 for r in rows)
    recorded_dates = {r.date for r in rows}

    leave_rows = (
        await db.execute(
            select(Leave).where(
                Leave.employee_id == employee_id,
                Leave.status == LeaveStatus.APPROVED,
                Leave.start_date <= period_end,
                Leave.end_date >= period_start,
            )
        )
    ).scalars().all()
    leave_dates: set[date] = set()
    for leave in leave_rows:
        day = max(leave.start_date, period_start)
        end = min(leave.end_date, period_end)
        while day <= end:
            leave_dates.add(day)
            day += timedelta(days=1)

    # Only days up to today count toward "expected" - future days in the requested
    # month haven't happened yet and shouldn't be counted as absences or lower the percentage.
    evaluable_end = min(period_end, today_local())
    working_days = 0
    on_leave_count = 0
    absent_count = 0
    if evaluable_end >= period_start:
        day = period_start
        while day <= evaluable_end:
            if is_working_day(day, settings):
                working_days += 1
                if day in leave_dates:
                    on_leave_count += 1
                elif day not in recorded_dates:
                    absent_count += 1
            day += timedelta(days=1)

    attendance_percentage = round((len(recorded_dates) / working_days) * 100, 1) if working_days else 0.0

    return EmployeeAttendanceSummaryResponse(
        employee=EmployeeBrief.model_validate(employee),
        period_start=period_start,
        period_end=period_end,
        on_time_count=on_time_count,
        late_count=late_count,
        absent_count=absent_count,
        on_leave_count=on_leave_count,
        total_working_minutes=total_working_minutes,
        attendance_percentage=attendance_percentage,
    )
