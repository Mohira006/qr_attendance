from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import today_local, to_local
from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import AttendanceStatus, EmploymentStatus, LeaveStatus
from app.models.leave import Leave
from app.schemas.dashboard import DashboardStatisticsResponse, DepartmentBreakdown, TrendDay
from app.schemas.department import DepartmentBrief
from app.services import attendance_query_service, settings_service
from app.services.working_hours import is_working_day


async def get_statistics(db: AsyncSession, target_date: date | None = None) -> DashboardStatisticsResponse:
    target_date = target_date or today_local()
    overview = await attendance_query_service.get_day_overview(db, target_date)

    all_today = overview.on_time + overview.late
    expected = overview.total_employees - len(overview.on_leave)
    attendance_percentage = round(overview.present_count / expected * 100, 1) if expected > 0 else 0.0

    average_arrival_time = None
    if all_today:
        seconds_of_day = [
            (to_local(a.check_in).hour * 3600 + to_local(a.check_in).minute * 60 + to_local(a.check_in).second)
            for a in all_today
        ]
        average_seconds = sum(seconds_of_day) // len(seconds_of_day)
        average_arrival_time = f"{average_seconds // 3600:02d}:{(average_seconds % 3600) // 60:02d}"

    return DashboardStatisticsResponse(
        date=target_date,
        total_employees=overview.total_employees,
        present_today=overview.present_count,
        on_time_count=len(overview.on_time),
        late_count=len(overview.late),
        absent_count=len(overview.absent),
        on_leave_count=len(overview.on_leave),
        currently_working_count=overview.currently_working_count,
        attendance_percentage=attendance_percentage,
        average_arrival_time=average_arrival_time,
    )


async def get_trend(db: AsyncSession, days: int) -> list[TrendDay]:
    """A single pair of grouped queries covers the whole window, rather than
    re-running the full day-overview computation once per day."""
    days = max(1, min(days, 90))
    end = today_local()
    start = end - timedelta(days=days - 1)
    settings = await settings_service.get_or_create(db)

    total_active = (
        await db.execute(select(func.count(Employee.id)).where(Employee.status == EmploymentStatus.ACTIVE))
    ).scalar_one()

    rows = (
        await db.execute(
            select(Attendance.date, Attendance.status, func.count(Attendance.id))
            .join(Attendance.employee)
            .where(Attendance.date >= start, Attendance.date <= end, Employee.status == EmploymentStatus.ACTIVE)
            .group_by(Attendance.date, Attendance.status)
        )
    ).all()

    counts: dict[date, dict[str, int]] = defaultdict(lambda: {"on_time": 0, "late": 0})
    for day, status, count in rows:
        counts[day][status.value] = count

    result: list[TrendDay] = []
    day = start
    while day <= end:
        on_time = counts[day]["on_time"]
        late = counts[day]["late"]
        present = on_time + late
        # Approximation: unlike the per-employee summary, this does not exclude
        # employees on leave from the denominator - acceptable for a trend chart.
        percentage = round(present / total_active * 100, 1) if total_active else 0.0
        result.append(
            TrendDay(
                date=day,
                on_time_count=on_time,
                late_count=late,
                present_count=present,
                attendance_percentage=percentage,
                is_working_day=is_working_day(day, settings),
            )
        )
        day += timedelta(days=1)
    return result


async def get_department_breakdown(db: AsyncSession, target_date: date | None = None) -> list[DepartmentBreakdown]:
    target_date = target_date or today_local()
    settings = await settings_service.get_or_create(db)

    departments = (await db.execute(select(Department))).scalars().all()

    total_by_dept = dict(
        (
            await db.execute(
                select(Employee.department_id, func.count(Employee.id))
                .where(Employee.status == EmploymentStatus.ACTIVE)
                .group_by(Employee.department_id)
            )
        ).all()
    )
    attendance_rows = (
        await db.execute(
            select(Employee.department_id, Attendance.status, func.count(Attendance.id))
            .select_from(Attendance)
            .join(Attendance.employee)
            .where(Attendance.date == target_date, Employee.status == EmploymentStatus.ACTIVE)
            .group_by(Employee.department_id, Attendance.status)
        )
    ).all()
    on_time_by_dept: dict[int, int] = defaultdict(int)
    late_by_dept: dict[int, int] = defaultdict(int)
    for dept_id, status, count in attendance_rows:
        if status == AttendanceStatus.ON_TIME:
            on_time_by_dept[dept_id] = count
        else:
            late_by_dept[dept_id] = count

    # Employees on approved leave are neither present nor absent - excluded from
    # the count the same way get_day_overview excludes them, so the two endpoints
    # (and their totals, summed across departments) agree with each other.
    on_leave_by_dept: dict[int, int] = defaultdict(int)
    leave_rows = (
        await db.execute(
            select(Employee.department_id, func.count(Leave.id))
            .select_from(Leave)
            .join(Leave.employee)
            .where(
                Leave.status == LeaveStatus.APPROVED,
                Leave.start_date <= target_date,
                Leave.end_date >= target_date,
                Employee.status == EmploymentStatus.ACTIVE,
            )
            .group_by(Employee.department_id)
        )
    ).all()
    for dept_id, count in leave_rows:
        on_leave_by_dept[dept_id] = count

    is_working = is_working_day(target_date, settings)

    breakdown = []
    for department in departments:
        total = total_by_dept.get(department.id, 0)
        on_time = on_time_by_dept.get(department.id, 0)
        late = late_by_dept.get(department.id, 0)
        on_leave = on_leave_by_dept.get(department.id, 0)
        absent = max(0, total - on_time - late - on_leave) if is_working else 0
        breakdown.append(
            DepartmentBreakdown(
                department=DepartmentBrief.model_validate(department),
                total_employees=total,
                on_time_count=on_time,
                late_count=late,
                absent_count=absent,
            )
        )
    return breakdown
