from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DB, require_device_key
from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import now_utc
from app.models.enums import FaceEventOutcome, FaceEventRequestType
from app.schemas.attendance import AttendanceResponse
from app.schemas.employee import EmployeeBrief
from app.schemas.face_event import FaceEventRequest, FaceEventResponse
from app.services import attendance_service
from app.services.face_recognition.factory import get_provider

router = APIRouter(
    prefix="/face-recognition", tags=["face-recognition"], dependencies=[Depends(require_device_key)]
)


def _to_response(result: attendance_service.FaceEventResult) -> FaceEventResponse:
    return FaceEventResponse(
        outcome=result.outcome,
        message=result.message,
        face_event_id=result.face_event.id,
        employee=EmployeeBrief.model_validate(result.employee) if result.employee else None,
        attendance=AttendanceResponse.model_validate(result.attendance) if result.attendance else None,
    )


async def _handle(
    db: DB, payload: FaceEventRequest, requested_type: FaceEventRequestType, response: Response
) -> FaceEventResponse:
    provider = get_provider()
    resolved = await provider.resolve(
        identifier=payload.identifier,
        timestamp=payload.timestamp or now_utc(),
        device_id=payload.device_id,
    )
    result = await attendance_service.process_face_event(
        db,
        identifier=resolved.identifier,
        timestamp=payload.timestamp,
        requested_type=requested_type,
        device_id=payload.device_id,
        confidence=resolved.confidence if resolved.confidence is not None else payload.confidence,
    )

    if result.outcome == FaceEventOutcome.UNKNOWN_EMPLOYEE:
        raise NotFoundError(result.message, code="unknown_employee", details={"face_event_id": result.face_event.id})
    if result.outcome == FaceEventOutcome.REJECTED:
        raise ConflictError(result.message, code="face_event_rejected", details={"face_event_id": result.face_event.id})
    # 201 only when a new attendance row was actually created; a check-out update or a
    # benign duplicate (nothing created) is 200, regardless of which endpoint was called.
    response.status_code = status.HTTP_201_CREATED if result.outcome == FaceEventOutcome.CHECK_IN else status.HTTP_200_OK
    return _to_response(result)


@router.post("/event", response_model=FaceEventResponse)
async def face_event(payload: FaceEventRequest, db: DB, response: Response) -> FaceEventResponse:
    """The backend infers direction: no open record -> check-in, open record -> check-out."""
    return await _handle(db, payload, FaceEventRequestType.AUTO, response)


@router.post("/check-in", response_model=FaceEventResponse)
async def check_in(payload: FaceEventRequest, db: DB, response: Response) -> FaceEventResponse:
    """For installations with a dedicated entry camera/sensor."""
    return await _handle(db, payload, FaceEventRequestType.CHECK_IN, response)


@router.post("/check-out", response_model=FaceEventResponse)
async def check_out(payload: FaceEventRequest, db: DB, response: Response) -> FaceEventResponse:
    """For installations with a dedicated exit camera/sensor."""
    return await _handle(db, payload, FaceEventRequestType.CHECK_OUT, response)
