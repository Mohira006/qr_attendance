from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import DepartmentStatus, EmploymentStatus
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services import audit_service


async def list_departments(
    db: AsyncSession, *, status: DepartmentStatus | None = None
) -> list[DepartmentResponse]:
    count_subquery = (
        select(Employee.department_id, func.count(Employee.id).label("employee_count"))
        .where(Employee.status == EmploymentStatus.ACTIVE)
        .group_by(Employee.department_id)
        .subquery()
    )
    stmt = (
        select(Department, func.coalesce(count_subquery.c.employee_count, 0))
        .outerjoin(count_subquery, count_subquery.c.department_id == Department.id)
        .order_by(Department.name)
    )
    if status is not None:
        stmt = stmt.where(Department.status == status)

    rows = (await db.execute(stmt)).all()
    return [_to_response(department, count) for department, count in rows]


async def get_department(db: AsyncSession, department_id: int) -> Department:
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundError("Department not found", code="department_not_found")
    return department


async def get_department_response(db: AsyncSession, department_id: int) -> DepartmentResponse:
    department = await get_department(db, department_id)
    return _to_response(department, await _active_employee_count(db, department_id))


async def _active_employee_count(db: AsyncSession, department_id: int) -> int:
    return (
        await db.execute(
            select(func.count(Employee.id)).where(
                Employee.department_id == department_id, Employee.status == EmploymentStatus.ACTIVE
            )
        )
    ).scalar_one()


async def _assert_name_unique(db: AsyncSession, name: str, *, exclude_id: int | None) -> None:
    stmt = select(Department.id).where(func.lower(Department.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Department.id != exclude_id)
    if (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None:
        raise ConflictError("A department with this name already exists", code="department_name_taken")


async def create_department(db: AsyncSession, data: DepartmentCreate, actor: User, ip: str | None) -> DepartmentResponse:
    await _assert_name_unique(db, data.name, exclude_id=None)
    department = Department(**data.model_dump())
    db.add(department)
    await db.flush()
    audit_service.record(
        db,
        user_id=actor.id,
        action="DEPARTMENT_CREATED",
        entity_type="department",
        entity_id=str(department.id),
        details={"name": department.name},
        ip_address=ip,
    )
    await db.commit()
    return _to_response(department, 0)


async def update_department(
    db: AsyncSession, department: Department, data: DepartmentUpdate, actor: User, ip: str | None
) -> DepartmentResponse:
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None and changes["name"] != department.name:
        await _assert_name_unique(db, changes["name"], exclude_id=department.id)

    before = {key: _audit_value(getattr(department, key)) for key in changes}
    for key, value in changes.items():
        if key == "name" and value is None:
            continue
        setattr(department, key, value)

    audit_service.record(
        db,
        user_id=actor.id,
        action="DEPARTMENT_UPDATED",
        entity_type="department",
        entity_id=str(department.id),
        details={"before": before, "after": {key: _audit_value(getattr(department, key)) for key in changes}},
        ip_address=ip,
    )
    await db.commit()
    return _to_response(department, await _active_employee_count(db, department.id))


async def deactivate_department(db: AsyncSession, department: Department, actor: User, ip: str | None) -> None:
    if department.status == DepartmentStatus.INACTIVE:
        return
    department.status = DepartmentStatus.INACTIVE
    audit_service.record(
        db,
        user_id=actor.id,
        action="DEPARTMENT_DEACTIVATED",
        entity_type="department",
        entity_id=str(department.id),
        details={"name": department.name},
        ip_address=ip,
    )
    await db.commit()


def _to_response(department: Department, employee_count: int) -> DepartmentResponse:
    response = DepartmentResponse.model_validate(department)
    response.employee_count = employee_count
    return response


def _audit_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value
