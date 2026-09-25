from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, Index, Integer, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.types import UTCDateTime
from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import AttendanceStatus, CheckoutStatus


class Attendance(TimestampMixin, Base):
    """One record per employee per work date. Created on check-in, closed on check-out.

    `date` is the local calendar date of the check-in; for overnight shifts the
    check-out may fall on the next calendar day.
    """

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
        Index("ix_attendance_date_status", "date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    check_out: Mapped[datetime | None] = mapped_column(UTCDateTime)
    status: Mapped[AttendanceStatus] = mapped_column(
        str_enum(AttendanceStatus, "attendance_status"), nullable=False, index=True
    )
    checkout_status: Mapped[CheckoutStatus] = mapped_column(
        str_enum(CheckoutStatus, "checkout_status"),
        default=CheckoutStatus.PENDING,
        nullable=False,
        index=True,
    )
    late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_working_minutes: Mapped[int | None] = mapped_column(Integer)
    # Snapshot of the working hours that applied when the record was created, so
    # history and explanation letters stay correct after HR changes the settings.
    expected_check_in: Mapped[time] = mapped_column(Time, nullable=False)
    expected_check_out: Mapped[time] = mapped_column(Time, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="attendance_records", lazy="joined")  # noqa: F821
    explanation_letter: Mapped["ExplanationLetter | None"] = relationship(  # noqa: F821
        back_populates="attendance", uselist=False, lazy="raise"
    )

    @property
    def explanation_letter_id(self) -> int | None:
        return self.explanation_letter.id if self.explanation_letter is not None else None
