import anyio
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.models.department import Department
from app.schemas.department import DepartmentCreateRequest, DepartmentUpdateRequest
from app.services import departments as department_service


class FakeDepartmentRepository:
    departments: dict[int, Department] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self):
        return sorted(self.departments.values(), key=lambda department: department.name)

    async def get_by_id(self, department_id: int):
        return self.departments.get(department_id)

    async def get_by_name(self, name: str):
        lowered = name.lower()
        for department in self.departments.values():
            if department.name.lower() == lowered:
                return department
        return None

    async def get_by_code(self, code: str):
        lowered = code.lower()
        for department in self.departments.values():
            if department.code.lower() == lowered:
                return department
        return None

    async def create(self, department: Department):
        department.id = self.next_id
        self.next_id += 1
        department.created_at = department.created_at or utc_now()
        department.updated_at = department.updated_at or utc_now()
        self.departments[department.id] = department
        return department

    async def save(self, department: Department):
        department.updated_at = utc_now()
        self.departments[department.id] = department
        return department

    async def delete(self, department: Department):
        self.departments.pop(department.id, None)


async def _create_department(name: str, code: str, is_active: bool):
    return await department_service.create_department(
        session=cast(AsyncSession, object()),
        payload=DepartmentCreateRequest(name=name, code=code, is_active=is_active),
    )


async def _update_department(
    department_id: int,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
):
    return await department_service.update_department(
        session=cast(AsyncSession, object()),
        department_id=department_id,
        payload=DepartmentUpdateRequest(name=name, code=code, is_active=is_active),
    )


async def _delete_department(department_id: int):
    return await department_service.delete_department(
        session=cast(AsyncSession, object()),
        department_id=department_id,
    )


async def _list_departments():
    return await department_service.list_departments(session=cast(AsyncSession, object()))


def setup_function():
    FakeDepartmentRepository.departments = {}
    FakeDepartmentRepository.next_id = 1


def test_list_departments_returns_ordered_departments(monkeypatch):
    first = Department(name="Finance", code="FIN", is_active=True)
    second = Department(name="Accounting", code="ACC", is_active=True)
    first.id = 1
    second.id = 2
    FakeDepartmentRepository.departments = {first.id: first, second.id: second}

    monkeypatch.setattr(department_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(_list_departments)

    assert [department.name for department in response] == ["Accounting", "Finance"]


def test_create_department_persists_department(monkeypatch):
    monkeypatch.setattr(department_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(
        _create_department,
        "Human Resources",
        "HR",
        True,
    )

    assert response.id == 1
    assert response.name == "Human Resources"
    assert response.code == "HR"


def test_create_department_rejects_duplicate_name(monkeypatch):
    existing = Department(name="Human Resources", code="HR", is_active=True)
    existing.id = 1
    FakeDepartmentRepository.departments = {1: existing}
    monkeypatch.setattr(department_service, "DepartmentRepository", FakeDepartmentRepository)

    try:
        anyio.run(
            _create_department,
            "Human Resources",
            "OPS",
            True,
        )
    except ConflictError as exc:
        assert "Department name already exists." in exc.detail
    else:
        raise AssertionError("Expected ConflictError to be raised")


def test_update_department_changes_fields(monkeypatch):
    existing = Department(name="Human Resources", code="HR", is_active=True)
    existing.id = 1
    FakeDepartmentRepository.departments = {1: existing}
    monkeypatch.setattr(department_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(
        _update_department,
        1,
        "People Ops",
        "PPL",
        False,
    )

    assert response.name == "People Ops"
    assert response.code == "PPL"
    assert response.is_active is False


def test_delete_department_returns_name(monkeypatch):
    existing = Department(name="Human Resources", code="HR", is_active=True)
    existing.id = 1
    FakeDepartmentRepository.departments = {1: existing}
    monkeypatch.setattr(department_service, "DepartmentRepository", FakeDepartmentRepository)

    response = anyio.run(_delete_department, 1)

    assert response == "Human Resources"


def test_update_department_missing_department_raises(monkeypatch):
    monkeypatch.setattr(department_service, "DepartmentRepository", FakeDepartmentRepository)

    try:
        anyio.run(_update_department, 999, "New")
    except NotFoundError as exc:
        assert exc.detail == "Department not found."
    else:
        raise AssertionError("Expected NotFoundError to be raised")
