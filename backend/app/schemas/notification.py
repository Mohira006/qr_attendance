from datetime import datetime

from app.models.enums import NotificationType
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeBrief


class NotificationResponse(ORMModel):
    id: int
    type: NotificationType
    title: str
    message: str
    employee: EmployeeBrief | None
    attendance_id: int | None
    explanation_letter_id: int | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class UnreadCountResponse(ORMModel):
    unread_count: int
