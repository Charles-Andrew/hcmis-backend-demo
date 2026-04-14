from __future__ import annotations

from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.special_requests import (
    CertificateAttendanceRequest,
    CertificateAttendanceRequestApprover,
    OfficialBusinessRequest,
    OfficialBusinessRequestApprover,
)
from app.models.user import User


class OfficialBusinessRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _base_statement():
        return select(OfficialBusinessRequest).options(
            selectinload(OfficialBusinessRequest.user).selectinload(User.department),
            selectinload(OfficialBusinessRequest.approver).selectinload(User.department),
            selectinload(OfficialBusinessRequest.approver_pool)
            .selectinload(OfficialBusinessRequestApprover.approver)
            .selectinload(User.department),
        )

    async def list(
        self,
        *,
        user_id: UUID | None = None,
        approver_id: UUID | None = None,
        year: int | None = None,
        month: int | None = None,
        status: str | None = None,
        department_id: int | None = None,
        query: str | None = None,
    ) -> List[OfficialBusinessRequest]:
        statement = self._base_statement()
        if user_id is not None:
            statement = statement.where(OfficialBusinessRequest.user_id == user_id)
        if approver_id is not None:
            statement = statement.join(
                OfficialBusinessRequestApprover,
                OfficialBusinessRequestApprover.official_business_request_id
                == OfficialBusinessRequest.id,
            ).where(
                OfficialBusinessRequestApprover.approver_id == approver_id
            )
        if year is not None:
            statement = statement.where(func.extract("year", OfficialBusinessRequest.date) == year)
        if month is not None:
            statement = statement.where(
                func.extract("month", OfficialBusinessRequest.date) == month
            )
        if status is not None:
            statement = statement.where(OfficialBusinessRequest.status == status)
        if department_id is not None:
            statement = statement.where(
                OfficialBusinessRequest.user.has(User.department_id == department_id)
            )
        if query:
            lowered = f"%{query.lower()}%"
            statement = statement.where(
                OfficialBusinessRequest.user.has(
                    func.lower(User.first_name).like(lowered)
                    | func.lower(User.last_name).like(lowered)
                    | func.lower(User.email).like(lowered)
                )
            )

        statement = statement.order_by(
            OfficialBusinessRequest.status.asc(),
            OfficialBusinessRequest.date.desc(),
            OfficialBusinessRequest.id.desc(),
        ).distinct()
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, request_id: int) -> OfficialBusinessRequest | None:
        result = await self.session.execute(
            self._base_statement().where(OfficialBusinessRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_user_date(
        self,
        user_id: UUID,
        selected_date: date,
        *,
        statuses: tuple[str, ...],
    ) -> OfficialBusinessRequest | None:
        result = await self.session.execute(
            self._base_statement().where(
                OfficialBusinessRequest.user_id == user_id,
                OfficialBusinessRequest.date == selected_date,
                OfficialBusinessRequest.status.in_(statuses),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, request: OfficialBusinessRequest) -> OfficialBusinessRequest:
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        loaded = await self.get_by_id(request.id)
        return loaded or request

    async def save(self, request: OfficialBusinessRequest) -> OfficialBusinessRequest:
        await self.session.commit()
        await self.session.refresh(request)
        loaded = await self.get_by_id(request.id)
        return loaded or request


class CertificateAttendanceRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _base_statement():
        return select(CertificateAttendanceRequest).options(
            selectinload(CertificateAttendanceRequest.user).selectinload(User.department),
            selectinload(CertificateAttendanceRequest.approver).selectinload(User.department),
            selectinload(CertificateAttendanceRequest.approver_pool)
            .selectinload(CertificateAttendanceRequestApprover.approver)
            .selectinload(User.department),
        )

    async def list(
        self,
        *,
        user_id: UUID | None = None,
        approver_id: UUID | None = None,
        year: int | None = None,
        month: int | None = None,
        status: str | None = None,
        department_id: int | None = None,
        query: str | None = None,
    ) -> List[CertificateAttendanceRequest]:
        statement = self._base_statement()
        if user_id is not None:
            statement = statement.where(CertificateAttendanceRequest.user_id == user_id)
        if approver_id is not None:
            statement = statement.join(
                CertificateAttendanceRequestApprover,
                CertificateAttendanceRequestApprover.certificate_attendance_request_id
                == CertificateAttendanceRequest.id,
            ).where(
                CertificateAttendanceRequestApprover.approver_id == approver_id
            )
        if year is not None:
            statement = statement.where(
                func.extract("year", CertificateAttendanceRequest.date) == year
            )
        if month is not None:
            statement = statement.where(
                func.extract("month", CertificateAttendanceRequest.date) == month
            )
        if status is not None:
            statement = statement.where(CertificateAttendanceRequest.status == status)
        if department_id is not None:
            statement = statement.where(
                CertificateAttendanceRequest.user.has(User.department_id == department_id)
            )
        if query:
            lowered = f"%{query.lower()}%"
            statement = statement.where(
                CertificateAttendanceRequest.user.has(
                    func.lower(User.first_name).like(lowered)
                    | func.lower(User.last_name).like(lowered)
                    | func.lower(User.email).like(lowered)
                )
            )

        statement = statement.order_by(
            CertificateAttendanceRequest.status.asc(),
            CertificateAttendanceRequest.date.desc(),
            CertificateAttendanceRequest.id.desc(),
        ).distinct()
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, request_id: int) -> CertificateAttendanceRequest | None:
        result = await self.session.execute(
            self._base_statement().where(CertificateAttendanceRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_user_date(
        self,
        user_id: UUID,
        selected_date: date,
        *,
        statuses: tuple[str, ...],
    ) -> CertificateAttendanceRequest | None:
        result = await self.session.execute(
            self._base_statement().where(
                CertificateAttendanceRequest.user_id == user_id,
                CertificateAttendanceRequest.date == selected_date,
                CertificateAttendanceRequest.status.in_(statuses),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, request: CertificateAttendanceRequest) -> CertificateAttendanceRequest:
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        loaded = await self.get_by_id(request.id)
        return loaded or request

    async def save(self, request: CertificateAttendanceRequest) -> CertificateAttendanceRequest:
        await self.session.commit()
        await self.session.refresh(request)
        loaded = await self.get_by_id(request.id)
        return loaded or request
