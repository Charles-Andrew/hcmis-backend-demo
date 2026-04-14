import anyio
from datetime import UTC, date, datetime, time
from typing import Literal, cast
from uuid import UUID

from app.core.time import utc_now
from app.models.special_requests import (
    CertificateAttendanceRequest,
    CertificateAttendanceRequestApprover,
    SpecialRequestStatus,
)
from app.schemas.special_requests import SpecialRequestRespondRequest
from app.services import special_requests as special_requests_service
from sqlalchemy.ext.asyncio import AsyncSession


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, item: object) -> None:
        self.added.append(item)


class FakeCertificateAttendanceRequestRepository:
    requests: dict[int, CertificateAttendanceRequest] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, request_id: int):
        return self.requests.get(request_id)

    async def save(self, request: CertificateAttendanceRequest):
        request.updated_at = utc_now()
        self.requests[request.id] = request
        return request


class FakeAttendanceRecordRepository:
    duplicates: set[tuple[UUID, datetime, str]] = set()

    def __init__(self, session):
        self.session = session

    async def get_duplicate(self, user_id: UUID, timestamp: datetime, punch: str):
        if (user_id, timestamp, punch) in self.duplicates:
            return object()
        return None


def _build_request(*, punch: str = "IN") -> CertificateAttendanceRequest:
    requester_id = UUID(int=101)
    approver_id = UUID(int=202)
    request = CertificateAttendanceRequest(
        id=1,
        user_id=requester_id,
        approver_id=approver_id,
        info="Certificate correction",
        date=date(2026, 4, 10),
        time=time(8, 45),
        punch=punch,
        status=SpecialRequestStatus.PENDING.value,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    request.approver_pool = [
        CertificateAttendanceRequestApprover(
            id=1,
            certificate_attendance_request_id=1,
            approver_id=approver_id,
            status=SpecialRequestStatus.PENDING.value,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    ]
    return request


async def _respond(
    session: FakeSession,
    request_id: int,
    approver_id: UUID,
    response: Literal["APPROVE", "REJECT"],
):
    return await special_requests_service.respond_to_certificate_attendance_request(
        cast(AsyncSession, session),
        request_id,
        approver_id,
        SpecialRequestRespondRequest(response=response),
    )


def test_approve_certificate_request_adds_attendance_record(monkeypatch):
    request = _build_request(punch="OUT")
    FakeCertificateAttendanceRequestRepository.requests = {request.id: request}
    FakeAttendanceRecordRepository.duplicates = set()

    monkeypatch.setattr(
        special_requests_service,
        "CertificateAttendanceRequestRepository",
        FakeCertificateAttendanceRequestRepository,
    )
    monkeypatch.setattr(
        special_requests_service,
        "AttendanceRecordRepository",
        FakeAttendanceRecordRepository,
    )

    session = FakeSession()
    updated = anyio.run(_respond, session, request.id, request.approver_id, "APPROVE")

    assert updated.status == SpecialRequestStatus.APPROVED.value
    assert len(session.added) == 1

    attendance_record = session.added[0]
    assert getattr(attendance_record, "user_id") == request.user_id
    assert getattr(attendance_record, "punch") == "OUT"
    assert getattr(attendance_record, "timestamp") == datetime(
        2026, 4, 10, 8, 45, tzinfo=UTC
    )


def test_reject_certificate_request_does_not_add_attendance_record(monkeypatch):
    request = _build_request(punch="IN")
    FakeCertificateAttendanceRequestRepository.requests = {request.id: request}
    FakeAttendanceRecordRepository.duplicates = set()

    monkeypatch.setattr(
        special_requests_service,
        "CertificateAttendanceRequestRepository",
        FakeCertificateAttendanceRequestRepository,
    )
    monkeypatch.setattr(
        special_requests_service,
        "AttendanceRecordRepository",
        FakeAttendanceRecordRepository,
    )

    session = FakeSession()
    updated = anyio.run(_respond, session, request.id, request.approver_id, "REJECT")

    assert updated.status == SpecialRequestStatus.REJECTED.value
    assert session.added == []
