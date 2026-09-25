from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.schemas.common import Message, Page
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationResponse])
async def list_notifications(
    db: DB,
    user: CurrentUser,
    unread_only: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[NotificationResponse]:
    items, total = await notification_service.list_for_user(
        db, user.id, unread_only=unread_only, page=page, page_size=page_size
    )
    return Page.build([NotificationResponse.model_validate(item) for item in items], total, page, page_size)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(db: DB, user: CurrentUser) -> UnreadCountResponse:
    count = await notification_service.unread_count(db, user.id)
    return UnreadCountResponse(unread_count=count)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(notification_id: int, db: DB, user: CurrentUser) -> NotificationResponse:
    notification = await notification_service.mark_read(db, user.id, notification_id)
    return NotificationResponse.model_validate(notification)


@router.put("/read-all", response_model=Message)
async def mark_all_read(db: DB, user: CurrentUser) -> Message:
    count = await notification_service.mark_all_read(db, user.id)
    return Message(message=f"Marked {count} notification(s) as read")
