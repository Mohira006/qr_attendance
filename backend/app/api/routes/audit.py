from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, HRUser
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import Page
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogResponse])
async def list_audit_logs(
    db: DB,
    _: HRUser,
    action: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    user_id: Annotated[int | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[AuditLogResponse]:
    items, total = await audit_service.list_entries(
        db, action=action, entity_type=entity_type, user_id=user_id, page=page, page_size=page_size
    )
    return Page.build([AuditLogResponse.model_validate(item) for item in items], total, page, page_size)
