import anyio
import pytest
from datetime import date
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.department import Department
from app.models.leave import LeaveApprover, LeaveCredit, LeaveRequest, LeaveRequestStatus
from app.models.user import User
from app.schemas.leave import (
    LeaveApproverUpsertRequest,
    LeaveCreditUpsertRequest,
    LeaveRequestCreateRequest,
    LeaveRequestReviewRequest,
)
from app.services import leave as leave_service


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

    async def get_by_id(self, user_id: int):
        return self.users.get(user_id)


class FakeLeaveApproverRepository:
    leave_approvers: dict[int, LeaveApprover] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self):
        return list(self.leave_approvers.values())

    async def get_by_department_id(self, department_id: int):
        return self.leave_approvers.get(department_id)

    async def create(self, leave_approver: LeaveApprover):
        leave_approver.id = self.next_id
        self.next_id += 1
        self.leave_approvers[leave_approver.department_id] = leave_approver
        return leave_approver

    async def save(self, leave_approver: LeaveApprover):
        self.leave_approvers[leave_approver.department_id] = leave_approver
        return leave_approver

    async def delete(self, leave_approver: LeaveApprover):
        self.leave_approvers.pop(leave_approver.department_id, None)


class FakeLeaveCreditRepository:
    leave_credits: dict[int, LeaveCredit] = {}

    def __init__(self, session):
        self.session = session

    async def list(self):
        return list(self.leave_credits.values())

    async def get_by_user_id(self, user_id: int):
        return self.leave_credits.get(user_id)

    async def create(self, leave_credit: LeaveCredit):
        self.leave_credits[leave_credit.user_id] = leave_credit
        return leave_credit

    async def save(self, leave_credit: LeaveCredit):
        self.leave_credits[leave_credit.user_id] = leave_credit
        return leave_credit


class FakeLeaveRequestRepository:
    leave_requests: dict[int, LeaveRequest] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(
        self,
        user_id: int | None = None,
        department_id: int | None = None,
        approver_id: int | None = None,
        status: str | None = None,
        year: int | None = None,
        month: int | None = None,
    ):
        requests = list(self.leave_requests.values())
        if user_id is not None:
            requests = [item for item in requests if item.user_id == user_id]
        if approver_id is not None:
            requests = [
                item
                for item in requests
                if item.first_approver_id == approver_id
                or item.second_approver_id == approver_id
            ]
        if status is not None:
            requests = [item for item in requests if item.status == status]
        if year is not None:
            requests = [item for item in requests if item.leave_date.year == year]
        if month is not None:
            requests = [item for item in requests if item.leave_date.month == month]
        if department_id is not None:
            requests = [
                item
                for item in requests
                if FakeUserRepository.users[item.user_id].department_id == department_id
            ]
        return sorted(requests, key=lambda item: (item.leave_date, item.created_at), reverse=True)

    async def list_years(self):
        return sorted({item.leave_date.year for item in self.leave_requests.values()})

    async def get_by_id(self, leave_id: int):
        return self.leave_requests.get(leave_id)

    async def create(self, leave_request: LeaveRequest):
        leave_request.id = self.next_id
        self.next_id += 1
        leave_request.created_at = leave_request.created_at or utc_now()
        leave_request.updated_at = leave_request.updated_at or utc_now()
        self.leave_requests[leave_request.id] = leave_request
        return leave_request

    async def save(self, leave_request: LeaveRequest):
        leave_request.updated_at = utc_now()
        self.leave_requests[leave_request.id] = leave_request
        return leave_request

    async def delete(self, leave_request: LeaveRequest):
        self.leave_requests.pop(leave_request.id, None)


async def _create_leave(payload: dict) -> LeaveRequest:
    employee = FakeUserRepository.users[1]
    return await leave_service.create_leave_request(
        cast(AsyncSession, object()),
        employee,
        LeaveRequestCreateRequest(**payload),
    )


async def _review_leave(
    leave_id: int, user: User, response: Literal["APPROVE", "REJECT"]
) -> LeaveRequest:
    return await leave_service.review_leave_request(
        cast(AsyncSession, object()),
        leave_id,
        user,
        LeaveRequestReviewRequest(response=response),
    )


def _reset_fakes():
    FakeDepartmentRepository.departments = {}
    FakeUserRepository.users = {}
    FakeLeaveApproverRepository.leave_approvers = {}
    FakeLeaveApproverRepository.next_id = 1
    FakeLeaveCreditRepository.leave_credits = {}
    FakeLeaveRequestRepository.leave_requests = {}
    FakeLeaveRequestRepository.next_id = 1


def _seed_users_and_department():
    department = Department(
        id=1, name="Operations", code="OPS", is_active=True, workweek=[]
    )
    FakeDepartmentRepository.departments[department.id] = department

    employee = User(
        id=1,
        email="employee@example.com",
        password_hash="hashed",
        first_name="Emp",
        last_name="One",
        role="EMP",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    dept_head = User(
        id=2,
        email="dept.head@example.com",
        password_hash="hashed",
        first_name="Dept",
        last_name="Head",
        role="DH",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    hr_user = User(
        id=3,
        email="hr@example.com",
        password_hash="hashed",
        first_name="Human",
        last_name="Resource",
        role="HR",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    director = User(
        id=4,
        email="director@example.com",
        password_hash="hashed",
        first_name="Dir",
        last_name="Ector",
        role="DIR",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    president = User(
        id=5,
        email="president@example.com",
        password_hash="hashed",
        first_name="Pre",
        last_name="Sident",
        role="PRES",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    for user in [employee, dept_head, hr_user, director, president]:
        FakeUserRepository.users[user.id] = user

    approver = LeaveApprover(
        id=1,
        department_id=department.id,
        department_approver_id=dept_head.id,
        director_approver_id=director.id,
        president_approver_id=president.id,
        hr_approver_id=hr_user.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    FakeLeaveApproverRepository.leave_approvers[department.id] = approver

    credit = LeaveCredit(
        user_id=employee.id,
        credits=10,
        used_credits=0,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    FakeLeaveCreditRepository.leave_credits[employee.id] = credit


def test_leave_request_creation_uses_department_chain(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 1), "leave_type": "PA", "info": "Family matter"},
    )

    assert leave_request.first_approver_id == 2
    assert leave_request.second_approver_id == 3
    assert leave_request.status == LeaveRequestStatus.PENDING.value


def test_leave_request_review_approves_in_two_steps_and_consumes_credit(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 1), "leave_type": "PA", "info": "Annual leave"},
    )

    first_review = anyio.run(
        _review_leave, leave_request.id, FakeUserRepository.users[2], "APPROVE"
    )
    assert first_review.first_approver_status == LeaveRequestStatus.APPROVED.value
    assert first_review.status == LeaveRequestStatus.PENDING.value
    assert FakeLeaveCreditRepository.leave_credits[1].used_credits == 0

    final_review = anyio.run(
        _review_leave, leave_request.id, FakeUserRepository.users[3], "APPROVE"
    )
    assert final_review.second_approver_status == LeaveRequestStatus.APPROVED.value
    assert final_review.status == LeaveRequestStatus.APPROVED.value
    assert FakeLeaveCreditRepository.leave_credits[1].used_credits == 1


def test_leave_request_rejection_does_not_consume_credit(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 2), "leave_type": "PA", "info": "Another leave"},
    )

    rejected = anyio.run(
        _review_leave, leave_request.id, FakeUserRepository.users[2], "REJECT"
    )
    assert rejected.status == LeaveRequestStatus.REJECTED.value
    assert FakeLeaveCreditRepository.leave_credits[1].used_credits == 0


def test_leave_request_deletion_reduces_used_credit_when_approved(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 3), "leave_type": "PA", "info": "Vacation"},
    )
    anyio.run(_review_leave, leave_request.id, FakeUserRepository.users[2], "APPROVE")
    anyio.run(_review_leave, leave_request.id, FakeUserRepository.users[3], "APPROVE")
    assert FakeLeaveCreditRepository.leave_credits[1].used_credits == 1

    anyio.run(
        leave_service.delete_leave_request,
        cast(AsyncSession, object()),
        leave_request.id,
        FakeUserRepository.users[1],
    )
    assert FakeLeaveCreditRepository.leave_credits[1].used_credits == 0


def test_leave_credit_management_and_approver_settings(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    approver = anyio.run(
        leave_service.upsert_leave_approver,
        cast(AsyncSession, object()),
        1,
        LeaveApproverUpsertRequest(
            department_approver_id=2,
            director_approver_id=4,
            president_approver_id=5,
            hr_approver_id=3,
        ),
    )
    assert approver.department_approver_id == 2

    credit = anyio.run(
        leave_service.set_leave_credit,
        cast(AsyncSession, object()),
        1,
        LeaveCreditUpsertRequest(credits=15),
    )
    assert credit.credits == 15

    reset_credit = anyio.run(
        leave_service.reset_leave_credit,
        cast(AsyncSession, object()),
        1,
    )
    assert reset_credit.used_credits == 0

    credits = anyio.run(
        leave_service.list_leave_credits,
        cast(AsyncSession, object()),
    )
    assert credits[0].remaining_credits == 15


def test_paid_leave_request_requires_available_credit(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()
    FakeLeaveCreditRepository.leave_credits[1].credits = 1
    FakeLeaveCreditRepository.leave_credits[1].used_credits = 1

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    with pytest.raises(leave_service.ConflictError):
        anyio.run(
            _create_leave,
            {"leave_date": date(2026, 4, 6), "leave_type": "PA", "info": "Out of credits"},
        )


def test_paid_leave_final_approval_fails_when_credit_depleted(monkeypatch):
    _reset_fakes()
    _seed_users_and_department()

    monkeypatch.setattr(leave_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveApproverRepository", FakeLeaveApproverRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 8), "leave_type": "PA", "info": "Annual leave"},
    )
    anyio.run(_review_leave, leave_request.id, FakeUserRepository.users[2], "APPROVE")
    FakeLeaveCreditRepository.leave_credits[1].credits = 1
    FakeLeaveCreditRepository.leave_credits[1].used_credits = 1

    with pytest.raises(leave_service.ConflictError):
        anyio.run(_review_leave, leave_request.id, FakeUserRepository.users[3], "APPROVE")
