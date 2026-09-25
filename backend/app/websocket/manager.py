import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from app.models.enums import UserRole

logger = logging.getLogger(__name__)


@dataclass
class _Connection:
    websocket: WebSocket
    user_id: int
    role: UserRole


@dataclass
class ConnectionManager:
    """Tracks live WebSocket connections and fans out events to them.

    In-process only: this works correctly with a single uvicorn worker. Running
    multiple workers would need a shared layer (e.g. Redis pub/sub) so an event
    handled by worker A reaches a client connected to worker B - not implemented
    here; see the README for the documented limitation.
    """

    _connections: list[_Connection] = field(default_factory=list)

    async def connect(self, websocket: WebSocket, *, user_id: int, role: UserRole) -> None:
        await websocket.accept()
        self._connections.append(_Connection(websocket=websocket, user_id=user_id, role=role))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections = [c for c in self._connections if c.websocket is not websocket]

    async def broadcast_to_hr(self, message: dict[str, Any]) -> None:
        await self._send_to_matching(message, lambda c: c.role == UserRole.HR)

    async def send_to_user(self, user_id: int, message: dict[str, Any]) -> None:
        await self._send_to_matching(message, lambda c: c.user_id == user_id)

    async def _send_to_matching(self, message: dict[str, Any], predicate) -> None:
        stale: list[_Connection] = []
        for connection in list(self._connections):
            if not predicate(connection):
                continue
            try:
                await connection.websocket.send_json(message)
            except Exception:  # noqa: BLE001 - a broken connection must not stop the fan-out
                logger.info("Dropping stale websocket connection for user %s", connection.user_id)
                stale.append(connection)
        if stale:
            self._connections = [c for c in self._connections if c not in stale]


manager = ConnectionManager()
