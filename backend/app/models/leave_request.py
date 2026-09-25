from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.types import UTCDateTime
from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import LeaveRequestStatus, LeaveRequestType


class LeaveRequest(TimestampMixin, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("requested_end_date >= requested_start_date", name="ck_leave_requests_date_order"),
        Index("ix_leave_requests_employee_status", "employee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_cycle_id: Mapped[int] = mapped_column(
        ForeignKey("leave_cycles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requested_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Snapshot of the HR-configured duration AT THE TIME OF SUBMISSION. Never
    # recomputed - a later change to the company setting must not alter this row.
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    request_type: Mapped[LeaveRequestType] = mapped_column(
        str_enum(LeaveRequestType, "leave_request_type"), nullable=False
    )
    status: Mapped[LeaveRequestStatus] = mapped_column(
        str_enum(LeaveRequestStatus, "leave_request_status"),
        default=LeaveRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    employee_comment: Mapped[str | None] = mapped_column(Text)
    hr_comment: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    rejected_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # True when a notice-period rule was bypassed by HR (section 13/33 of the spec).
    is_hr_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    # Set once approved: the row this request produced in the existing `leaves` table,
    # which is what the attendance engine actually checks.
    leave_id: Mapped[int | None] = mapped_column(ForeignKey("leaves.id", ondelete="SET NULL"))

    employee: Mapped["Employee"] = relationship(lazy="joined")  # noqa: F821
    cycle: Mapped["LeaveCycle"] = relationship(back_populates="requests", lazy="joined")
    leave: Mapped["Leave | None"] = relationship(lazy="raise")  # noqa: F821
