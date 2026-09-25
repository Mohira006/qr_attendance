from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import LeaveCycleStatus


class LeaveCycle(TimestampMixin, Base):
    """One eligibility period per employee. Cycle 1 starts at employment_start_date
    (eligible after `leave_eligibility_after_months`, default 6). Cycle N+1 starts at
    the end date of cycle N's approved leave (eligible after `leave_next_cycle_after_months`,
    default 11) - created automatically the moment cycle N's request is approved, not
    when the leave is actually taken.

    `cycle_end_date` is a nominal, display-only one-year window (the "work period"
    shown to HR/employees). It does not gate anything: once eligible, an employee
    stays eligible until they actually take leave - there is no forfeiture rule.
    """

    __tablename__ = "leave_cycles"
    __table_args__ = (
        UniqueConstraint("employee_id", "cycle_number", name="uq_leave_cycles_employee_number"),
        Index("ix_leave_cycles_employee_status", "employee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    eligibility_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[LeaveCycleStatus] = mapped_column(
        str_enum(LeaveCycleStatus, "leave_cycle_status"),
        default=LeaveCycleStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    employee: Mapped["Employee"] = relationship(lazy="joined")  # noqa: F821
    requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="cycle", lazy="raise")  # noqa: F821
