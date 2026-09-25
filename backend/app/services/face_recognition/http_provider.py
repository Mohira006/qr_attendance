from datetime import datetime

import httpx

from app.core.exceptions import BadRequestError
from app.services.face_recognition.base import ResolvedIdentity

_TIMEOUT_SECONDS = 5.0


class HttpProvider:
    """Calls an external face recognition service to resolve/confirm a device's raw
    identifier before it reaches the attendance engine.

    If FACE_RECOGNITION_URL is not configured, this behaves like the simulator
    (trusts the identifier as-is) so the system keeps working for devices that
    already resolve identity locally and only report the final employee/face ID -
    which is what the specification's own example request does.
    """

    def __init__(self, url: str | None, api_key: str | None) -> None:
        self._url = url
        self._api_key = api_key

    async def resolve(self, *, identifier: str, timestamp: datetime, device_id: str | None) -> ResolvedIdentity:
        identifier = identifier.strip()
        if not self._url:
            return ResolvedIdentity(identifier=identifier, confidence=None)

        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        payload = {"identifier": identifier, "timestamp": timestamp.isoformat(), "device_id": device_id}

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(self._url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise BadRequestError(
                "The face recognition service is unavailable", code="face_recognition_unavailable"
            ) from exc
        except ValueError as exc:  # invalid JSON
            raise BadRequestError(
                "The face recognition service returned an invalid response", code="face_recognition_invalid_response"
            ) from exc

        resolved = data.get("identifier") or data.get("employee_id")
        if not resolved:
            raise BadRequestError(
                "The face recognition service did not return an identifier",
                code="face_recognition_invalid_response",
            )
        confidence = data.get("confidence")
        return ResolvedIdentity(identifier=str(resolved), confidence=float(confidence) if confidence is not None else None)
