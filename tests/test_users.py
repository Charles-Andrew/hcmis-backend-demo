import anyio
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.models.department import Department
from app.models.user import User
from app.schemas.user import UserBiometricUpdateRequest
from app.schemas.user import UserUpdateRequest
from app.services import users as user_service


class FakeDepartmentRepository:
    departments: dict[int, Department] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, department_id: int):
        return self.departments.get(department_id)


class FakeUserRepository:
    users: dict[int, User] = {}

    def __init__(self, session):
        self.session = session

    async def list(
        self,
        query=None,
        department_id=None,
        active_only=None,
        include_superusers=False,
        exclude_hr=False,
        exclude_user_id=None,
    ):
        users = list(self.users.values())
        if not include_superusers:
            users = [user for user in users if not user.is_superuser]
        if exclude_hr:
            users = [
                user
                for user in users
                if (user.role or "").strip().upper() != "HR"
                and (getattr(user.department, "code", "") or "").strip().upper()
                != "HR"
                and (getattr(user.department, "name", "") or "").strip().upper()
                != "HR"
            ]
        if exclude_user_id is not None:
            users = [user for user in users if user.id != exclude_user_id]
        if department_id is not None:
            users = [user for user in users if user.department_id == department_id]
        if active_only is True:
            users = [user for user in users if user.is_active]
        if query:
            lowered = query.lower()
            users = [
                user
                for user in users
                if lowered in user.first_name.lower()
                or lowered in user.last_name.lower()
                or lowered in user.email.lower()
                or (user.employee_number and lowered in user.employee_number.lower())
            ]
        return sorted(
            users,
            key=lambda user: (
                user.department.name if getattr(user, "department", None) else "",
                user.first_name,
                user.last_name,
            ),
        )

    async def get_by_id(self, user_id: int):
        return self.users.get(user_id)

    async def save(self, user: User):
        user.updated_at = utc_now()
        self.users[user.id] = user
        return user


async def _list_users(
    query: str | None = None,
    department_id: int | None = None,
    active_only: bool | None = None,
    exclude_hr: bool = False,
    exclude_user_id: int | None = None,
):
    return await user_service.list_users(
        session=cast(AsyncSession, object()),
        query=query,
        department_id=department_id,
        active_only=active_only,
        exclude_hr=exclude_hr,
        exclude_user_id=exclude_user_id,
    )


async def _update_user(user_id: int, payload: UserUpdateRequest):
    return await user_service.update_user(
        session=cast(AsyncSession, object()),
        user_id=user_id,
        payload=payload,
    )


async def _toggle_user(user_id: int):
    return await user_service.toggle_user_status(
        session=cast(AsyncSession, object()),
        user_id=user_id,
    )


async def _update_biometric(user_id: int, payload: UserBiometricUpdateRequest):
    return await user_service.update_user_biometric_uid(
        session=cast(AsyncSession, object()),
        user_id=user_id,
        payload=payload,
    )


def setup_function():
    FakeDepartmentRepository.departments = {}
    FakeUserRepository.users = {}


def _make_department(department_id: int, name: str):
    department = Department(name=name, code=name[:3].upper(), is_active=True)
    department.id = department_id
    return department


def _make_user(
    user_id: int,
    first_name: str,
    last_name: str,
    email: str,
    department: Department | None = None,
    department_id: int | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
):
    user = User(
        id=user_id,
        email=email,
        password_hash="hashed",
        first_name=first_name,
        last_name=last_name,
        can_modify_shift=False,
        department_id=department_id,
        is_active=is_active,
        is_superuser=is_superuser,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    user.department = department
    return user


def test_list_users_filters_and_orders(monkeypatch):
    accounting = _make_department(1, "Accounting")
    hr = _make_department(2, "Human Resources")

    first = _make_user(1, "Alice", "A", "alice@example.com", accounting, 1)
    second = _make_user(2, "Charlie", "C", "charlie@example.com", accounting, 1)
    third = _make_user(3, "Bob", "B", "bob@example.com", hr, 2)
    superuser = _make_user(4, "Admin", "User", "admin@example.com", hr, 2, is_superuser=True)

    FakeUserRepository.users = {
        first.id: first,
        second.id: second,
        third.id: third,
        superuser.id: superuser,
    }

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)

    response = anyio.run(_list_users)

    assert [user.first_name for user in response] == ["Alice", "Charlie", "Bob"]


def test_list_users_can_exclude_hr_users(monkeypatch):
    accounting = _make_department(1, "Accounting")
    hr = _make_department(2, "Human Resources")

    emp = _make_user(1, "Alice", "A", "alice@example.com", accounting, 1)
    hr_role = _make_user(2, "Bob", "B", "bob@example.com", accounting, 1)
    hr_role.role = "HR"
    hr_department = _make_user(3, "Cara", "C", "cara@example.com", hr, 2)

    FakeUserRepository.users = {
        emp.id: emp,
        hr_role.id: hr_role,
        hr_department.id: hr_department,
    }

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)

    response = anyio.run(_list_users, None, None, None, True)

    assert [user.email for user in response] == [
        "alice@example.com",
        "cara@example.com",
    ]


def test_list_users_supports_query_and_department_filters(monkeypatch):
    accounting = _make_department(1, "Accounting")
    hr = _make_department(2, "Human Resources")
    alice = _make_user(1, "Alice", "A", "alice@example.com", accounting, 1)
    bob = _make_user(2, "Bob", "B", "bob@example.com", hr, 2)

    FakeUserRepository.users = {alice.id: alice, bob.id: bob}
    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)

    response = anyio.run(
        _list_users,
        "bo",
        2,
        True,
    )

    assert [user.email for user in response] == ["bob@example.com"]


def test_list_users_can_exclude_a_specific_user(monkeypatch):
    accounting = _make_department(1, "Accounting")
    alice = _make_user(1, "Alice", "A", "alice@example.com", accounting, 1)
    bob = _make_user(2, "Bob", "B", "bob@example.com", accounting, 1)

    FakeUserRepository.users = {alice.id: alice, bob.id: bob}
    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)

    response = anyio.run(_list_users, None, None, None, False, 2)

    assert [user.id for user in response] == [1]


def test_update_user_changes_department_and_status(monkeypatch):
    accounting = _make_department(1, "Accounting")
    hr = _make_department(2, "Human Resources")
    FakeDepartmentRepository.departments = {1: accounting, 2: hr}

    user = _make_user(1, "Alice", "A", "alice@example.com", accounting, 1)
    FakeUserRepository.users = {user.id: user}

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(user_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(
        _update_user,
        1,
        UserUpdateRequest(first_name="Alicia", department_id=2, is_active=False),
    )

    assert response.first_name == "Alicia"
    assert response.department_id == 2
    assert response.is_active is False


def test_update_user_missing_department_raises(monkeypatch):
    user = _make_user(1, "Alice", "A", "alice@example.com", None, None)
    FakeUserRepository.users = {user.id: user}

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(user_service, "DepartmentRepository", FakeDepartmentRepository)

    try:
        anyio.run(_update_user, 1, UserUpdateRequest(department_id=999))
    except NotFoundError as exc:
        assert exc.detail == "Department not found."
    else:
        raise AssertionError("Expected NotFoundError to be raised")


def test_toggle_user_status_flips_active_flag(monkeypatch):
    user = _make_user(1, "Alice", "A", "alice@example.com", None, None, is_active=True)
    FakeUserRepository.users = {user.id: user}

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(user_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(_toggle_user, 1)

    assert response.is_active is False


def test_update_user_biometric_uid(monkeypatch):
    user = _make_user(1, "Alice", "A", "alice@example.com", None, None)
    FakeUserRepository.users = {user.id: user}

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(user_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(
        _update_biometric,
        1,
        UserBiometricUpdateRequest(biometric_uid=99),
    )

    assert response.biometric_uid == 99


def test_update_user_biometric_uid_rejects_duplicates(monkeypatch):
    first = _make_user(1, "Alice", "A", "alice@example.com", None, None)
    second = _make_user(2, "Bob", "B", "bob@example.com", None, None)
    first.biometric_uid = 99
    FakeUserRepository.users = {1: first, 2: second}

    monkeypatch.setattr(user_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(user_service, "DepartmentRepository", FakeDepartmentRepository)

    try:
        anyio.run(_update_biometric, 2, UserBiometricUpdateRequest(biometric_uid=99))
    except NotFoundError as exc:
        assert exc.detail == "Biometric UID is already assigned to another user."
    else:
        raise AssertionError("Expected NotFoundError to be raised")
