import re
from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

from app.core.security import PASSWORD_MAX_BYTES
from app.models.enums import EmploymentStatus, UserRole
from app.schemas.common import ORMModel
from app.schemas.department import DepartmentBrief

EMPLOYEE_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 ()-]{4,30}$")


# Validators are module-level so the create and update schemas share them.
def normalise_employee_id(cls, value):  # noqa: ARG001
    if isinstance(value, str):
        value = value.strip().upper()
        if not EMPLOYEE_ID_PATTERN.match(value):
            raise ValueError("employee_id may contain only letters, digits, '-' and '_' (2-32 characters)")
    return value


def strip_optional(cls, value):  # noqa: ARG001
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def validate_phone(cls, value):  # noqa: ARG001
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if not PHONE_PATTERN.match(value):
            raise ValueError("phone number format is invalid")
    return value


def lower_email(cls, value):  # noqa: ARG001
    if isinstance(value, str):
        value = value.strip().lower()
        return value or None
    return value


def validate_password(cls, value: str | None) -> str | None:  # noqa: ARG001
    if value is not None and len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(f"password must be at most {PASSWORD_MAX_BYTES} bytes")
    return value


class EmployeeAccountResponse(ORMModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    last_login_at: datetime | None


class EmployeeBase(BaseModel):
    employee_id: str = Field(min_length=2, max_length=32, description="Company employee code, e.g. EMP001")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    department_id: int
    position: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None

    _normalise_employee_id = field_validator("employee_id", mode="before")(normalise_employee_id)
    _strip = field_validator("first_name", "last_name", "position", mode="before")(strip_optional)
    _validate_phone = field_validator("phone", mode="before")(validate_phone)
    _lower_email = field_validator("email", mode="before")(lower_email)


class EmployeeCreate(EmployeeBase):
    # Optional here even though the column is NOT NULL: callers written before this
    # field existed (the employee-creation form shipped in an earlier stage) don't
    # send it. employee_service defaults it to today when omitted.
    employment_start_date: date | None = None
    # Per-employee override of the company-wide annual leave duration. None means
    # "use the company default" - same as the work_start_time/work_end_time pattern.
    annual_leave_duration_days: int | None = Field(default=None, ge=1, le=365)
    status: EmploymentStatus = EmploymentStatus.ACTIVE


class EmployeeUpdate(BaseModel):
    employee_id: str | None = Field(default=None, min_length=2, max_length=32)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None
    employment_start_date: date | None = None
    annual_leave_duration_days: int | None = Field(default=None, ge=1, le=365)
    status: EmploymentStatus | None = None

    _normalise_employee_id = field_validator("employee_id", mode="before")(normalise_employee_id)
    _strip = field_validator("first_name", "last_name", "position", mode="before")(strip_optional)
    _validate_phone = field_validator("phone", mode="before")(validate_phone)
    _lower_email = field_validator("email", mode="before")(lower_email)


class EmployeeBrief(ORMModel):
    id: int
    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    department: DepartmentBrief
    position: str | None
    profile_photo: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def profile_photo_url(self) -> str | None:
        return f"/api/employees/{self.id}/photo" if self.profile_photo else None


class EmployeeResponse(EmployeeBrief):
    phone: str | None
    email: EmailStr | None
    work_start_time: time | None
    work_end_time: time | None
    employment_start_date: date
    annual_leave_duration_days: int | None
    status: EmploymentStatus
    account: EmployeeAccountResponse | None = Field(default=None, validation_alias="user")
    created_at: datetime
    updated_at: datetime


class EmployeeAccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.EMPLOYEE

    _lower_email = field_validator("email", mode="before")(lower_email)
    _validate_password = field_validator("password")(validate_password)


class EmployeeAccountUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    is_active: bool | None = None

    _validate_password = field_validator("password")(validate_password)
