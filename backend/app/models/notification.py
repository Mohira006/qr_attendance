from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import now_utc
from app.core.types import UTCDateTime
from app.models.base import Base, str_enum
from app.models.enums import NotificationType


class Notification(Base):
    """A notification addressed to a single user. Company-wide HR notifications are
    fanned out as one row per HR user so read state is tracked per person."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(
        str_enum(NotificationType, "notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional references to the subject of the notification.
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    attendance_id: Mapped[int | None] = mapped_column(ForeignKey("attendance.id", ondelete="SET NULL"))
    explanation_letter_id: Mapped[int | None] = mapped_column(
        ForeignKey("explanation_letters.id", ondelete="SET NULL")
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False, index=True)

    user: Mapped["User"] = relationship(lazy="raise")  # noqa: F821
    employee: Mapped["Employee | None"] = relationship(lazy="raise")  # noqa: F821
