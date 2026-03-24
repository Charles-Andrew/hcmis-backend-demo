import anyio
from datetime import UTC, date, datetime, timedelta
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.app_log import AppLog
from app.services import logs as log_service


class FakeAppLogRepository:
    logs: dict[int, AppLog] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list_for_date(self, selected_date: date, user_id: int | None = None):
        logs = [
            log
            for log in self.logs.values()
            if log.created_at.date() == selected_date
            and (user_id is None or log.user_id == user_id)
        ]
        return sorted(logs, key=lambda item: item.id, reverse=True)

    async def create(self, log: AppLog):
        log.id = self.next_id
        self.next_id += 1
        log.created_at = log.created_at or utc_now()
        log.updated_at = log.updated_at or utc_now()
        self.logs[log.id] = log
        return log


async def _list_app_logs(selected_date: date, user_id: int | None = None):
    return await log_service.list_app_logs(
        session=cast(AsyncSession, object()),
        selected_date=selected_date,
        user_id=user_id,
    )


async def _create_app_log(user_id: int, details: str):
    return await log_service.create_app_log(
        session=cast(AsyncSession, object()),
        user_id=user_id,
        details=details,
    )


def setup_function():
    FakeAppLogRepository.logs = {}
    FakeAppLogRepository.next_id = 1


def _make_log(log_id: int, user_id: int, created_at: datetime):
    return AppLog(
        id=log_id,
        user_id=user_id,
        details=f"Log {log_id}",
        created_at=created_at,
        updated_at=created_at,
    )


def test_list_app_logs_filters_by_date_and_user(monkeypatch):
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)
    first = _make_log(1, 10, datetime.combine(today, datetime.min.time(), tzinfo=UTC))
    second = _make_log(2, 20, datetime.combine(today, datetime.min.time(), tzinfo=UTC))
    third = _make_log(3, 10, datetime.combine(yesterday, datetime.min.time(), tzinfo=UTC))
    FakeAppLogRepository.logs = {first.id: first, second.id: second, third.id: third}

    monkeypatch.setattr(log_service, "AppLogRepository", FakeAppLogRepository)

    response = anyio.run(_list_app_logs, today, 10)

    assert [log.id for log in response] == [1]


def test_create_app_log_returns_created_log(monkeypatch):
    monkeypatch.setattr(log_service, "AppLogRepository", FakeAppLogRepository)

    response = anyio.run(_create_app_log, 10, "Logged in.")

    assert response.id == 1
    assert response.user_id == 10
    assert response.details == "Logged in."
