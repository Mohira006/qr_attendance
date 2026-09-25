from typing import Any

from fastapi import UploadFile
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.core.time import today_local
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import DepartmentStatus, EmploymentStatus, UserRole
from app.models.user import User
from app.schemas.employee import EmployeeAccountCreate, EmployeeAccountUpdate, EmployeeCreate, EmployeeUpdate
from app.services import audit_service, auth_service, photo_storage


def _base_query() -> Select[tuple[Employee]]:
    return (
        select(Employee)
        .join(Employee.department)
        .options(contains_eager(Employee.department), selectinload(Employee.user))
    )


async def get_employee(db: AsyncSession, employee_pk: int) -> Employee:
    # populate_existing: this is also called right after a commit to return the updated row;
    # without it an already-loaded relationship (e.g. the old department) would be served from the identity map.
    employee = (
        await db.execute(_base_query().where(Employee.id == employee_pk).execution_options(populate_existing=True))
    ).unique().scalar_one_or_none()
    if employee is None:
        raise NotFoundError("Employee not found", code="employee_not_found")
    return employee


async def get_by_code(db: AsyncSession, employee_code: str) -> Employee | None:
    return (
        (await db.execute(_base_query().where(Employee.employee_id == employee_code.strip().upper())))
        .unique()
        .scalar_one_or_none()
    )


async def list_employees(
    db: AsyncSession,
    *,
    search: str | None,
    department_id: int | None,
    status: EmploymentStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Employee], int]:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                (Employee.first_name + " " + Employee.last_name).ilike(pattern),
                Employee.employee_id.ilike(pattern),
                Employee.position.ilike(pattern),
                Department.name.ilike(pattern),
            )
        )
    if department_id is not None:
        filters.append(Employee.department_id == department_id)
    if status is not None:
        filters.append(Employee.status == status)

    total = (
        await db.execute(select(func.count(Employee.id)).select_from(Employee).join(Employee.department).where(*filters))
    ).scalar_one()
    rows = (
        await db.execute(
            _base_query()
            .where(*filters)
            .order_by(Employee.last_name, Employee.first_name, Employee.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).unique().scalars().all()
    return list(rows), total


async def _get_active_department(db: AsyncSession, department_id: int) -> Department:
    department = await db.get(Department, department_id)
    if department is None:
        raise BadRequestError("Department does not exist", code="department_not_found")
    if department.status != DepartmentStatus.ACTIVE:
        raise BadRequestError("Department is inactive", code="department_inactive")
    return department


async def _assert_unique(db: AsyncSession, column, value: str | None, *, exclude_pk: int | None, message: str, code: str) -> None:
    if value is None:
        return
    stmt = select(Employee.id).where(column == value)
    if exclude_pk is not None:
        stmt = stmt.where(Employee.id != exclude_pk)
    if (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None:
        raise ConflictError(message, code=code)


async def _assert_unique_fields(db: AsyncSession, values: dict[str, Any], *, exclude_pk: int | None) -> None:
    if "employee_id" in values:
        await _assert_unique(
            db, Employee.employee_id, values["employee_id"], exclude_pk=exclude_pk,
            message="An employee with this employee ID already exists", code="employee_id_taken",
        )
    if "email" in values:
        await _assert_unique(
            db, Employee.email, values["email"], exclude_pk=exclude_pk,
            message="An employee with this email already exists", code="email_taken",
        )


async def create_employee(db: AsyncSession, data: EmployeeCreate, actor: User, ip: str | None) -> Employee:
    values = data.model_dump()
    if values.get("employment_start_date") is None:
        values["employment_start_date"] = today_local()
    await _get_active_department(db, values["department_id"])
    await _assert_unique_fields(db, values, exclude_pk=None)

    employee = Employee(**values)
    db.add(employee)
    await db.flush()
    audit_service.record(
        db,
        user_id=actor.id,
        action="EMPLOYEE_CREATED",
        entity_type="employee",
        entity_id=str(employee.id),
        details={"employee_id": employee.employee_id},
        ip_address=ip,
    )
    await db.commit()
    return await get_employee(db, employee.id)


async def update_employee(
    db: AsyncSession, employee: Employee, data: EmployeeUpdate, actor: User, ip: str | None
) -> Employee:
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return employee

    if "department_id" in changes and changes["department_id"] != employee.department_id:
        await _get_active_department(db, changes["department_id"])
    await _assert_unique_fields(db, changes, exclude_pk=employee.id)

    before = {key: _audit_value(getattr(employee, key)) for key in changes}
    for key, value in changes.items():
        setattr(employee, key, value)

    if changes.get("status") == EmploymentStatus.INACTIVE and employee.user is not None:
        await _deactivate_account(db, employee.user)

    audit_service.record(
        db,
        user_id=actor.id,
        action="EMPLOYEE_UPDATED",
        entity_type="employee",
        entity_id=str(employee.id),
        details={"before": before, "after": {key: _audit_value(value) for key, value in changes.items()}},
        ip_address=ip,
    )
    await db.commit()
    return await get_employee(db, employee.id)


async def deactivate_employee(db: AsyncSession, employee: Employee, actor: User, ip: str | None) -> None:
    if employee.status == EmploymentStatus.INACTIVE:
        return
    employee.status = EmploymentStatus.INACTIVE
    if employee.user is not None:
        await _deactivate_account(db, employee.user)
    audit_service.record(
        db,
        user_id=actor.id,
        action="EMPLOYEE_DEACTIVATED",
        entity_type="employee",
        entity_id=str(employee.id),
        details={"employee_id": employee.employee_id},
        ip_address=ip,
    )
    await db.commit()


async def _deactivate_account(db: AsyncSession, user: User) -> None:
    user.is_active = False
    await auth_service.revoke_all_for_user(db, user.id)


async def set_profile_photo(
    db: AsyncSession, employee: Employee, upload: UploadFile, actor: User, ip: str | None
) -> Employee:
    new_path = await photo_storage.save_profile_photo(employee.employee_id, upload)
    old_path = employee.profile_photo
    employee.profile_photo = new_path
    audit_service.record(
        db,
        user_id=actor.id,
        action="EMPLOYEE_PHOTO_UPDATED",
        entity_type="employee",
        entity_id=str(employee.id),
        ip_address=ip,
    )
    await db.commit()
    photo_storage.delete_file(old_path)
    return await get_employee(db, employee.id)


async def create_account(
    db: AsyncSession, employee: Employee, data: EmployeeAccountCreate, actor: User, ip: str | None
) -> User:
    if employee.user is not None:
        raise ConflictError("This employee already has a login account", code="account_exists")
    if employee.status != EmploymentStatus.ACTIVE:
        raise BadRequestError("Cannot create an account for an inactive employee", code="employee_inactive")
    if await auth_service.get_user_by_email(db, data.email) is not None:
        raise ConflictError("A user with this email already exists", code="email_taken")

    user = User(
        employee_id=employee.id,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    audit_service.record(
        db,
        user_id=actor.id,
        action="ACCOUNT_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        details={"employee_id": employee.employee_id, "email": user.email, "role": user.role.value},
        ip_address=ip,
    )
    await db.commit()
    return user


async def update_account(
    db: AsyncSession, employee: Employee, data: EmployeeAccountUpdate, actor: User, ip: str | None
) -> User:
    user = employee.user
    if user is None:
        raise NotFoundError("This employee has no login account", code="account_not_found")

    changes = data.model_dump(exclude_unset=True)
    details: dict[str, Any] = {}
    if changes.get("password") is not None:
        user.password_hash = hash_password(changes["password"])
        await auth_service.revoke_all_for_user(db, user.id)
        details["password_reset"] = True
    if changes.get("role") is not None:
        if user.id == actor.id and changes["role"] != UserRole.HR:
            raise BadRequestError("You cannot remove your own HR role", code="self_demotion")
        details["role"] = changes["role"].value
        user.role = changes["role"]
    if changes.get("is_active") is not None:
        if user.id == actor.id and not changes["is_active"]:
            raise BadRequestError("You cannot deactivate your own account", code="self_deactivation")
        details["is_active"] = changes["is_active"]
        user.is_active = changes["is_active"]
        if not user.is_active:
            await auth_service.revoke_all_for_user(db, user.id)

    audit_service.record(
        db,
        user_id=actor.id,
        action="ACCOUNT_UPDATED",
        entity_type="user",
        entity_id=str(user.id),
        details=details,
        ip_address=ip,
    )
    await db.commit()
    return user


def _audit_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value
