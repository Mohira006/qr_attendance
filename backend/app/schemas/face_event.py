from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.models.enums import FaceEventOutcome
from app.schemas.attendance import AttendanceResponse
from app.schemas.employee import EmployeeBrief


class FaceEventRequest(BaseModel):
    """Shared request shape for all three device-facing endpoints.

    The direction (check-in / check-out / auto) is determined by which endpoint
    is called, not by a field in the body, so a real device only needs to know
    one URL. `employee_id` is accepted as an alias so the exact request body
    from the specification (section 3) works unchanged.
    """

    identifier: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("identifier", "employee_id", "face_recognition_id"),
        description="The employee_id or face_recognition_id reported by the device",
    )
    # Optional: devices should always send this. Missing only for convenience when testing manually.
    timestamp: datetime | None = Field(
        default=None, description="When the recognition happened. Naive values are read in COMPANY_TIMEZONE."
    )
    device_id: str | None = Field(default=None, max_length=64)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("identifier", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class FaceEventResponse(BaseModel):
    outcome: FaceEventOutcome
    message: str
    face_event_id: int
    employee: EmployeeBrief | None = None
    attendance: AttendanceResponse | None = None
