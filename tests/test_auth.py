import anyio
from typing import cast

from app.api.routes import auth as auth_routes
from app.core.security import decode_access_token
from app.core.time import utc_now
from app.models.user import User
from app.schemas.auth import AuthLoginRequest, AuthRegisterRequest
from app.schemas.auth import AuthResponse
from app.schemas.user import UserRead
from sqlalchemy.ext.asyncio import AsyncSession


class FakeUserRepository:
    users_by_email: dict[str, User] = {}
    users_by_id: dict[int, User] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def get_by_email(self, email: str):
        return self.users_by_email.get(email)

    async def get_by_id(self, user_id: int):
        return self.users_by_id.get(user_id)

    async def create(self, user: User):
        user.id = self.next_id
        self.next_id += 1
        user.created_at = user.created_at or utc_now()
        user.updated_at = user.updated_at or utc_now()
        self.users_by_email[user.email] = user
        self.users_by_id[user.id] = user
        return user


async def _register(payload: dict[str, str]) -> UserRead:
    return await auth_routes.register(
        AuthRegisterRequest(**payload),
        session=cast(AsyncSession, object()),
    )


async def _login(payload: dict[str, str]) -> AuthResponse:
    return await auth_routes.login(
        AuthLoginRequest(**payload),
        session=cast(AsyncSession, object()),
    )


async def _me(user: User) -> UserRead:
    return await auth_routes.me(current_user=user)


def test_register_returns_created_user(monkeypatch):
    FakeUserRepository.users_by_email = {}
    FakeUserRepository.users_by_id = {}
    FakeUserRepository.next_id = 1

    monkeypatch.setattr(auth_routes, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(auth_routes, "hash_password", lambda password: "hashed")

    payload = {
        "email": "new.user@example.com",
        "password": "supersecret1",
        "first_name": "New",
        "last_name": "User",
        "employee_number": "EMP-001",
        "role": "EMP",
    }

    response = anyio.run(_register, payload)

    assert response.email == payload["email"]
    assert response.employee_number == payload["employee_number"]
    assert response.role == payload["role"]


def test_login_returns_token_and_user(monkeypatch):
    user = User(
        id=7,
        email="jane.doe@example.com",
        password_hash="hashed",
        first_name="Jane",
        last_name="Doe",
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    FakeUserRepository.users_by_email = {user.email: user}
    FakeUserRepository.users_by_id = {user.id: user}
    FakeUserRepository.next_id = 8

    monkeypatch.setattr(auth_routes, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda password, password_hash: password == "secret-password",
    )

    response = anyio.run(
        _login,
        {"email": user.email, "password": "secret-password"},
    )

    assert response.token_type == "bearer"
    assert response.user.email == user.email
    assert decode_access_token(response.access_token)["sub"] == "7"


def test_me_returns_current_user():
    user = User(
        id=11,
        email="current.user@example.com",
        password_hash="hashed",
        first_name="Current",
        last_name="User",
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    response = anyio.run(_me, user)

    assert response.email == user.email
