from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import LeaveStatus, LeaveType


class Leave(TimestampMixin, Base):
    __tablename__ = "leaves"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_leaves_date_order"),
        Index("ix_leaves_employee_dates", "employee_id", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(str_enum(LeaveType, "leave_type"), nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        str_enum(LeaveStatus, "leave_status"), default=LeaveStatus.APPROVED, nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    employee: Mapped["Employee"] = relationship(lazy="joined")  # noqa: F821





















