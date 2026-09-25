from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def company_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().COMPANY_TIMEZONE)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return now_utc().astimezone(company_tz())


def today_local() -> date:
    return now_local().date()


def to_utc(value: datetime) -> datetime:
    """Naive datetimes are assumed to be in the company timezone (this is what Face ID devices send)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=company_tz())
    return value.astimezone(timezone.utc)


def to_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(company_tz())


def local_date(value: datetime) -> date:
    return to_local(value).date()


def combine_local(day: date, at: time) -> datetime:
    """Build an aware UTC datetime from a local calendar date and local wall-clock time."""
    return datetime.combine(day, at, tzinfo=company_tz()).astimezone(timezone.utc)


def truncate_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def format_local_time(value: datetime | None) -> str | None:
    if value is None:
        return None
    return to_local(value).strftime("%H:%M")
