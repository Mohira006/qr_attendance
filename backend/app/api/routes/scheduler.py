from fastapi import APIRouter

from app.api.deps import DB, HRUser
from app.schemas.common import Message
from app.services import scheduler as scheduler_service

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/run-missing-checkout-check", response_model=Message)
async def run_missing_checkout_check(db: DB, _: HRUser) -> Message:
    """Runs the end-of-day missing-checkout sweep immediately instead of waiting
    for its normal interval. Useful for ops follow-up and for testing."""
    count = await scheduler_service.mark_missing_checkouts(db)
    return Message(message=f"Marked {count} attendance record(s) as missing checkout")
