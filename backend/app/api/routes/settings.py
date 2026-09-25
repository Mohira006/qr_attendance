from fastapi import APIRouter

from app.api.deps import DB, ClientIP, CurrentUser, HRUser
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(db: DB, _: CurrentUser) -> SettingsResponse:
    return settings_service.to_response(await settings_service.get_or_create(db))


@router.put("", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate, db: DB, actor: HRUser, ip: ClientIP) -> SettingsResponse:
    return settings_service.to_response(await settings_service.update(db, payload, actor, ip))
