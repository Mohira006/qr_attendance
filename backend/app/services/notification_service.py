from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.time import now_utc
from app.models.employee import Employee
from app.models.enums import NotificationType, UserRole
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.websocket.manager import manager


async def _active_hr_user_ids(db: AsyncSession) -> list[int]:
    rows = await db.execute(select(User.id).where(User.role == UserRole.HR, User.is_active.is_(True)))
    return [row[0] for row in rows.all()]


async def notify_hr(
    db: AsyncSession,
    *,
    type: NotificationType,
    title: str,
    message: str,
    employee: Employee | None = None,
    attendance_id: int | None = None,
    explanation_letter_id: int | None = None,
) -> list[Notification]:
    """Queues one notification row per active HR user. Does not commit -
    call sites include this in the same transaction as the action it describes.

    `employee` is set as the relationship (not employee_id) so the returned rows
    already have it populated, letting the caller serialize and broadcast them
    over WebSocket immediately without a re-query.
    """
    user_ids = await _active_hr_user_ids(db)
    notifications = [
        Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            employee=employee,
            attendance_id=attendance_id,
            explanation_letter_id=explanation_letter_id,
        )
        for user_id in user_ids
    ]
    db.add_all(notifications)
    return notifications


async def notify_user(
    db: AsyncSession,
    *,
    user_id: int,
    type: NotificationType,
    title: str,
    message: str,
    employee: Employee | None = None,
    attendance_id: int | None = None,
    explanation_letter_id: int | None = None,
) -> Notification:
    """Same as notify_hr, but for a single specific recipient - e.g. telling one
    employee their leave request was approved or rejected. Does not commit."""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        employee=employee,
        attendance_id=attendance_id,
        explanation_letter_id=explanation_letter_id,
    )
    db.add(notification)
    return notification


async def list_for_user(
    db: AsyncSession, user_id: int, *, unread_only: bool, page: int, page_size: int
) -> tuple[list[Notification], int]:
    filters = [Notification.user_id == user_id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))

    total = (await db.execute(select(func.count(Notification.id)).where(*filters))).scalar_one()
    rows = (
        await db.execute(
            select(Notification)
            .where(*filters)
            .options(selectinload(Notification.employee).selectinload(Employee.department))
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return list(rows), total


async def unread_count(db: AsyncSession, user_id: int) -> int:
    return (
        await db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
    ).scalar_one()


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> Notification:
    notification = await db.get(
        Notification,
        notification_id,
        options=[selectinload(Notification.employee).selectinload(Employee.department)],
    )
    if notification is None or notification.user_id != user_id:
        raise NotFoundError("Notification not found", code="notification_not_found")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = now_utc()
        await db.commit()
    return notification


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=now_utc())
    )
    await db.commit()
    return result.rowcount or 0


async def broadcast_notifications(notifications: list[Notification]) -> None:
    """Pushes each notification to its recipient's WebSocket connection, if any.
    Shared by every service that creates notifications (attendance, leave, ...)
    so the broadcast logic lives in exactly one place."""
    for notification in notifications:
        payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
        await manager.send_to_user(notification.user_id, {"type": "notification.new", "data": payload})
