from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.leave import LeaveCredit, LeaveRequest, LeaveRequestApprover
from app.models.user import User


class LeaveCreditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> List[LeaveCredit]:
        statement = (
            select(LeaveCredit)
            .options(selectinload(LeaveCredit.user).selectinload(User.department))
            .join(User, User.id == LeaveCredit.user_id)
            .outerjoin(Department, Department.id == User.department_id)
            .order_by(func.coalesce(Department.name, ""), User.first_name, User.last_name)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_user_id(self, user_id: UUID) -> LeaveCredit | None:
        statement = (
            select(LeaveCredit)
            .options(selectinload(LeaveCredit.user).selectinload(User.department))
            .where(LeaveCredit.user_id == user_id)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, leave_credit: LeaveCredit) -> LeaveCredit:
        self.session.add(leave_credit)
        await self.session.commit()
        await self.session.refresh(leave_credit)
        return leave_credit

    async def save(self, leave_credit: LeaveCredit) -> LeaveCredit:
        await self.session.commit()
        await self.session.refresh(leave_credit)
        return leave_credit


class LeaveRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_statement(self):
        return select(LeaveRequest).options(
            selectinload(LeaveRequest.user).selectinload(User.department),
            selectinload(LeaveRequest.first_approver).selectinload(User.department),
            selectinload(LeaveRequest.second_approver).selectinload(User.department),
            selectinload(LeaveRequest.approver_pool)
            .selectinload(LeaveRequestApprover.approver)
            .selectinload(User.department),
        )

    async def list(
        self,
        user_id: UUID | None = None,
        department_id: int | None = None,
        approver_id: UUID | None = None,
        status: str | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> List[LeaveRequest]:
        statement = self._base_statement()
        if user_id is not None:
            statement = statement.where(LeaveRequest.user_id == user_id)
        if department_id is not None:
            statement = statement.join(LeaveRequest.user).where(
                User.department_id == department_id
            )
        if approver_id is not None:
            statement = statement.join(
                LeaveRequestApprover,
                LeaveRequestApprover.leave_request_id == LeaveRequest.id,
            ).where(
                LeaveRequestApprover.approver_id == approver_id
            )
        if status is not None:
            statement = statement.where(LeaveRequest.status == status)
        if year is not None and month is not None:
            last_day = monthrange(year, month)[1]
            statement = statement.where(
                LeaveRequest.leave_date >= date(year, month, 1),
                LeaveRequest.leave_date <= date(year, month, last_day),
            )
        elif year is not None:
            statement = statement.where(
                LeaveRequest.leave_date >= date(year, 1, 1),
                LeaveRequest.leave_date <= date(year, 12, 31),
            )
        elif month is not None:
            statement = statement.where(extract("month", LeaveRequest.leave_date) == month)
        statement = statement.order_by(
            LeaveRequest.leave_date.desc(), LeaveRequest.created_at.desc()
        ).distinct()
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_years(self) -> List[int]:
        statement = (
            select(extract("year", LeaveRequest.leave_date))
            .distinct()
            .order_by(extract("year", LeaveRequest.leave_date))
        )
        result = await self.session.execute(statement)
        years: list[int] = []
        for value in result.scalars().all():
            if value is not None:
                years.append(int(value))
        return years

    async def get_by_id(self, leave_id: int) -> LeaveRequest | None:
        statement = self._base_statement().where(LeaveRequest.id == leave_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_for_user_date(
        self,
        user_id: UUID,
        selected_date: date,
        *,
        statuses: tuple[str, ...],
    ) -> LeaveRequest | None:
        statement = self._base_statement().where(
            LeaveRequest.user_id == user_id,
            LeaveRequest.leave_date == selected_date,
            LeaveRequest.status.in_(statuses),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, leave_request: LeaveRequest) -> LeaveRequest:
        self.session.add(leave_request)
        await self.session.commit()
        await self.session.refresh(leave_request)
        hydrated = await self.get_by_id(leave_request.id)
        return hydrated or leave_request

    async def save(self, leave_request: LeaveRequest) -> LeaveRequest:
        await self.session.commit()
        await self.session.refresh(leave_request)
        hydrated = await self.get_by_id(leave_request.id)
        return hydrated or leave_request

    async def delete(self, leave_request: LeaveRequest) -> None:
        await self.session.delete(leave_request)
        await self.session.commit()
