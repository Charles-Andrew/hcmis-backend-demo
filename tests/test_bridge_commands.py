from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import cast

import anyio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.routes import attendance as attendance_routes
from app.core.config import settings
from app.main import app
from app.schemas.attendance import BridgeCommandRead


async def _fake_db_session() -> AsyncGenerator[AsyncSession, None]:
    yield cast(AsyncSession, object())


async def _get_commands(headers: dict[str, str]):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(
            "/attendance/bridge/commands",
            params={"site_code": "MAIN", "device_id": "zk-main-1", "limit": 10},
            headers=headers,
        )


async def _post_ack(headers: dict[str, str]):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/attendance/bridge/commands/42/ack",
            json={"status": "done", "message": "ok"},
            headers=headers,
        )


def test_bridge_command_poll_requires_agent_key(monkeypatch):
    monkeypatch.setattr(settings, "bridge_agent_key", "test-bridge-key")
    app.dependency_overrides[get_db_session] = _fake_db_session

    response = anyio.run(_get_commands, {})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid bridge agent key."


def test_bridge_command_ack_with_agent_key(monkeypatch):
    async def fake_ack(session, *, command_id, payload):  # noqa: ANN001
        _ = session
        assert command_id == 42
        assert payload.status == "done"
        return BridgeCommandRead(
            command_id=42,
            site_code="MAIN",
            device_id="zk-main-1",
            type="sync_users",
            payload={},
            status="done",
            message="ok",
            created_at=datetime.now(timezone.utc),
            dispatched_at=datetime.now(timezone.utc),
            executed_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(attendance_routes, "ack_command", fake_ack)
    monkeypatch.setattr(settings, "bridge_agent_key", "test-bridge-key")
    app.dependency_overrides[get_db_session] = _fake_db_session

    response = anyio.run(_post_ack, {"X-Agent-Key": "test-bridge-key"})

    assert response.status_code == 200
    assert response.json()["status"] == "done"
