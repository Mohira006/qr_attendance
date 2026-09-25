from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator

from app.models.enums import DepartmentStatus
from app.schemas.common import ORMModel


class DepartmentBrief(ORMModel):
    id: int
    name: str


class DepartmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    work_start_time: time | None = None
    work_end_time: time | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def _strip(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class DepartmentCreate(DepartmentBase):
    status: DepartmentStatus = DepartmentStatus.ACTIVE


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    work_start_time: time | None = None
    work_end_time: time | None = None
    status: DepartmentStatus | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def _strip(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class DepartmentResponse(ORMModel):
    id: int
    name: str
    description: str | None
    status: DepartmentStatus
    work_start_time: time | None
    work_end_time: time | None
    employee_count: int = 0
    created_at: datetime
    updated_at: datetime
