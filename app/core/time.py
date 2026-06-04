from calendar import monthrange
from datetime import UTC, date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings


def utc_now() -> datetime:
    return datetime.now(UTC)


@lru_cache
def app_timezone() -> ZoneInfo:
    timezone_name = settings.app_timezone.strip() or "Asia/Manila"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Invalid APP_TIMEZONE: {timezone_name}") from exc


def local_now() -> datetime:
    return utc_now().astimezone(app_timezone())


def local_today() -> date:
    return local_now().date()


def ensure_utc(value: datetime, *, default_timezone: ZoneInfo | None = None) -> datetime:
    timezone = default_timezone or app_timezone()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone).astimezone(UTC)
    return value.astimezone(UTC)


def to_local(value: datetime) -> datetime:
    return ensure_utc(value).astimezone(app_timezone())


def combine_local(selected_date: date, selected_time: time) -> datetime:
    return datetime.combine(selected_date, selected_time, tzinfo=app_timezone())


def day_bounds_utc(selected_date: date) -> tuple[datetime, datetime]:
    start_local = combine_local(selected_date, time.min)
    end_local = combine_local(selected_date, time.max)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def month_bounds_utc(year: int, month: int) -> tuple[datetime, datetime]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return day_bounds_utc(start)[0], day_bounds_utc(end)[1]
