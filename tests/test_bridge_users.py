from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

import anyio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.routes import attendance as attendance_routes
from app.core.config import settings
from app.main import app
from app.models.user import User


class FakeUserRepository:
    users: list[User] = []

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, **_kwargs) -> list[User]:
        return self.users


def _make_user(
    user_id: UUID,
    first_name: str,
    last_name: str,
    biometric_uid: int | None,
    is_active: bool = True,
) -> User:
    return User(
        id=user_id,
        email=f"{first_name.lower()}@example.com",
        password_hash="hashed",
        first_name=first_name,
        last_name=last_name,
        biometric_uid=biometric_uid,
        can_modify_shift=False,
        is_active=is_active,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


async def _fake_db_session() -> AsyncGenerator[AsyncSession, None]:
    yield cast(AsyncSession, object())


async def _get_bridge_users(headers: dict[str, str]):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(
            "/attendance/bridge/users",
            params={"site_code": "MAIN", "device_id": "zk-main-1"},
            headers=headers,
        )


def test_bridge_users_requires_valid_agent_key(monkeypatch):
    monkeypatch.setattr(settings, "bridge_agent_key", "test-bridge-key")
    app.dependency_overrides[get_db_session] = _fake_db_session
    monkeypatch.setattr(attendance_routes, "UserRepository", FakeUserRepository)

    response = anyio.run(_get_bridge_users, {})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid bridge agent key."


def test_bridge_users_returns_biometric_mapped_users(monkeypatch):
    monkeypatch.setattr(settings, "bridge_agent_key", "test-bridge-key")
    app.dependency_overrides[get_db_session] = _fake_db_session
    monkeypatch.setattr(attendance_routes, "UserRepository", FakeUserRepository)
    FakeUserRepository.users = [
        _make_user(UUID(int=1), "Alice", "Anderson", biometric_uid=101, is_active=True),
        _make_user(UUID(int=2), "Bob", "Brown", biometric_uid=None, is_active=True),
        _make_user(UUID(int=3), "Cara", "Cole", biometric_uid=303, is_active=False),
    ]

    response = anyio.run(_get_bridge_users, {"X-Agent-Key": "test-bridge-key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "users": [
            {
                "user_id": str(UUID(int=1)),
                "biometric_uid": 101,
                "first_name": "Alice",
                "last_name": "Anderson",
                "is_active": True,
            },
            {
                "user_id": str(UUID(int=3)),
                "biometric_uid": 303,
                "first_name": "Cara",
                "last_name": "Cole",
                "is_active": False,
            },
        ]
    }
