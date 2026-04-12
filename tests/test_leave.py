import anyio
import pytest
from datetime import date
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.attendance import OvertimeRequest
from app.models.department import Department
from app.models.leave import LeaveCredit, LeaveRequest, LeaveRequestStatus
from app.models.user import User
from app.schemas.leave import (
    LeaveCreditUpsertRequest,
    LeaveRequestCreateRequest,
    LeaveRequestReviewRequest,
)
from app.services import leave as leave_service


class FakeOvertimeRepository:
    overtime_requests = {}

    def __init__(self, session):
        self.session = session

    async def get_active_for_user_date(self, user_id: UUID, selected_date: date, *, statuses: tuple[str, ...]):
        for request in self.overtime_requests.values():
            if request.user_id == user_id and request.date == selected_date and request.status in statuses:
                return request
        return None


class FakeUserRepository:
    users: dict[UUID, User] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id: UUID):
        return self.users.get(user_id)


class FakeLeaveCreditRepository:
    leave_credits: dict[UUID, LeaveCredit] = {}

    def __init__(self, session):
        self.session = session

    async def list(self):
        return list(self.leave_credits.values())

    async def get_by_user_id(self, user_id: UUID):
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
    next_assignment_id = 1

    def __init__(self, session):
        self.session = session

    async def list(
        self,
        user_id: UUID | None = None,
        department_id: int | None = None,
        approver_id: UUID | None = None,
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
                if any(assignment.approver_id == approver_id for assignment in (item.approver_pool or []))
            ]
        if status is not None:
            requests = [item for item in requests if item.status == status]
        if year is not None:
            requests = [item for item in requests if item.leave_date.year == year]
        if month is not None:
            requests = [item for item in requests if item.leave_date.month == month]
        if department_id is not None:
            requests = [item for item in requests if FakeUserRepository.users[item.user_id].department_id == department_id]
        return sorted(requests, key=lambda item: (item.leave_date, item.created_at), reverse=True)

    async def list_years(self):
        return sorted({item.leave_date.year for item in self.leave_requests.values()})

    async def get_by_id(self, leave_id: int):
        return self.leave_requests.get(leave_id)

    async def get_active_for_user_date(self, user_id: UUID, selected_date: date, *, statuses: tuple[str, ...]):
        for request in self.leave_requests.values():
            if request.user_id == user_id and request.leave_date == selected_date and request.status in statuses:
                return request
        return None

    async def create(self, leave_request: LeaveRequest):
        leave_request.id = self.next_id
        self.next_id += 1
        leave_request.created_at = leave_request.created_at or utc_now()
        leave_request.updated_at = leave_request.updated_at or utc_now()
        for assignment in leave_request.approver_pool:
            assignment.id = assignment.id or self.next_assignment_id
            self.next_assignment_id += 1
            assignment.leave_request_id = leave_request.id
        self.leave_requests[leave_request.id] = leave_request
        return leave_request

    async def save(self, leave_request: LeaveRequest):
        leave_request.updated_at = utc_now()
        self.leave_requests[leave_request.id] = leave_request
        return leave_request


async def _create_leave(payload: dict) -> LeaveRequest:
    employee = FakeUserRepository.users[UUID(int=1)]
    return await leave_service.create_leave_request(
        cast(AsyncSession, object()),
        employee,
        LeaveRequestCreateRequest(**payload),
    )


async def _review_leave(leave_id: int, user: User, response: Literal["APPROVE", "REJECT"]) -> LeaveRequest:
    return await leave_service.review_leave_request(
        cast(AsyncSession, object()),
        leave_id,
        user,
        LeaveRequestReviewRequest(response=response),
    )


def _reset_fakes():
    FakeUserRepository.users = {}
    FakeLeaveCreditRepository.leave_credits = {}
    FakeLeaveRequestRepository.leave_requests = {}
    FakeLeaveRequestRepository.next_id = 1
    FakeLeaveRequestRepository.next_assignment_id = 1
    FakeOvertimeRepository.overtime_requests = {}


def _seed_users():
    department = Department(id=1, name="Operations", code="OPS", is_active=True, workweek=[])

    employee = User(
        id=UUID(int=1),
        email="employee@example.com",
        password_hash="hashed",
        first_name="Emp",
        last_name="One",
        role="EMP",
        department_id=department.id,
        level_1_approver_id=UUID(int=2),
        level_2_approver_id=UUID(int=3),
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    level_1 = User(
        id=UUID(int=2),
        email="l1@example.com",
        password_hash="hashed",
        first_name="Level",
        last_name="One",
        role="DH",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    level_2 = User(
        id=UUID(int=3),
        email="l2@example.com",
        password_hash="hashed",
        first_name="Level",
        last_name="Two",
        role="HR",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    hr_admin = User(
        id=UUID(int=4),
        email="admin@example.com",
        password_hash="hashed",
        first_name="Admin",
        last_name="User",
        role="HR",
        department_id=department.id,
        can_modify_shift=False,
        is_active=True,
        is_superuser=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    for user in [employee, level_1, level_2, hr_admin]:
        FakeUserRepository.users[user.id] = user

    FakeLeaveCreditRepository.leave_credits[employee.id] = LeaveCredit(
        user_id=employee.id,
        credits=10,
        used_credits=0,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def _patch_dependencies(monkeypatch):
    monkeypatch.setattr(leave_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(leave_service, "LeaveCreditRepository", FakeLeaveCreditRepository)
    monkeypatch.setattr(leave_service, "LeaveRequestRepository", FakeLeaveRequestRepository)
    monkeypatch.setattr(leave_service, "OvertimeRepository", FakeOvertimeRepository)


def test_leave_request_creation_uses_level_1_and_backup(monkeypatch):
    _reset_fakes()
    _seed_users()
    _patch_dependencies(monkeypatch)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 1), "leave_type": "PA", "info": "Family matter"},
    )

    assert leave_request.first_approver_id == UUID(int=2)
    assert leave_request.second_approver_id == UUID(int=3)
    assert [assignment.approver_id for assignment in leave_request.approver_pool] == [UUID(int=2)]


def test_leave_request_review_approves_and_consumes_credit(monkeypatch):
    _reset_fakes()
    _seed_users()
    _patch_dependencies(monkeypatch)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 1), "leave_type": "PA", "info": "Annual leave"},
    )

    reviewed = anyio.run(_review_leave, leave_request.id, FakeUserRepository.users[UUID(int=2)], "APPROVE")
    assert reviewed.status == LeaveRequestStatus.APPROVED.value
    assert reviewed.first_approver_status == LeaveRequestStatus.APPROVED.value
    assert FakeLeaveCreditRepository.leave_credits[UUID(int=1)].used_credits == 1


def test_leave_escalation_routes_to_backup(monkeypatch):
    _reset_fakes()
    _seed_users()
    _patch_dependencies(monkeypatch)

    leave_request = anyio.run(
        _create_leave,
        {"leave_date": date(2026, 4, 3), "leave_type": "UN", "info": "Travel"},
    )

    escalated = anyio.run(
        leave_service.escalate_leave_request,
        cast(AsyncSession, object()),
        leave_request.id,
        FakeUserRepository.users[UUID(int=4)],
    )

    assert escalated.escalated_to_backup_by_id == UUID(int=4)
    assert escalated.escalated_to_backup_at is not None
    assert escalated.first_approver_status == LeaveRequestStatus.CANCELLED.value
    assert escalated.second_approver_status == LeaveRequestStatus.PENDING.value


def test_create_leave_request_rejects_same_day_active_overtime(monkeypatch):
    _reset_fakes()
    _seed_users()
    _patch_dependencies(monkeypatch)

    FakeOvertimeRepository.overtime_requests = {
        1: OvertimeRequest(
            id=1,
            user_id=UUID(int=1),
            approver_id=UUID(int=2),
            info="Overtime",
            date=date(2026, 4, 11),
            status=OvertimeRequest.Status.PENDING.value,
            approver_pool=[],
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    }

    with pytest.raises(leave_service.ConflictError, match="active overtime request already exists"):
        anyio.run(
            _create_leave,
            {"leave_date": date(2026, 4, 11), "leave_type": "PA", "info": "Leave"},
        )


def test_leave_credit_management(monkeypatch):
    _reset_fakes()
    _seed_users()
    _patch_dependencies(monkeypatch)

    credit = anyio.run(
        leave_service.set_leave_credit,
        cast(AsyncSession, object()),
        UUID(int=1),
        LeaveCreditUpsertRequest(credits=15),
    )
    assert credit.credits == 15

    reset_credit = anyio.run(
        leave_service.reset_leave_credit,
        cast(AsyncSession, object()),
        UUID(int=1),
    )
    assert reset_credit.used_credits == 0
