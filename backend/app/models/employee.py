from datetime import date, datetime, time

from sqlalchemy import ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.types import UTCDateTime
from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import EmploymentStatus


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Human-readable company identifier, e.g. EMP001. Distinct from the primary key.
    employee_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    # Relative path inside STORAGE_PATH; served through an authenticated endpoint only.
    profile_photo: Mapped[str | None] = mapped_column(String(512))
    # Optional per-employee override of department / company working hours.
    work_start_time: Mapped[time | None] = mapped_column(Time)
    work_end_time: Mapped[time | None] = mapped_column(Time)
    # Real-world hire date - distinct from created_at (when the row was added to this
    # system, which may postdate the actual hire). Drives the leave eligibility engine.
    employment_start_date: Mapped[date] = mapped_column(nullable=False, index=True)
    # Per-employee override of the company-wide annual leave duration (e.g. extra
    # days for long-tenured staff). NULL means "use the company default" - same
    # override pattern as work_start_time/work_end_time above.
    annual_leave_duration_days: Mapped[int | None] = mapped_column(Integer)
    # Timestamp of this employee's most recent QR-code scan, regardless of outcome -
    # used only to detect near-simultaneous repeat scans within the duplicate window
    # (see attendance_service.process_scan). Not a history; always overwritten.
    last_scan_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    status: Mapped[EmploymentStatus] = mapped_column(
        str_enum(EmploymentStatus, "employment_status"),
        default=EmploymentStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    department: Mapped["Department"] = relationship(back_populates="employees", lazy="joined")  # noqa: F821
    user: Mapped["User | None"] = relationship(back_populates="employee", uselist=False, lazy="raise")  # noqa: F821
    attendance_records: Mapped[list["Attendance"]] = relationship(back_populates="employee", lazy="raise")  # noqa: F821

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        return self.status == EmploymentStatus.ACTIVE
