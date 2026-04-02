from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import List

from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.leave import LeaveApprover, LeaveCredit, LeaveRequest
from app.models.user import User


class LeaveApproverRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> List[LeaveApprover]:
        statement = (
            select(LeaveApprover)
            .options(
                selectinload(LeaveApprover.department),
                selectinload(LeaveApprover.department_approver).selectinload(User.department),
                selectinload(LeaveApprover.director_approver).selectinload(User.department),
                selectinload(LeaveApprover.president_approver).selectinload(User.department),
                selectinload(LeaveApprover.hr_approver).selectinload(User.department),
            )
            .join(Department, Department.id == LeaveApprover.department_id)
            .order_by(Department.name)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_department_id(self, department_id: int) -> LeaveApprover | None:
        statement = (
            select(LeaveApprover)
            .options(
                selectinload(LeaveApprover.department),
                selectinload(LeaveApprover.department_approver).selectinload(User.department),
                selectinload(LeaveApprover.director_approver).selectinload(User.department),
                selectinload(LeaveApprover.president_approver).selectinload(User.department),
                selectinload(LeaveApprover.hr_approver).selectinload(User.department),
            )
            .where(LeaveApprover.department_id == department_id)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, leave_approver: LeaveApprover) -> LeaveApprover:
        self.session.add(leave_approver)
        await self.session.commit()
        await self.session.refresh(leave_approver)
        hydrated = await self.get_by_department_id(leave_approver.department_id)
        return hydrated or leave_approver

    async def save(self, leave_approver: LeaveApprover) -> LeaveApprover:
        await self.session.commit()
        await self.session.refresh(leave_approver)
        hydrated = await self.get_by_department_id(leave_approver.department_id)
        return hydrated or leave_approver

    async def delete(self, leave_approver: LeaveApprover) -> None:
        await self.session.delete(leave_approver)
        await self.session.commit()


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

    async def get_by_user_id(self, user_id: int) -> LeaveCredit | None:
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
        )

    async def list(
        self,
        user_id: int | None = None,
        department_id: int | None = None,
        approver_id: int | None = None,
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
            statement = statement.where(
                or_(
                    LeaveRequest.first_approver_id == approver_id,
                    LeaveRequest.second_approver_id == approver_id,
                )
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
        )
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

    async def create(self, leave_request: LeaveRequest) -> LeaveRequest:
        self.session.add(leave_request)
        await self.session.commit()
        await self.session.refresh(leave_request)
        return leave_request

    async def save(self, leave_request: LeaveRequest) -> LeaveRequest:
        await self.session.commit()
        await self.session.refresh(leave_request)
        return leave_request

    async def delete(self, leave_request: LeaveRequest) -> None:
        await self.session.delete(leave_request)
        await self.session.commit()
