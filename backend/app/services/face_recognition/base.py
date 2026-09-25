from datetime import datetime
from typing import NamedTuple, Protocol


class ResolvedIdentity(NamedTuple):
    """Result of resolving a raw device identifier to the identifier we look employees up by."""

    identifier: str
    confidence: float | None


class FaceRecognitionProvider(Protocol):
    """Abstraction over however a raw recognition event gets turned into a trustworthy identifier.

    The attendance engine never talks to a device or vendor API directly; it only
    calls `resolve()` and then looks the returned identifier up against
    `employees.employee_id` / `employees.face_recognition_id`. Swapping providers
    (simulator -> a real vendor integration) means changing FACE_RECOGNITION_PROVIDER
    and, if needed, FACE_RECOGNITION_URL - no other code changes.
    """

    async def resolve(self, *, identifier: str, timestamp: datetime, device_id: str | None) -> ResolvedIdentity: ...
