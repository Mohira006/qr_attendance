from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def record(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Queue an audit entry in the current transaction so it is committed (or rolled back)
    together with the action it describes."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry


async def list_entries(
    db: AsyncSession,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    filters = []
    if action is not None:
        filters.append(AuditLog.action == action)
    if entity_type is not None:
        filters.append(AuditLog.entity_type == entity_type)
    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)

    total = (await db.execute(select(func.count(AuditLog.id)).where(*filters))).scalar_one()
    rows = (
        await db.execute(
            select(AuditLog).where(*filters).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return list(rows), total
