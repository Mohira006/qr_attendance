import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.time import now_utc, today_local
from app.models.attendance import Attendance
from app.models.enums import CheckoutStatus
from app.services import leave_service, settings_service
from app.services.working_hours import WorkingHours, expected_end

logger = logging.getLogger(__name__)

# How long after a shift's expected end an employee is still assumed to just be
# running late leaving, before HR is asked to follow up manually. No checkout
# time is ever invented - the record is simply flagged for review.
MISSING_CHECKOUT_GRACE = timedelta(hours=4)

_scheduler: AsyncIOScheduler | None = None


async def mark_missing_checkouts(db: AsyncSession) -> int:
    now = now_utc()
    # Rows from today can still be legitimately open; only rows from earlier days
    # are worth evaluating; expected shifts don't have any use in comparing today's
    # rows against a cutoff that, for any realistic grace period, is always in the future.
    candidates = (
        await db.execute(
            select(Attendance).where(Attendance.checkout_status == CheckoutStatus.PENDING, Attendance.date < today_local())
        )
    ).scalars().all()

    marked = 0
    for record in candidates:
        hours = WorkingHours(start=record.expected_check_in, end=record.expected_check_out, grace_minutes=0)
        cutoff = expected_end(record.date, hours) + MISSING_CHECKOUT_GRACE
        if now > cutoff:
            record.checkout_status = CheckoutStatus.MISSING
            marked += 1

    if marked:
        await db.commit()
        logger.info("Marked %d attendance record(s) as missing checkout", marked)
    return marked


async def _run_missing_checkout_job() -> None:
    async with SessionLocal() as db:
        try:
            await mark_missing_checkouts(db)
        except Exception:  # noqa: BLE001 - a failed background run must not crash the scheduler thread
            logger.exception("Missing-checkout job failed")


async def _run_leave_completion_job() -> None:
    async with SessionLocal() as db:
        try:
            count = await leave_service.mark_completed_requests(db)
            if count:
                logger.info("Marked %d leave request(s) as completed", count)
        except Exception:  # noqa: BLE001
            logger.exception("Leave completion job failed")


async def _run_leave_reminder_job() -> None:
    async with SessionLocal() as db:
        try:
            settings = await settings_service.get_or_create(db)
            count = await leave_service.send_eligibility_reminders(db, settings)
            if count:
                logger.info("Sent %d leave eligibility reminder(s)", count)
        except Exception:  # noqa: BLE001
            logger.exception("Leave reminder job failed")


def start() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_missing_checkout_job,
        trigger="interval",
        minutes=30,
        id="missing_checkout_check",
        next_run_time=now_utc(),  # also run once immediately, so a freshly started server catches up
        max_instances=1,
        coalesce=True,
    )
    # Leave state is date-based, not time-sensitive - daily is plenty, unlike the
    # 30-minute attendance job above.
    _scheduler.add_job(
        _run_leave_completion_job,
        trigger="interval",
        hours=24,
        id="leave_completion_check",
        next_run_time=now_utc(),
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _run_leave_reminder_job,
        trigger="interval",
        hours=24,
        id="leave_reminder_check",
        next_run_time=now_utc(),
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started: missing-checkout (30m), leave completion + reminders (24h)")
    return _scheduler


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
