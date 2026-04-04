from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import cast

import anyio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.routes import attendance as attendance_routes
from app.core.config import settings
from app.main import app


async def _fake_db_session() -> AsyncGenerator[AsyncSession, None]:
    yield cast(AsyncSession, object())


async def _post_bridge_logs(payload: dict, headers: dict[str, str]):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/attendance/bridge/logs",
            json=payload,
            headers=headers,
        )


async def _post_device_cdata(params: dict[str, str]):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/attendance/device/cdata",
            params=params,
        )


def test_bridge_logs_normalizes_naive_timestamp_using_configured_timezone(monkeypatch):
    captured: list[datetime] = []

    async def fake_sync(
        session, *, device_user_id, timestamp, punch, raw_event_id=None
    ):  # noqa: ANN001
        _ = session, device_user_id, punch, raw_event_id
        captured.append(timestamp)
        return cast(object, None)

    monkeypatch.setattr(attendance_routes, "sync_device_attendance", fake_sync)
    monkeypatch.setattr(settings, "bridge_agent_key", "test-bridge-key")
    monkeypatch.setattr(settings, "bridge_device_timezone", "Asia/Manila")
    app.dependency_overrides[get_db_session] = _fake_db_session

    response = anyio.run(
        _post_bridge_logs,
        {
            "site_code": "MAIN",
            "device_id": "zk-main-1",
            "events": [
                {
                    "device_user_id": "101",
                    "timestamp": "2026-04-04T08:00:00",
                    "status": 0,
                    "punch": 0,
                }
            ],
        },
        {"X-Agent-Key": "test-bridge-key"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert captured == [datetime(2026, 4, 4, 0, 0, tzinfo=UTC)]


def test_bridge_logs_normalizes_aware_timestamp_to_utc(monkeypatch):
    captured: list[datetime] = []

    async def fake_sync(
        session, *, device_user_id, timestamp, punch, raw_event_id=None
    ):  # noqa: ANN001
        _ = session, device_user_id, punch, raw_event_id
        captured.append(timestamp)
        return cast(object, None)

    monkeypatch.setattr(attendance_routes, "sync_device_attendance", fake_sync)
    monkeypatch.setattr(settings, "bridge_agent_key", "test-bridge-key")
    monkeypatch.setattr(settings, "bridge_device_timezone", "Asia/Manila")
    app.dependency_overrides[get_db_session] = _fake_db_session

    response = anyio.run(
        _post_bridge_logs,
        {
            "site_code": "MAIN",
            "device_id": "zk-main-1",
            "events": [
                {
                    "device_user_id": "101",
                    "timestamp": "2026-04-04T08:00:00+08:00",
                    "status": 0,
                    "punch": 0,
                }
            ],
        },
        {"X-Agent-Key": "test-bridge-key"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert captured == [datetime(2026, 4, 4, 0, 0, tzinfo=UTC)]


def test_device_cdata_normalizes_naive_timestamp_using_configured_timezone(monkeypatch):
    captured: list[datetime] = []

    async def fake_sync(
        session, device_user_id, timestamp, punch, raw_event_id=None
    ):  # noqa: ANN001
        _ = session, device_user_id, punch, raw_event_id
        captured.append(timestamp)
        return cast(object, None)

    monkeypatch.setattr(attendance_routes, "sync_device_attendance", fake_sync)
    monkeypatch.setattr(settings, "bridge_device_timezone", "Asia/Manila")
    app.dependency_overrides[get_db_session] = _fake_db_session

    response = anyio.run(
        _post_device_cdata,
        {
            "device_user_id": "101",
            "timestamp": "2026-04-04T08:00:00",
            "punch": "IN",
        },
    )

    assert response.status_code == 200
    assert response.text == "OK"
    assert captured == [datetime(2026, 4, 4, 0, 0, tzinfo=UTC)]
