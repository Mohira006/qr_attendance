from datetime import datetime, time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.core.types import UTCDateTime
from app.models.base import Base


class CompanySettings(Base):
    """Single-row table holding the company-wide attendance rules.

    Resolution order for working hours is employee -> department -> these values.
    """

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    work_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    work_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    # Recognition events for the same employee inside this window are logged but ignored.
    duplicate_event_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    # ISO weekday numbers, comma separated (Monday=1 ... Sunday=7).
    working_days: Mapped[str] = mapped_column(String(32), nullable=False, default="1,2,3,4,5")

    # --- Leave management (HR-configurable; see app/services/leave_service.py) ---
    annual_leave_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    leave_normal_notice_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    leave_force_majeure_notice_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    leave_eligibility_after_months: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    leave_next_cycle_after_months: Mapped[int] = mapped_column(Integer, nullable=False, default=11)
    leave_reminder_30_days_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    leave_reminder_14_days_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    leave_reminder_7_days_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, onupdate=now_utc, nullable=False)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    @property
    def working_day_numbers(self) -> list[int]:
        return [int(part) for part in self.working_days.split(",") if part.strip()]
