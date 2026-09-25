from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.time import now_utc, today_local
from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.enums import (
    EmploymentStatus,
    LeaveCycleStatus,
    LeaveRequestStatus,
    LeaveRequestType,
    LeaveStatus,
    LeaveType,
    NotificationType,
    UserRole,
)
from app.models.leave import Leave
from app.models.leave_cycle import LeaveCycle
from app.models.leave_request import LeaveRequest
from app.models.settings import CompanySettings
from app.models.user import User
from app.schemas.employee import EmployeeBrief
from app.schemas.leave import LeaveEligibilityResponse, LeaveRequestResponse
from app.services import audit_service, notification_service


def compute_cycle_window(cycle_start: date, eligibility_after_months: int) -> tuple[date, date]:
    """Returns (cycle_end, eligibility_date) for a cycle starting on cycle_start.
    cycle_end is a nominal, display-only one-year "work period" - it does not gate
    anything. Once eligible, an employee stays eligible until they actually take
    leave; there is no forfeiture rule."""
    eligibility_date = cycle_start + relativedelta(months=eligibility_after_months)
    cycle_end = cycle_start + relativedelta(months=12)
    return cycle_end, eligibility_date


def resolve_leave_duration(employee: Employee, settings: CompanySettings) -> int:
    """Precedence: employee override -> company settings. Mirrors
    resolve_working_hours' employee-then-company pattern in working_hours.py -
    e.g. a long-tenured employee with a personally configured higher entitlement."""
    return employee.annual_leave_duration_days if employee.annual_leave_duration_days is not None else settings.annual_leave_duration_days


async def _latest_cycle(db: AsyncSession, employee_id: int) -> LeaveCycle | None:
    return (
        await db.execute(
            select(LeaveCycle)
            .where(LeaveCycle.employee_id == employee_id)
            .order_by(LeaveCycle.cycle_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def get_or_create_current_cycle(db: AsyncSession, employee: Employee, settings: CompanySettings) -> LeaveCycle:
    """The employee's current (not-yet-consumed) cycle. Creates cycle #1 (eligible
    `leave_eligibility_after_months` after employment_start_date, default 6) the
    first time this is called for a given employee. Every cycle after that is
    created by approve_leave_request, immediately on approval - not when the time
    off is actually taken - since the leave's end date (and therefore the next
    cycle's start) is already known as soon as it's approved.
    """
    latest = await _latest_cycle(db, employee.id)
    if latest is not None:
        if latest.status == LeaveCycleStatus.CONSUMED:
            # approve_leave_request always creates the next cycle in the same
            # transaction it consumes this one, so this should be unreachable.
            raise AssertionError(f"Employee {employee.id}'s latest leave cycle is consumed with no successor")
        return latest

    cycle_end, eligibility_date = compute_cycle_window(
        employee.employment_start_date, settings.leave_eligibility_after_months
    )
    cycle = LeaveCycle(
        employee_id=employee.id,
        cycle_number=1,
        cycle_start_date=employee.employment_start_date,
        cycle_end_date=cycle_end,
        eligibility_date=eligibility_date,
        status=LeaveCycleStatus.AVAILABLE,
    )
    db.add(cycle)
    await db.flush()
    return cycle


async def _create_next_cycle(
    db: AsyncSession, employee_id: int, previous_cycle_number: int, leave_end_date: date, settings: CompanySettings
) -> LeaveCycle:
    cycle_end, eligibility_date = compute_cycle_window(leave_end_date, settings.leave_next_cycle_after_months)
    cycle = LeaveCycle(
        employee_id=employee_id,
        cycle_number=previous_cycle_number + 1,
        cycle_start_date=leave_end_date,
        cycle_end_date=cycle_end,
        eligibility_date=eligibility_date,
        status=LeaveCycleStatus.AVAILABLE,
    )
    db.add(cycle)
    await db.flush()
    return cycle


def _base_query():
    return (
        select(LeaveRequest)
        .join(LeaveRequest.employee)
        .options(
            contains_eager(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.cycle),
        )
    )


async def get_request(db: AsyncSession, request_id: int) -> LeaveRequest:
    request = (await db.execute(_base_query().where(LeaveRequest.id == request_id))).unique().scalar_one_or_none()
    if request is None:
        raise NotFoundError("Leave request not found", code="leave_request_not_found")
    return request


def assert_can_view(request: LeaveRequest, user: User) -> None:
    if user.role != UserRole.HR and user.employee_id != request.employee_id:
        raise ForbiddenError("You can only view your own leave requests", code="forbidden")


def to_response(request: LeaveRequest) -> LeaveRequestResponse:
    return LeaveRequestResponse(
        id=request.id,
        employee=EmployeeBrief.model_validate(request.employee),
        cycle_number=request.cycle.cycle_number,
        work_period_start=request.cycle.cycle_start_date,
        work_period_end=request.cycle.cycle_end_date,
        eligibility_date=request.cycle.eligibility_date,
        requested_start_date=request.requested_start_date,
        requested_end_date=request.requested_end_date,
        duration_days=request.duration_days,
        request_type=request.request_type,
        status=request.status,
        employee_comment=request.employee_comment,
        hr_comment=request.hr_comment,
        submitted_at=request.submitted_at,
        approved_at=request.approved_at,
        rejected_at=request.rejected_at,
        cancelled_at=request.cancelled_at,
        reviewed_by_user_id=request.reviewed_by_user_id,
        is_hr_override=request.is_hr_override,
        override_reason=request.override_reason,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


async def create_leave_request(
    db: AsyncSession,
    *,
    employee: Employee,
    requested_start_date: date,
    request_type: LeaveRequestType,
    employee_comment: str | None,
    settings: CompanySettings,
    actor: User,
    ip: str | None,
    override_reason: str | None = None,
) -> LeaveRequest:
    if not employee.is_active:
        raise BadRequestError("Deactivated employees cannot request leave", code="employee_inactive")

    today = today_local()
    if requested_start_date < today:
        # Always enforced, even with an override - a data-integrity rule, not a
        # notice-period rule HR should be able to waive.
        raise BadRequestError("Leave cannot start in the past", code="invalid_start_date")

    cycle = await get_or_create_current_cycle(db, employee, settings)

    if cycle.status != LeaveCycleStatus.AVAILABLE and not override_reason:
        raise ConflictError(
            "This employee already has a leave request pending or approved for the current cycle",
            code="leave_already_pending",
        )

    if not override_reason:
        if today < cycle.eligibility_date:
            raise BadRequestError(
                f"Not eligible for annual leave until {cycle.eligibility_date.isoformat()}",
                code="not_yet_eligible",
                details={"eligibility_date": cycle.eligibility_date.isoformat()},
            )

        notice_days = (requested_start_date - today).days
        required = (
            settings.leave_normal_notice_days
            if request_type == LeaveRequestType.NORMAL
            else settings.leave_force_majeure_notice_days
        )
        if notice_days < required:
            kind = "Normal" if request_type == LeaveRequestType.NORMAL else "Force majeure"
            raise BadRequestError(
                f"{kind} leave requests must be submitted at least {required} day(s) before the leave start date",
                code="notice_period_too_short",
                details={"required_days": required, "notice_days": notice_days},
            )

    duration = resolve_leave_duration(employee, settings)
    requested_end_date = requested_start_date + timedelta(days=duration - 1)

    request = LeaveRequest(
        employee=employee,
        leave_cycle_id=cycle.id,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        duration_days=duration,
        request_type=request_type,
        status=LeaveRequestStatus.PENDING,
        employee_comment=employee_comment,
        submitted_at=now_utc(),
        is_hr_override=bool(override_reason),
        override_reason=override_reason,
    )
    db.add(request)
    cycle.status = LeaveCycleStatus.REQUESTED
    await db.flush()

    audit_service.record(
        db,
        user_id=actor.id,
        action="LEAVE_REQUEST_SUBMITTED",
        entity_type="leave_request",
        entity_id=str(request.id),
        details={
            "employee_id": employee.employee_id,
            "start": requested_start_date.isoformat(),
            "end": requested_end_date.isoformat(),
            "days": duration,
            "type": request_type.value,
            "override": bool(override_reason),
        },
        ip_address=ip,
    )
    notifications = list(
        await notification_service.notify_hr(
            db,
            type=NotificationType.LEAVE_REQUEST_SUBMITTED,
            title="New leave request",
            message=f"{employee.full_name} requested leave starting {requested_start_date.isoformat()} ({duration} days).",
            employee=employee,
        )
    )
    await db.commit()
    await notification_service.broadcast_notifications(notifications)
    return await get_request(db, request.id)


async def approve_leave_request(
    db: AsyncSession,
    request: LeaveRequest,
    settings: CompanySettings,
    actor: User,
    ip: str | None,
    hr_comment: str | None = None,
) -> LeaveRequest:
    if request.status != LeaveRequestStatus.PENDING:
        raise ConflictError("Only pending requests can be approved", code="invalid_status_transition")

    request.status = LeaveRequestStatus.APPROVED
    request.approved_at = now_utc()
    request.reviewed_by_user_id = actor.id
    if hr_comment is not None:
        request.hr_comment = hr_comment

    # This is the actual thing the rest of the system checks: the attendance
    # engine already knows how to read the `leaves` table, so approving a
    # request just needs to add a row here - no change to attendance logic.
    leave = Leave(
        employee=request.employee,
        start_date=request.requested_start_date,
        end_date=request.requested_end_date,
        leave_type=LeaveType.VACATION,
        status=LeaveStatus.APPROVED,
        reason=request.employee_comment,
        created_by_user_id=actor.id,
    )
    db.add(leave)
    await db.flush()
    request.leave_id = leave.id

    cycle = await db.get(LeaveCycle, request.leave_cycle_id)
    cycle.status = LeaveCycleStatus.CONSUMED
    await _create_next_cycle(db, request.employee_id, cycle.cycle_number, request.requested_end_date, settings)

    audit_service.record(
        db,
        user_id=actor.id,
        action="LEAVE_REQUEST_APPROVED",
        entity_type="leave_request",
        entity_id=str(request.id),
        details={"employee_id": request.employee.employee_id, "start": request.requested_start_date.isoformat()},
        ip_address=ip,
    )

    notifications = []
    if request.employee.user is not None:
        notifications.append(
            await notification_service.notify_user(
                db,
                user_id=request.employee.user.id,
                type=NotificationType.LEAVE_REQUEST_APPROVED,
                title="Leave request approved",
                message=(
                    f"Your leave request for {request.requested_start_date.isoformat()} - "
                    f"{request.requested_end_date.isoformat()} has been approved."
                ),
                employee=request.employee,
            )
        )
    await db.commit()
    await notification_service.broadcast_notifications(notifications)
    return await get_request(db, request.id)


async def reject_leave_request(
    db: AsyncSession, request: LeaveRequest, actor: User, ip: str | None, hr_comment: str | None = None
) -> LeaveRequest:
    if request.status != LeaveRequestStatus.PENDING:
        raise ConflictError("Only pending requests can be rejected", code="invalid_status_transition")

    request.status = LeaveRequestStatus.REJECTED
    request.rejected_at = now_utc()
    request.reviewed_by_user_id = actor.id
    if hr_comment is not None:
        request.hr_comment = hr_comment

    cycle = await db.get(LeaveCycle, request.leave_cycle_id)
    cycle.status = LeaveCycleStatus.AVAILABLE  # they can submit again against the same cycle

    audit_service.record(
        db,
        user_id=actor.id,
        action="LEAVE_REQUEST_REJECTED",
        entity_type="leave_request",
        entity_id=str(request.id),
        details={"employee_id": request.employee.employee_id},
        ip_address=ip,
    )
    notifications = []
    if request.employee.user is not None:
        notifications.append(
            await notification_service.notify_user(
                db,
                user_id=request.employee.user.id,
                type=NotificationType.LEAVE_REQUEST_REJECTED,
                title="Leave request rejected",
                message=f"Your leave request for {request.requested_start_date.isoformat()} was not approved.",
                employee=request.employee,
            )
        )
    await db.commit()
    await notification_service.broadcast_notifications(notifications)
    return await get_request(db, request.id)


async def cancel_leave_request(db: AsyncSession, request: LeaveRequest, actor: User, ip: str | None) -> LeaveRequest:
    if request.status != LeaveRequestStatus.PENDING:
        raise ConflictError("Only pending requests can be cancelled", code="invalid_status_transition")
    if actor.role != UserRole.HR and actor.employee_id != request.employee_id:
        raise ForbiddenError("You can only cancel your own leave request", code="forbidden")

    request.status = LeaveRequestStatus.CANCELLED
    request.cancelled_at = now_utc()

    cycle = await db.get(LeaveCycle, request.leave_cycle_id)
    cycle.status = LeaveCycleStatus.AVAILABLE

    audit_service.record(
        db,
        user_id=actor.id,
        action="LEAVE_REQUEST_CANCELLED",
        entity_type="leave_request",
        entity_id=str(request.id),
        details={"employee_id": request.employee.employee_id},
        ip_address=ip,
    )
    await db.commit()
    return await get_request(db, request.id)


async def update_hr_comment(db: AsyncSession, request: LeaveRequest, comment: str, actor: User, ip: str | None) -> LeaveRequest:
    request.hr_comment = comment
    audit_service.record(
        db,
        user_id=actor.id,
        action="LEAVE_COMMENT_ADDED",
        entity_type="leave_request",
        entity_id=str(request.id),
        details={"employee_id": request.employee.employee_id},
        ip_address=ip,
    )
    await db.commit()
    return await get_request(db, request.id)


async def update_duration(
    db: AsyncSession, request: LeaveRequest, new_duration_days: int, actor: User, ip: str | None
) -> LeaveRequest:
    """HR-only adjustment of a still-pending request's duration/end date. Only
    permitted while PENDING: once approved, a Leave row and the next cycle have
    already been created from the original duration (see approve_leave_request),
    so changing it after the fact would silently desynchronize those."""
    if request.status != LeaveRequestStatus.PENDING:
        raise ConflictError("Only pending requests can have their duration adjusted", code="invalid_status_transition")

    old_duration = request.duration_days
    request.duration_days = new_duration_days
    request.requested_end_date = request.requested_start_date + timedelta(days=new_duration_days - 1)

    audit_service.record(
        db,
        user_id=actor.id,
        action="LEAVE_DURATION_ADJUSTED",
        entity_type="leave_request",
        entity_id=str(request.id),
        details={
            "employee_id": request.employee.employee_id,
            "old_duration_days": old_duration,
            "new_duration_days": new_duration_days,
        },
        ip_address=ip,
    )
    await db.commit()
    return await get_request(db, request.id)


async def list_requests(
    db: AsyncSession,
    *,
    viewer: User,
    employee_id: int | None,
    department_id: int | None,
    status: LeaveRequestStatus | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
) -> tuple[list[LeaveRequest], int]:
    filters = []
    if viewer.role != UserRole.HR:
        filters.append(LeaveRequest.employee_id == viewer.employee_id)
    elif employee_id is not None:
        filters.append(LeaveRequest.employee_id == employee_id)
    if department_id is not None:
        filters.append(Employee.department_id == department_id)
    if status is not None:
        filters.append(LeaveRequest.status == status)
    if date_from is not None:
        filters.append(LeaveRequest.requested_start_date >= date_from)
    if date_to is not None:
        filters.append(LeaveRequest.requested_start_date <= date_to)

    total = (
        await db.execute(
            select(func.count(LeaveRequest.id)).select_from(LeaveRequest).join(LeaveRequest.employee).where(*filters)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            _base_query()
            .where(*filters)
            .order_by(LeaveRequest.submitted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).unique().scalars().all()
    return list(rows), total


async def get_calendar(db: AsyncSession, date_from: date, date_to: date) -> list[LeaveRequest]:
    rows = (
        await db.execute(
            _base_query()
            .where(
                LeaveRequest.status.in_([LeaveRequestStatus.APPROVED, LeaveRequestStatus.COMPLETED]),
                LeaveRequest.requested_start_date <= date_to,
                LeaveRequest.requested_end_date >= date_from,
            )
            .order_by(LeaveRequest.requested_start_date)
        )
    ).unique().scalars().all()
    return list(rows)


async def get_eligibility(db: AsyncSession, employee: Employee, settings: CompanySettings) -> LeaveEligibilityResponse:
    cycle = await get_or_create_current_cycle(db, employee, settings)
    today = today_local()

    # Defined by status, not by which cycle a row happens to be attached to: the
    # cycle advances immediately on approval (see get_or_create_current_cycle), so
    # an approved-but-not-yet-taken leave would otherwise flip to "previous" the
    # instant it's approved, even though it's still upcoming.
    current_request = (
        await db.execute(
            _base_query()
            .where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status.in_([LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]),
            )
            .order_by(LeaveRequest.id.desc())
            .limit(1)
        )
    ).unique().scalar_one_or_none()

    previous_request = (
        await db.execute(
            _base_query()
            .where(LeaveRequest.employee_id == employee.id, LeaveRequest.status == LeaveRequestStatus.COMPLETED)
            .order_by(LeaveRequest.id.desc())
            .limit(1)
        )
    ).unique().scalar_one_or_none()

    # Only new information while still PENDING: once approved, the cycle has
    # already advanced (see above) and the top-level eligibility_date above
    # already reports exactly this.
    next_eligibility_date = None
    if current_request is not None and current_request.status == LeaveRequestStatus.PENDING:
        next_eligibility_date = current_request.requested_end_date + relativedelta(
            months=settings.leave_next_cycle_after_months
        )

    return LeaveEligibilityResponse(
        employee=EmployeeBrief.model_validate(employee),
        employment_start_date=employee.employment_start_date,
        annual_leave_duration_days=resolve_leave_duration(employee, settings),
        cycle_number=cycle.cycle_number,
        work_period_start=cycle.cycle_start_date,
        work_period_end=cycle.cycle_end_date,
        eligibility_date=cycle.eligibility_date,
        is_eligible=today >= cycle.eligibility_date,
        cycle_status=cycle.status,
        current_request=to_response(current_request) if current_request else None,
        previous_leave=to_response(previous_request) if previous_request else None,
        next_eligibility_date=next_eligibility_date,
    )


async def mark_completed_requests(db: AsyncSession) -> int:
    """Scheduler sweep: approved requests whose leave period has fully passed become
    COMPLETED. Purely informational - cycles already advanced at approval time."""
    today = today_local()
    rows = (
        await db.execute(
            select(LeaveRequest).where(
                LeaveRequest.status == LeaveRequestStatus.APPROVED, LeaveRequest.requested_end_date < today
            )
        )
    ).scalars().all()
    for row in rows:
        row.status = LeaveRequestStatus.COMPLETED
    if rows:
        await db.commit()
    return len(rows)


async def send_eligibility_reminders(db: AsyncSession, settings: CompanySettings) -> int:
    """Scheduler sweep: notifies HR (and the employee, if they have a login) when
    an employee's eligibility date is exactly 30/14/7 days away. Deduplicated via
    the audit log so a reminder is never sent twice for the same (cycle, milestone)."""
    today = today_local()
    milestones = [
        days
        for days, enabled in (
            (30, settings.leave_reminder_30_days_enabled),
            (14, settings.leave_reminder_14_days_enabled),
            (7, settings.leave_reminder_7_days_enabled),
        )
        if enabled
    ]

    sent = 0
    for days_before in milestones:
        target_date = today + timedelta(days=days_before)
        cycles = (
            await db.execute(
                select(LeaveCycle)
                .join(LeaveCycle.employee)
                .options(contains_eager(LeaveCycle.employee).selectinload(Employee.user))
                .where(
                    LeaveCycle.eligibility_date == target_date,
                    LeaveCycle.status == LeaveCycleStatus.AVAILABLE,
                    Employee.status == EmploymentStatus.ACTIVE,
                )
            )
        ).unique().scalars().all()

        for cycle in cycles:
            dedup_key = f"{cycle.id}:{days_before}"
            already_sent = (
                await db.execute(
                    select(AuditLog.id)
                    .where(AuditLog.action == "LEAVE_REMINDER_SENT", AuditLog.entity_id == dedup_key)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if already_sent is not None:
                continue

            employee = cycle.employee
            audit_service.record(
                db,
                user_id=None,
                action="LEAVE_REMINDER_SENT",
                entity_type="leave_cycle",
                entity_id=dedup_key,
                details={"employee_id": employee.employee_id, "days_before": days_before},
            )
            notifications = list(
                await notification_service.notify_hr(
                    db,
                    type=NotificationType.LEAVE_ELIGIBILITY_REMINDER,
                    title="Leave eligibility approaching",
                    message=f"{employee.full_name} becomes eligible for annual leave in {days_before} days.",
                    employee=employee,
                )
            )
            if employee.user is not None:
                notifications.append(
                    await notification_service.notify_user(
                        db,
                        user_id=employee.user.id,
                        type=NotificationType.LEAVE_ELIGIBILITY_REMINDER,
                        title="Your annual leave eligibility is approaching",
                        message=f"You will become eligible for annual leave in {days_before} days.",
                        employee=employee,
                    )
                )
            sent += 1
            await db.commit()
            await notification_service.broadcast_notifications(notifications)
    return sent
