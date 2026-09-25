from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.settings import CompanySettings
from app.models.user import User
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services import audit_service

DEFAULT_WORK_START = time(9, 0)
DEFAULT_WORK_END = time(18, 0)
DEFAULT_GRACE_MINUTES = 15
DEFAULT_DUPLICATE_WINDOW_SECONDS = 60
DEFAULT_WORKING_DAYS = "1,2,3,4,5"


async def get_or_create(db: AsyncSession) -> CompanySettings:
    row = (await db.execute(select(CompanySettings).order_by(CompanySettings.id).limit(1))).scalar_one_or_none()
    if row is not None:
        return row

    row = CompanySettings(
        company_name=get_settings().COMPANY_NAME,
        work_start_time=DEFAULT_WORK_START,
        work_end_time=DEFAULT_WORK_END,
        grace_period_minutes=DEFAULT_GRACE_MINUTES,
        duplicate_event_window_seconds=DEFAULT_DUPLICATE_WINDOW_SECONDS,
        working_days=DEFAULT_WORKING_DAYS,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update(db: AsyncSession, data: SettingsUpdate, actor: User, ip: str | None) -> CompanySettings:
    row = await get_or_create(db)
    changes = data.model_dump(exclude_unset=True)
    if "working_days" in changes and changes["working_days"] is not None:
        changes["working_days"] = ",".join(str(day) for day in changes["working_days"])

    before = {key: _serialisable(getattr(row, key)) for key in changes}
    for key, value in changes.items():
        if value is not None:
            setattr(row, key, value)
    row.updated_by_user_id = actor.id

    audit_service.record(
        db,
        user_id=actor.id,
        action="SETTINGS_UPDATED",
        entity_type="company_settings",
        entity_id=str(row.id),
        details={"before": before, "after": {key: _serialisable(getattr(row, key)) for key in changes}},
        ip_address=ip,
    )
    await db.commit()
    await db.refresh(row)
    return row


def to_response(row: CompanySettings) -> SettingsResponse:
    return SettingsResponse(
        company_name=row.company_name,
        timezone=get_settings().COMPANY_TIMEZONE,
        work_start_time=row.work_start_time,
        work_end_time=row.work_end_time,
        grace_period_minutes=row.grace_period_minutes,
        duplicate_event_window_seconds=row.duplicate_event_window_seconds,
        working_days=row.working_days,
        annual_leave_duration_days=row.annual_leave_duration_days,
        leave_normal_notice_days=row.leave_normal_notice_days,
        leave_force_majeure_notice_days=row.leave_force_majeure_notice_days,
        leave_eligibility_after_months=row.leave_eligibility_after_months,
        leave_next_cycle_after_months=row.leave_next_cycle_after_months,
        leave_reminder_30_days_enabled=row.leave_reminder_30_days_enabled,
        leave_reminder_14_days_enabled=row.leave_reminder_14_days_enabled,
        leave_reminder_7_days_enabled=row.leave_reminder_7_days_enabled,
        updated_at=row.updated_at,
    )


def _serialisable(value):
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return value
