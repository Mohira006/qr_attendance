import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.database import SessionLocal
from app.core.security import TokenType, decode_token
from app.core.exceptions import UnauthorizedError
from app.models.user import User
from app.websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _authenticate(token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
        user_id = int(payload["sub"])
    except (UnauthorizedError, TypeError, ValueError):
        return None

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    """Real-time channel for the HR dashboard and employee dashboard.

    Authenticated with the same short-lived access token used for REST calls,
    passed as a query parameter (`?token=...`) since browsers cannot set custom
    headers on the WebSocket handshake. HR connections receive every event;
    employee connections receive only events about their own attendance.
    """
    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authenticated")
        return

    await manager.connect(websocket, user_id=user.id, role=user.role)
    try:
        while True:
            # Clients don't need to send anything; this simply detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
