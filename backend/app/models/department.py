from datetime import time

from sqlalchemy import String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import DepartmentStatus


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DepartmentStatus] = mapped_column(
        str_enum(DepartmentStatus, "department_status"),
        default=DepartmentStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    # Optional override of the company-wide working hours for this department.
    work_start_time: Mapped[time | None] = mapped_column(Time)
    work_end_time: Mapped[time | None] = mapped_column(Time)

    employees: Mapped[list["Employee"]] = relationship(back_populates="department", lazy="raise")  # noqa: F821
