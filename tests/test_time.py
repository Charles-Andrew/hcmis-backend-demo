from datetime import UTC, date, datetime

from app.core import time as time_utils


def test_local_today_uses_manila_date(monkeypatch):
    monkeypatch.setattr(
        time_utils,
        "utc_now",
        lambda: datetime(2026, 6, 4, 18, 30, tzinfo=UTC),
    )

    assert time_utils.local_today() == date(2026, 6, 5)


def test_day_bounds_utc_uses_manila_midnight():
    start, end = time_utils.day_bounds_utc(date(2026, 6, 5))

    assert start == datetime(2026, 6, 4, 16, 0, tzinfo=UTC)
    assert end == datetime(2026, 6, 5, 15, 59, 59, 999999, tzinfo=UTC)


def test_ensure_utc_assumes_manila_for_naive_values():
    normalized = time_utils.ensure_utc(datetime(2026, 6, 5, 8, 45))

    assert normalized == datetime(2026, 6, 5, 0, 45, tzinfo=UTC)
