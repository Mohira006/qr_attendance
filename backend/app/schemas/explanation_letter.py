from datetime import date, datetime

from pydantic import BaseModel, Field, computed_field, field_validator

from app.models.enums import LetterStatus
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeBrief


class ExplanationLetterResponse(ORMModel):
    id: int
    employee: EmployeeBrief
    attendance_id: int
    date: date
    late_minutes: int
    employee_explanation: str | None
    hr_comment: str | None
    status: LetterStatus
    reviewed_by_user_id: int | None
    created_at: datetime
    updated_at: datetime
    attachment_path: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def attachment_url(self) -> str | None:
        return f"/api/explanation-letters/{self.id}/attachment" if self.attachment_path else None


class RequestExplanationLetter(BaseModel):
    attendance_id: int


class SubmitExplanationRequest(BaseModel):
    employee_explanation: str = Field(min_length=1, max_length=4000)

    @field_validator("employee_explanation")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("explanation cannot be empty")
        return value


class ReviewLetterRequest(BaseModel):
    hr_comment: str = Field(min_length=1, max_length=4000)

    @field_validator("hr_comment")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("comment cannot be empty")
        return value
