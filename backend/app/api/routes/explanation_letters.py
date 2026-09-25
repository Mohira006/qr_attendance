from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DB, ClientIP, CurrentUser, HRUser
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import LetterStatus, UserRole
from app.schemas.common import Page
from app.schemas.explanation_letter import (
    ExplanationLetterResponse,
    RequestExplanationLetter,
    ReviewLetterRequest,
    SubmitExplanationRequest,
)
from app.services import attendance_query_service, explanation_letter_service, photo_storage

router = APIRouter(prefix="/explanation-letters", tags=["explanation-letters"])


@router.post("", response_model=ExplanationLetterResponse, status_code=status.HTTP_201_CREATED)
async def request_explanation_letter(payload: RequestExplanationLetter, db: DB, actor: HRUser, ip: ClientIP) -> ExplanationLetterResponse:
    attendance = await attendance_query_service.get_attendance(db, payload.attendance_id)
    letter = await explanation_letter_service.request_explanation(db, attendance, actor, ip)
    return ExplanationLetterResponse.model_validate(letter)


@router.get("", response_model=Page[ExplanationLetterResponse])
async def list_explanation_letters(
    db: DB,
    user: CurrentUser,
    status_filter: Annotated[LetterStatus | None, Query(alias="status")] = None,
    employee_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ExplanationLetterResponse]:
    items, total = await explanation_letter_service.list_letters(
        db,
        viewer=user,
        status=status_filter,
        employee_id=employee_id,
        department_id=department_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page.build([ExplanationLetterResponse.model_validate(item) for item in items], total, page, page_size)


@router.get("/{letter_id}", response_model=ExplanationLetterResponse)
async def get_explanation_letter(letter_id: int, db: DB, user: CurrentUser) -> ExplanationLetterResponse:
    letter = await explanation_letter_service.get_letter(db, letter_id)
    explanation_letter_service.assert_can_view(letter, user)
    return ExplanationLetterResponse.model_validate(letter)


@router.get("/{letter_id}/pdf")
async def download_explanation_letter_pdf(letter_id: int, db: DB, user: CurrentUser) -> FileResponse:
    letter = await explanation_letter_service.get_letter(db, letter_id)
    explanation_letter_service.assert_can_view(letter, user)
    path = await explanation_letter_service.get_or_generate_pdf(db, letter)
    filename = f"explanation-letter-{letter.employee.employee_id}-{letter.date}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/{letter_id}/attachment", response_model=ExplanationLetterResponse)
async def upload_explanation_letter_attachment(
    letter_id: int, db: DB, user: CurrentUser, ip: ClientIP, file: UploadFile = File(...)
) -> ExplanationLetterResponse:
    """The employee uploads their own explanation document (PDF or photo of a
    written note). HR may also upload on the employee's behalf, matching the
    text-submission endpoint above."""
    letter = await explanation_letter_service.get_letter(db, letter_id)
    if user.role != UserRole.HR and user.employee_id != letter.employee_id:
        raise ForbiddenError("You can only upload an attachment for your own letter", code="forbidden")
    updated = await explanation_letter_service.submit_attachment(db, letter, file, user, ip)
    return ExplanationLetterResponse.model_validate(updated)


@router.get("/{letter_id}/attachment")
async def download_explanation_letter_attachment(letter_id: int, db: DB, user: CurrentUser) -> FileResponse:
    letter = await explanation_letter_service.get_letter(db, letter_id)
    explanation_letter_service.assert_can_view(letter, user)
    if letter.attachment_path is None:
        raise NotFoundError("No attachment has been uploaded for this letter", code="attachment_not_found")
    path = photo_storage.resolve(letter.attachment_path)
    return FileResponse(path, filename=Path(letter.attachment_path).name)


@router.put("/{letter_id}/explanation", response_model=ExplanationLetterResponse)
async def submit_explanation(
    letter_id: int, payload: SubmitExplanationRequest, db: DB, user: CurrentUser, ip: ClientIP
) -> ExplanationLetterResponse:
    """The employee explains their own late arrival. HR may also fill this in on
    the employee's behalf (e.g. after a verbal explanation)."""
    letter = await explanation_letter_service.get_letter(db, letter_id)
    if user.role != UserRole.HR and user.employee_id != letter.employee_id:
        raise ForbiddenError("You can only submit an explanation for your own letter", code="forbidden")
    updated = await explanation_letter_service.submit_explanation(db, letter, payload.employee_explanation, user, ip)
    return ExplanationLetterResponse.model_validate(updated)


@router.put("/{letter_id}/review", response_model=ExplanationLetterResponse)
async def review_explanation_letter(
    letter_id: int, payload: ReviewLetterRequest, db: DB, actor: HRUser, ip: ClientIP
) -> ExplanationLetterResponse:
    letter = await explanation_letter_service.get_letter(db, letter_id)
    updated = await explanation_letter_service.review_letter(db, letter, payload.hr_comment, actor, ip)
    return ExplanationLetterResponse.model_validate(updated)
