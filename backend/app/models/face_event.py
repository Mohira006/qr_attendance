from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import now_utc
from app.core.types import UTCDateTime
from app.models.base import Base, str_enum
from app.models.enums import FaceEventOutcome, FaceEventRequestType


class FaceEvent(Base):
    """Append-only audit trail of recognition events, including the ones that
    did not change attendance (duplicates, unknown identities, rejections)."""

    __tablename__ = "face_events"
    __table_args__ = (Index("ix_face_events_employee_timestamp", "employee_id", "timestamp"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    # Raw identifier sent by the device: an employee_id (EMP001) or a face_recognition_id.
    identifier: Mapped[str | None] = mapped_column(String(128))
    requested_type: Mapped[FaceEventRequestType] = mapped_column(
        str_enum(FaceEventRequestType, "face_event_request_type"),
        default=FaceEventRequestType.AUTO,
        nullable=False,
    )
    outcome: Mapped[FaceEventOutcome] = mapped_column(
        str_enum(FaceEventOutcome, "face_event_outcome"), nullable=False, index=True
    )
    # Time of the recognition as reported by the device (authoritative for attendance).
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    # Time the backend received it (differs when a device retries after a network outage).
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    attendance_id: Mapped[int | None] = mapped_column(ForeignKey("attendance.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False)

    employee: Mapped["Employee | None"] = relationship(lazy="raise")  # noqa: F821
    attendance: Mapped["Attendance | None"] = relationship(lazy="raise")  # noqa: F821
