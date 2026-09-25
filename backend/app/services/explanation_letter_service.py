from datetime import date
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.enums import AttendanceStatus, LetterStatus, NotificationType, UserRole
from app.models.explanation_letter import ExplanationLetter
from app.models.user import User
from app.pdf import explanation_letter as letter_pdf
from app.services import audit_service, notification_service, photo_storage, settings_service

LETTERS_DIR = "letters"


def _base_query() -> Select[tuple[ExplanationLetter]]:
    return select(ExplanationLetter).join(ExplanationLetter.employee).options(contains_eager(ExplanationLetter.employee))


async def get_letter(db: AsyncSession, letter_id: int) -> ExplanationLetter:
    letter = (await db.execute(_base_query().where(ExplanationLetter.id == letter_id))).unique().scalar_one_or_none()
    if letter is None:
        raise NotFoundError("Explanation letter not found", code="letter_not_found")
    return letter


def assert_can_view(letter: ExplanationLetter, user: User) -> None:
    if user.role != UserRole.HR and user.employee_id != letter.employee_id:
        raise ForbiddenError("You can only view your own explanation letters", code="forbidden")


async def request_explanation(db: AsyncSession, attendance: Attendance, actor: User, ip: str | None) -> ExplanationLetter:
    """HR explicitly requests an explanation for one specific late arrival - letters
    are no longer created automatically (see the removed working_hours threshold
    logic); HR decides case by case, per attendance record."""
    if attendance.status != AttendanceStatus.LATE:
        raise BadRequestError("Can only request an explanation for a late arrival", code="not_late")
    if attendance.explanation_letter_id is not None:
        raise ConflictError(
            "An explanation letter already exists for this attendance record", code="letter_already_exists"
        )

    letter = ExplanationLetter(
        employee_id=attendance.employee_id,
        attendance_id=attendance.id,
        date=attendance.date,
        late_minutes=attendance.late_minutes,
        status=LetterStatus.PENDING,
    )
    db.add(letter)
    await db.flush()

    audit_service.record(
        db,
        user_id=actor.id,
        action="EXPLANATION_LETTER_REQUESTED",
        entity_type="explanation_letter",
        entity_id=str(letter.id),
        details={"employee_id": attendance.employee.employee_id, "attendance_id": attendance.id},
        ip_address=ip,
    )

    notifications = list(
        await notification_service.notify_hr(
            db,
            type=NotificationType.EXPLANATION_LETTER,
            title="Explanation letter requested",
            message=(
                f"An explanation letter was requested for {attendance.employee.full_name} "
                f"({attendance.late_minutes} minutes late)."
            ),
            employee=attendance.employee,
            attendance_id=attendance.id,
        )
    )
    if attendance.employee.user is not None:
        notifications.append(
            await notification_service.notify_user(
                db,
                user_id=attendance.employee.user.id,
                type=NotificationType.EXPLANATION_LETTER,
                title="Explanation needed",
                message=(
                    f"HR has requested an explanation for your late arrival on {attendance.date.isoformat()} "
                    f"({attendance.late_minutes} minutes late)."
                ),
                employee=attendance.employee,
                attendance_id=attendance.id,
            )
        )

    await db.commit()
    await notification_service.broadcast_notifications(notifications)
    return await get_letter(db, letter.id)


async def list_letters(
    db: AsyncSession,
    *,
    viewer: User,
    status: LetterStatus | None,
    employee_id: int | None,
    department_id: int | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
) -> tuple[list[ExplanationLetter], int]:
    filters = []
    if viewer.role != UserRole.HR:
        filters.append(ExplanationLetter.employee_id == viewer.employee_id)
    elif employee_id is not None:
        filters.append(ExplanationLetter.employee_id == employee_id)
    if department_id is not None:
        filters.append(Employee.department_id == department_id)
    if status is not None:
        filters.append(ExplanationLetter.status == status)
    if date_from is not None:
        filters.append(ExplanationLetter.date >= date_from)
    if date_to is not None:
        filters.append(ExplanationLetter.date <= date_to)

    total = (
        await db.execute(
            select(func.count(ExplanationLetter.id))
            .select_from(ExplanationLetter)
            .join(ExplanationLetter.employee)
            .where(*filters)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            _base_query()
            .where(*filters)
            .order_by(ExplanationLetter.date.desc(), ExplanationLetter.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).unique().scalars().all()
    return list(rows), total


async def submit_explanation(
    db: AsyncSession, letter: ExplanationLetter, text: str, actor: User, ip: str | None
) -> ExplanationLetter:
    letter.employee_explanation = text
    if letter.status == LetterStatus.PENDING:
        letter.status = LetterStatus.SUBMITTED
    letter.pdf_path = None  # invalidate the cached PDF; the next download regenerates it
    audit_service.record(
        db,
        user_id=actor.id,
        action="EXPLANATION_LETTER_SUBMITTED",
        entity_type="explanation_letter",
        entity_id=str(letter.id),
        ip_address=ip,
    )
    await db.commit()
    return await get_letter(db, letter.id)


async def submit_attachment(
    db: AsyncSession, letter: ExplanationLetter, upload: UploadFile, actor: User, ip: str | None
) -> ExplanationLetter:
    """Upload counts as submitting an explanation the same way writing text does -
    either is a valid way for the employee to respond, and either can be used
    alongside the other."""
    old_path = letter.attachment_path
    relative_path = await photo_storage.save_letter_attachment(letter.id, letter.employee.employee_id, upload)
    letter.attachment_path = relative_path
    if letter.status == LetterStatus.PENDING:
        letter.status = LetterStatus.SUBMITTED
    audit_service.record(
        db,
        user_id=actor.id,
        action="EXPLANATION_LETTER_ATTACHMENT_UPLOADED",
        entity_type="explanation_letter",
        entity_id=str(letter.id),
        ip_address=ip,
    )
    await db.commit()
    if old_path:
        photo_storage.delete_file(old_path)
    return await get_letter(db, letter.id)


async def review_letter(
    db: AsyncSession, letter: ExplanationLetter, comment: str, actor: User, ip: str | None
) -> ExplanationLetter:
    letter.hr_comment = comment
    letter.status = LetterStatus.REVIEWED
    letter.reviewed_by_user_id = actor.id
    letter.pdf_path = None
    audit_service.record(
        db,
        user_id=actor.id,
        action="EXPLANATION_LETTER_REVIEWED",
        entity_type="explanation_letter",
        entity_id=str(letter.id),
        ip_address=ip,
    )
    await db.commit()
    return await get_letter(db, letter.id)


async def get_or_generate_pdf(db: AsyncSession, letter: ExplanationLetter) -> Path:
    """Returns the on-disk path to this letter's PDF, generating (or regenerating,
    if the content changed since the last download) it on demand."""
    if letter.pdf_path:
        existing = photo_storage.resolve(letter.pdf_path)
        if existing.is_file():
            return existing

    settings = await settings_service.get_or_create(db)
    pdf_bytes = letter_pdf.generate(
        letter=letter,
        attendance=letter.attendance,
        employee=letter.employee,
        department=letter.employee.department,
        company_name=settings.company_name,
    )

    relative_path = f"{LETTERS_DIR}/{letter.employee.employee_id}-{letter.date}-{letter.id}.pdf"
    destination = photo_storage.storage_root() / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf_bytes)

    letter.pdf_path = relative_path
    await db.commit()
    return destination
