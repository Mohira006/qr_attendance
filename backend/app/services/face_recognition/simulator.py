from datetime import datetime

from app.services.face_recognition.base import ResolvedIdentity


class SimulatorProvider:
    """Development/test provider. There is no hardware to consult, so the identifier
    supplied by the caller (the simulator UI, or a test) is trusted as-is."""

    async def resolve(self, *, identifier: str, timestamp: datetime, device_id: str | None) -> ResolvedIdentity:  # noqa: ARG002
        return ResolvedIdentity(identifier=identifier.strip(), confidence=1.0)
