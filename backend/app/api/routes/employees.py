from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DB, ClientIP, CurrentUser, HRUser
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import EmploymentStatus, UserRole
from app.schemas.common import Page
from app.schemas.employee import (
    EmployeeAccountCreate,
    EmployeeAccountResponse,
    EmployeeAccountUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.schemas.leave import LeaveEligibilityResponse
from app.services import employee_service, leave_service, photo_storage, settings_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=Page[EmployeeResponse])
async def list_employees(
    db: DB,
    _: HRUser,
    search: Annotated[str | None, Query(max_length=100)] = None,
    department_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[EmploymentStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[EmployeeResponse]:
    items, total = await employee_service.list_employees(
        db, search=search, department_id=department_id, status=status_filter, page=page, page_size=page_size
    )
    return Page.build([EmployeeResponse.model_validate(item) for item in items], total, page, page_size)


@router.get("/me", response_model=EmployeeResponse)
async def my_profile(db: DB, user: CurrentUser) -> EmployeeResponse:
    if user.employee_id is None:
        raise NotFoundError("This account is not linked to an employee", code="employee_not_found")
    return EmployeeResponse.model_validate(await employee_service.get_employee(db, user.employee_id))


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(payload: EmployeeCreate, db: DB, actor: HRUser, ip: ClientIP) -> EmployeeResponse:
    return EmployeeResponse.model_validate(await employee_service.create_employee(db, payload, actor, ip))


@router.get("/{employee_pk}", response_model=EmployeeResponse)
async def get_employee(employee_pk: int, db: DB, _: HRUser) -> EmployeeResponse:
    return EmployeeResponse.model_validate(await employee_service.get_employee(db, employee_pk))


@router.put("/{employee_pk}", response_model=EmployeeResponse)
async def update_employee(
    employee_pk: int, payload: EmployeeUpdate, db: DB, actor: HRUser, ip: ClientIP
) -> EmployeeResponse:
    employee = await employee_service.get_employee(db, employee_pk)
    return EmployeeResponse.model_validate(await employee_service.update_employee(db, employee, payload, actor, ip))


@router.delete("/{employee_pk}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_employee(employee_pk: int, db: DB, actor: HRUser, ip: ClientIP) -> Response:
    """Soft delete: the employee is marked inactive and their login account is disabled.
    Attendance history is kept."""
    employee = await employee_service.get_employee(db, employee_pk)
    await employee_service.deactivate_employee(db, employee, actor, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{employee_pk}/photo", response_model=EmployeeResponse)
async def upload_photo(
    employee_pk: int,
    db: DB,
    actor: HRUser,
    ip: ClientIP,
    file: Annotated[UploadFile, File()],
) -> EmployeeResponse:
    employee = await employee_service.get_employee(db, employee_pk)
    return EmployeeResponse.model_validate(await employee_service.set_profile_photo(db, employee, file, actor, ip))


@router.get("/{employee_pk}/photo")
async def get_photo(employee_pk: int, db: DB, user: CurrentUser) -> FileResponse:
    if user.role != UserRole.HR and user.employee_id != employee_pk:
        raise ForbiddenError("You can only view your own photo", code="forbidden")
    employee = await employee_service.get_employee(db, employee_pk)
    if not employee.profile_photo:
        raise NotFoundError("This employee has no profile photo", code="photo_not_found")
    path = photo_storage.resolve(employee.profile_photo)
    if not path.is_file():
        raise NotFoundError("Profile photo file is missing", code="photo_not_found")
    return FileResponse(path)


@router.post("/{employee_pk}/account", response_model=EmployeeAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    employee_pk: int, payload: EmployeeAccountCreate, db: DB, actor: HRUser, ip: ClientIP
) -> EmployeeAccountResponse:
    employee = await employee_service.get_employee(db, employee_pk)
    return EmployeeAccountResponse.model_validate(await employee_service.create_account(db, employee, payload, actor, ip))


@router.put("/{employee_pk}/account", response_model=EmployeeAccountResponse)
async def update_account(
    employee_pk: int, payload: EmployeeAccountUpdate, db: DB, actor: HRUser, ip: ClientIP
) -> EmployeeAccountResponse:
    employee = await employee_service.get_employee(db, employee_pk)
    return EmployeeAccountResponse.model_validate(await employee_service.update_account(db, employee, payload, actor, ip))


@router.get("/{employee_pk}/leave-eligibility", response_model=LeaveEligibilityResponse)
async def get_leave_eligibility(employee_pk: int, db: DB, user: CurrentUser) -> LeaveEligibilityResponse:
    if user.role != UserRole.HR and user.employee_id != employee_pk:
        raise ForbiddenError("You can only view your own leave eligibility", code="forbidden")
    employee = await employee_service.get_employee(db, employee_pk)
    settings = await settings_service.get_or_create(db)
    return await leave_service.get_eligibility(db, employee, settings)
