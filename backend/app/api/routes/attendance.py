from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from app.api.deps import DB, CurrentUser, HRUser
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.time import today_local
from app.models.enums import AttendanceStatus, UserRole
from app.schemas.attendance import AttendanceResponse, DayOverviewResponse, EmployeeAttendanceSummaryResponse, ScanResponse
from app.schemas.common import Page
from app.services import attendance_query_service, attendance_service, employee_service, export_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _assert_can_view_employee(employee_id: int, user) -> None:
    if user.role != UserRole.HR and user.employee_id != employee_id:
        raise ForbiddenError("You can only view your own attendance", code="forbidden")


@router.post("/scan", response_model=ScanResponse)
async def scan(db: DB, user: CurrentUser) -> ScanResponse:
    """The employee's own phone hits this after scanning the entrance QR code -
    identity comes entirely from their own authenticated session (see
    attendance_service.process_scan), not a separate recognition system."""
    if user.employee_id is None:
        raise NotFoundError("This account is not linked to an employee", code="employee_not_found")
    employee = await employee_service.get_employee(db, user.employee_id)
    result = await attendance_service.process_scan(db, employee=employee)
    return ScanResponse(
        outcome=result.outcome,
        message=result.message,
        attendance=AttendanceResponse.model_validate(result.attendance) if result.attendance else None,
    )


@router.get("/today", response_model=DayOverviewResponse)
async def today_overview(
    db: DB,
    _: HRUser,
    target_date: Annotated[date | None, Query(alias="date")] = None,
    department_id: Annotated[int | None, Query()] = None,
) -> DayOverviewResponse:
    """Everything the dashboard, table, and card views need. Defaults to today, but
    accepts a `date` override so HR can pull up the same breakdown for a past day."""
    return await attendance_query_service.get_day_overview(db, target_date or today_local(), department_id)


@router.get("/history", response_model=Page[AttendanceResponse])
async def attendance_history(
    db: DB,
    user: CurrentUser,
    employee_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[AttendanceStatus | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[AttendanceResponse]:
    """HR sees everyone (optionally filtered); an employee only ever sees their own
    records regardless of the employee_id filter, enforced in the service layer."""
    items, total = await attendance_query_service.get_history(
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
    return Page.build([AttendanceResponse.model_validate(item) for item in items], total, page, page_size)


@router.get("/history/export")
async def export_attendance_history(
    db: DB,
    actor: HRUser,
    format: Annotated[Literal["csv", "xlsx"], Query()] = "csv",
    employee_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[AttendanceStatus | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Response:
    items, _total = await attendance_query_service.get_history(
        db,
        viewer=actor,
        employee_id=employee_id,
        department_id=department_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=1,
        page_size=export_service.MAX_EXPORT_ROWS,
    )
    filename = f"attendance-export.{format}"
    if format == "xlsx":
        content = export_service.build_xlsx(items)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = export_service.build_csv(items)
        media_type = "text/csv"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/employee/{employee_pk}", response_model=Page[AttendanceResponse])
async def employee_attendance_history(
    employee_pk: int,
    db: DB,
    user: CurrentUser,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[AttendanceResponse]:
    _assert_can_view_employee(employee_pk, user)
    await employee_service.get_employee(db, employee_pk)  # 404 if the employee doesn't exist
    items, total = await attendance_query_service.get_history(
        db,
        viewer=user,
        employee_id=employee_pk,
        department_id=None,
        status=None,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page.build([AttendanceResponse.model_validate(item) for item in items], total, page, page_size)


@router.get("/employee/{employee_pk}/summary", response_model=EmployeeAttendanceSummaryResponse)
async def employee_attendance_summary(
    employee_pk: int,
    db: DB,
    user: CurrentUser,
    month: Annotated[str | None, Query(description="YYYY-MM, defaults to the current month")] = None,
) -> EmployeeAttendanceSummaryResponse:
    _assert_can_view_employee(employee_pk, user)
    return await attendance_query_service.get_employee_summary(db, employee_pk, month)
