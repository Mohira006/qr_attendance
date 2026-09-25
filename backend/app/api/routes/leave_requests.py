from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DB, ClientIP, CurrentUser, HRUser
from app.core.exceptions import BadRequestError
from app.models.enums import LeaveRequestStatus
from app.schemas.common import Page
from app.schemas.leave import (
    HrLeaveRequestCreate,
    LeaveCommentUpdate,
    LeaveDurationUpdate,
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveRequestReview,
)
from app.services import employee_service, leave_service, settings_service

router = APIRouter(prefix="/leave-requests", tags=["leave"])


# Registered before "/{request_id}" so "calendar" is never matched as a request id.
@router.get("/calendar", response_model=list[LeaveRequestResponse])
async def leave_calendar(
    db: DB,
    _: HRUser,
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
) -> list[LeaveRequestResponse]:
    rows = await leave_service.get_calendar(db, date_from, date_to)
    return [leave_service.to_response(row) for row in rows]


@router.get("", response_model=Page[LeaveRequestResponse])
async def list_leave_requests(
    db: DB,
    user: CurrentUser,
    employee_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[LeaveRequestStatus | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[LeaveRequestResponse]:
    """HR sees everyone (optionally filtered); an employee only ever sees their own
    requests regardless of the employee_id filter, enforced in the service layer."""
    items, total = await leave_service.list_requests(
        db,
        viewer=user,
        employee_id=employee_id,
        department_id=department_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page.build([leave_service.to_response(item) for item in items], total, page, page_size)


@router.post("", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_request(payload: LeaveRequestCreate, db: DB, user: CurrentUser, ip: ClientIP) -> LeaveRequestResponse:
    """An employee (or an HR user who is also an employee) requesting their own leave."""
    if user.employee_id is None:
        raise BadRequestError("This account is not linked to an employee", code="employee_not_found")
    employee = await employee_service.get_employee(db, user.employee_id)
    settings = await settings_service.get_or_create(db)
    request = await leave_service.create_leave_request(
        db,
        employee=employee,
        requested_start_date=payload.requested_start_date,
        request_type=payload.request_type,
        employee_comment=payload.employee_comment,
        settings=settings,
        actor=user,
        ip=ip,
    )
    return leave_service.to_response(request)


@router.post("/hr", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def hr_create_leave_request(payload: HrLeaveRequestCreate, db: DB, actor: HRUser, ip: ClientIP) -> LeaveRequestResponse:
    """HR submitting on an employee's behalf, with a mandatory override reason that
    bypasses the eligibility/notice-period checks (never the past-date check)."""
    employee = await employee_service.get_employee(db, payload.employee_id)
    settings = await settings_service.get_or_create(db)
    request = await leave_service.create_leave_request(
        db,
        employee=employee,
        requested_start_date=payload.requested_start_date,
        request_type=payload.request_type,
        employee_comment=payload.employee_comment,
        settings=settings,
        actor=actor,
        ip=ip,
        override_reason=payload.override_reason,
    )
    return leave_service.to_response(request)


@router.get("/{request_id}", response_model=LeaveRequestResponse)
async def get_leave_request(request_id: int, db: DB, user: CurrentUser) -> LeaveRequestResponse:
    request = await leave_service.get_request(db, request_id)
    leave_service.assert_can_view(request, user)
    return leave_service.to_response(request)


@router.put("/{request_id}/approve", response_model=LeaveRequestResponse)
async def approve_leave_request(
    request_id: int, payload: LeaveRequestReview, db: DB, actor: HRUser, ip: ClientIP
) -> LeaveRequestResponse:
    request = await leave_service.get_request(db, request_id)
    settings = await settings_service.get_or_create(db)
    updated = await leave_service.approve_leave_request(db, request, settings, actor, ip, hr_comment=payload.hr_comment)
    return leave_service.to_response(updated)


@router.put("/{request_id}/reject", response_model=LeaveRequestResponse)
async def reject_leave_request(
    request_id: int, payload: LeaveRequestReview, db: DB, actor: HRUser, ip: ClientIP
) -> LeaveRequestResponse:
    request = await leave_service.get_request(db, request_id)
    updated = await leave_service.reject_leave_request(db, request, actor, ip, hr_comment=payload.hr_comment)
    return leave_service.to_response(updated)


@router.put("/{request_id}/cancel", response_model=LeaveRequestResponse)
async def cancel_leave_request(request_id: int, db: DB, user: CurrentUser, ip: ClientIP) -> LeaveRequestResponse:
    """The employee can cancel their own pending request; HR can cancel anyone's."""
    request = await leave_service.get_request(db, request_id)
    updated = await leave_service.cancel_leave_request(db, request, user, ip)
    return leave_service.to_response(updated)


@router.put("/{request_id}/comment", response_model=LeaveRequestResponse)
async def update_leave_comment(
    request_id: int, payload: LeaveCommentUpdate, db: DB, actor: HRUser, ip: ClientIP
) -> LeaveRequestResponse:
    request = await leave_service.get_request(db, request_id)
    updated = await leave_service.update_hr_comment(db, request, payload.hr_comment, actor, ip)
    return leave_service.to_response(updated)


@router.put("/{request_id}/duration", response_model=LeaveRequestResponse)
async def update_leave_duration(
    request_id: int, payload: LeaveDurationUpdate, db: DB, actor: HRUser, ip: ClientIP
) -> LeaveRequestResponse:
    request = await leave_service.get_request(db, request_id)
    updated = await leave_service.update_duration(db, request, payload.duration_days, actor, ip)
    return leave_service.to_response(updated)
