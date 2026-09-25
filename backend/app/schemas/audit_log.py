from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogResponse(ORMModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
