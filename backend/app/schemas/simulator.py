from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FaceEventRequestType
from app.schemas.common import ORMModel
from app.schemas.department import DepartmentBrief
from app.schemas.face_event import FaceEventResponse


class SimulatorEmployeeOption(ORMModel):
    """Lightweight entry for a simulator employee picker."""

    id: int
    employee_id: str
    full_name: str
    department: DepartmentBrief
    face_recognition_id: str | None


class SimulatorTriggerRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=128, description="employee_id or face_recognition_id")
    requested_type: FaceEventRequestType = FaceEventRequestType.AUTO
    # Defaults to now if omitted; useful for replaying a specific moment (e.g. the spec's demo scenario).
    timestamp: datetime | None = None


class SimulatorTriggerResponse(FaceEventResponse):
    pass
