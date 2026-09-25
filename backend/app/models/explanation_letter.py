from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import LetterStatus


class ExplanationLetter(TimestampMixin, Base):
    __tablename__ = "explanation_letters"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # One letter per attendance record.
    attendance_id: Mapped[int] = mapped_column(
        ForeignKey("attendance.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Relative path inside STORAGE_PATH; regenerated when the explanation or comment changes.
    pdf_path: Mapped[str | None] = mapped_column(String(512))
    # Relative path inside STORAGE_PATH for the employee's own uploaded document
    # (PDF or photo of a written explanation), independent of the system-generated PDF above.
    attachment_path: Mapped[str | None] = mapped_column(String(512))
    employee_explanation: Mapped[str | None] = mapped_column(Text)
    hr_comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LetterStatus] = mapped_column(
        str_enum(LetterStatus, "letter_status"), default=LetterStatus.PENDING, nullable=False, index=True
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    employee: Mapped["Employee"] = relationship(lazy="joined")  # noqa: F821
    attendance: Mapped["Attendance"] = relationship(back_populates="explanation_letter", lazy="joined")  # noqa: F821
