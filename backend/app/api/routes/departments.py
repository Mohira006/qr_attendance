from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DB, ClientIP, CurrentUser, HRUser
from app.models.enums import DepartmentStatus
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    db: DB,
    _: CurrentUser,
    status_filter: Annotated[DepartmentStatus | None, Query(alias="status")] = None,
) -> list[DepartmentResponse]:
    return await department_service.list_departments(db, status=status_filter)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(payload: DepartmentCreate, db: DB, actor: HRUser, ip: ClientIP) -> DepartmentResponse:
    return await department_service.create_department(db, payload, actor, ip)


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(department_id: int, db: DB, _: HRUser) -> DepartmentResponse:
    return await department_service.get_department_response(db, department_id)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int, payload: DepartmentUpdate, db: DB, actor: HRUser, ip: ClientIP
) -> DepartmentResponse:
    department = await department_service.get_department(db, department_id)
    return await department_service.update_department(db, department, payload, actor, ip)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_department(department_id: int, db: DB, actor: HRUser, ip: ClientIP) -> Response:
    """Soft delete: the department is marked inactive. Existing employees keep their assignment;
    new assignments to an inactive department are rejected."""
    department = await department_service.get_department(db, department_id)
    await department_service.deactivate_department(db, department, actor, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
