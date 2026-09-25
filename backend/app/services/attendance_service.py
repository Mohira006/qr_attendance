from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import format_local_time, local_date, now_utc
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.enums import AttendanceStatus, CheckoutStatus, LeaveStatus, NotificationType, ScanOutcome
from app.models.leave import Leave
from app.schemas.attendance import AttendanceResponse
from app.services import employee_service, notification_service, settings_service
from app.services.working_hours import evaluate_arrival, resolve_working_hours, working_minutes
from app.websocket.manager import manager


@dataclass
class ScanResult:
    outcome: ScanOutcome
    message: str
    employee: Employee
    attendance: Attendance | None


async def _active_attendance(db: AsyncSession, employee_id: int, today: date) -> Attendance | None:
    """The row that any further scan today should act on: today's own record
    (any status - a second scan today updates its check_out), OR yesterday's
    record but ONLY if it is still genuinely open (PENDING) - an overnight shift
    in progress. A *completed* record from a different day must never be reused:
    without this restriction a scan today could silently overwrite the check_out
    of an unrelated earlier day. Rows the end-of-day job already finalized as
    MISSING are excluded either way - those are closed; a new scan starts fresh.
    """
    yesterday = today - timedelta(days=1)
    return (
        await db.execute(
            select(Attendance)
            .options(selectinload(Attendance.explanation_letter))
            .where(
                Attendance.employee_id == employee_id,
                Attendance.checkout_status != CheckoutStatus.MISSING,
                or_(
                    Attendance.date == today,
                    and_(Attendance.date == yesterday, Attendance.checkout_status == CheckoutStatus.PENDING),
                ),
            )
            .order_by(Attendance.check_in.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _active_leave(db: AsyncSession, employee_id: int, day: date) -> Leave | None:
    return (
        await db.execute(
            select(Leave).where(
                Leave.employee_id == employee_id,
                Leave.status == LeaveStatus.APPROVED,
                Leave.start_date <= day,
                Leave.end_date >= day,
            )
        )
    ).scalar_one_or_none()


async def _broadcast_attendance(result: ScanResult) -> None:
    if result.attendance is None:
        return
    payload = AttendanceResponse.model_validate(result.attendance).model_dump(mode="json")
    event_type = "attendance.checked_in" if result.outcome == ScanOutcome.CHECK_IN else "attendance.checked_out"
    message = {"type": event_type, "data": payload}
    await manager.broadcast_to_hr(message)
    if result.employee.user is not None:
        await manager.send_to_user(result.employee.user.id, message)


async def process_scan(db: AsyncSession, *, employee: Employee) -> ScanResult:
    """Records a check-in or check-out for an employee scanning the entrance QR
    code with their own phone. No identifier resolution is needed - the caller's
    identity comes directly from their own authenticated session (see the
    /attendance/scan route), not a separate recognition system. The backend
    always decides check-in vs check-out itself, based on whether the employee
    already has an open record - there is no explicit "direction" to request,
    since scanning is the same single action either way.
    """
    event_timestamp = now_utc()  # always "now" - this is a live action, not a historical report
    settings = await settings_service.get_or_create(db)

    if not employee.is_active:
        # Defensive: a deactivated employee's own login should already be disabled
        # (see employee_service._deactivate_account), making this endpoint
        # unreachable for them in practice - this guards a data-integrity edge
        # case, not a normal path.
        return ScanResult(ScanOutcome.REJECTED, "This account is deactivated.", employee, None)

    # Duplicate window: near-simultaneous repeat scans (an employee tapping twice,
    # a slow page reload re-submitting) are ignored rather than treated as a new
    # check-out. Tracked as a single "last scan" timestamp on the employee, not a
    # separate event-log table - nothing here ever needs more than the most recent one.
    window = timedelta(seconds=settings.duplicate_event_window_seconds)
    if employee.last_scan_at is not None and abs(event_timestamp - employee.last_scan_at) < window:
        employee.last_scan_at = event_timestamp
        await db.commit()
        return ScanResult(
            ScanOutcome.DUPLICATE,
            f"Scan ignored - within the {settings.duplicate_event_window_seconds}s duplicate window.",
            employee,
            None,
        )
    employee.last_scan_at = event_timestamp

    today = local_date(event_timestamp)
    record = await _active_attendance(db, employee.id, today)

    if record is not None:
        return await _close_or_update_checkout(db, employee, record, event_timestamp)

    return await _create_check_in(db, employee, settings, event_timestamp)


async def _close_or_update_checkout(
    db: AsyncSession, employee: Employee, record: Attendance, event_timestamp: datetime
) -> ScanResult:
    # This schema stores one check-in and one check-out per day (matching the given
    # database design), not multiple sessions. Any scan after the first therefore
    # updates check_out to the latest time - see the Stage 2 summary for the reasoning.
    if event_timestamp <= record.check_in:
        await db.commit()
        return ScanResult(ScanOutcome.REJECTED, "Scan timestamp is not after check-in.", employee, record)

    record.check_out = event_timestamp
    record.checkout_status = CheckoutStatus.COMPLETED
    record.total_working_minutes = working_minutes(record.check_in, event_timestamp)

    message = f"{employee.full_name} checked out at {format_local_time(event_timestamp)}."
    notifications = await notification_service.notify_hr(
        db, type=NotificationType.CHECK_OUT, title="Check-out recorded", message=message, employee=employee, attendance_id=record.id
    )

    await db.commit()
    await db.refresh(record)
    await db.refresh(record, attribute_names=["explanation_letter"])

    result = ScanResult(ScanOutcome.CHECK_OUT, message, employee, record)
    await _broadcast_attendance(result)
    await notification_service.broadcast_notifications(notifications)
    return result


async def _create_check_in(db: AsyncSession, employee: Employee, settings, event_timestamp: datetime) -> ScanResult:
    work_date = local_date(event_timestamp)
    hours = resolve_working_hours(employee, employee.department, settings)
    evaluation = evaluate_arrival(event_timestamp, hours, work_date)
    leave = await _active_leave(db, employee.id, work_date)
    employee_id = employee.id  # captured now: rollback() below expires employee's attributes,
    # and touching an expired attribute via bare access afterward is not safe in async SQLAlchemy.

    new_record = Attendance(
        employee=employee,
        date=work_date,
        check_in=event_timestamp,
        status=evaluation.status,
        checkout_status=CheckoutStatus.PENDING,
        late_minutes=evaluation.late_minutes,
        expected_check_in=hours.start,
        expected_check_out=hours.end,
    )
    db.add(new_record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # employee's attributes are now expired by the rollback; re-fetch rather than
        # touch them via bare attribute access, which is not safe in async SQLAlchemy.
        employee = await employee_service.get_employee(db, employee_id)
        return ScanResult(ScanOutcome.DUPLICATE, "A concurrent request already recorded today's check-in.", employee, None)

    local_time = format_local_time(event_timestamp)
    if evaluation.status == AttendanceStatus.LATE:
        title = "Late arrival"
        message = f"{employee.full_name} arrived {evaluation.late_minutes} minutes late."
    else:
        title = "Check-in recorded"
        message = f"{employee.full_name} checked in at {local_time} (on time)."
    if leave is not None:
        message += " Note: this employee has an approved leave covering today."

    notifications = list(
        await notification_service.notify_hr(
            db,
            type=(NotificationType.LATE if evaluation.status == AttendanceStatus.LATE else NotificationType.CHECK_IN),
            title=title,
            message=message,
            employee=employee,
            attendance_id=new_record.id,
        )
    )

    await db.commit()
    await db.refresh(new_record)
    # The bare refresh above expires relationship state too (not just columns),
    # which would otherwise crash on the lazy="raise" access below - an explicit
    # targeted refresh is a deliberate reload, not the accidental implicit kind
    # lazy="raise" guards against, so it correctly bypasses that restriction.
    await db.refresh(new_record, attribute_names=["explanation_letter"])

    result = ScanResult(ScanOutcome.CHECK_IN, message, employee, new_record)
    await _broadcast_attendance(result)
    await notification_service.broadcast_notifications(notifications)
    return result
