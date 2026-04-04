from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        statement = (
            select(User)
            .options(selectinload(User.department))
            .where(User.id == user_id)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .options(selectinload(User.department))
            .where(User.email == email)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_employee_number(self, employee_number: str) -> User | None:
        statement = (
            select(User)
            .options(selectinload(User.department))
            .where(User.employee_number == employee_number)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_biometric_uid(self, biometric_uid: int) -> User | None:
        statement = (
            select(User)
            .options(selectinload(User.department))
            .where(User.biometric_uid == biometric_uid)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(
        self,
        query: str | None = None,
        department_id: int | None = None,
        active_only: bool | None = None,
        include_superusers: bool = False,
        exclude_hr: bool = False,
        exclude_user_id: UUID | None = None,
    ) -> list[User]:
        statement = select(User).options(selectinload(User.department)).outerjoin(
            Department, Department.id == User.department_id
        )
        if not include_superusers:
            statement = statement.where(User.is_superuser.is_(False))
        if exclude_hr:
            hr_label = "HR"
            statement = statement.where(func.upper(func.coalesce(User.role, "")) != hr_label)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        if department_id is not None:
            statement = statement.where(User.department_id == department_id)
        if active_only is True:
            statement = statement.where(User.is_active.is_(True))
        if query:
            lowered = f"%{query.lower()}%"
            statement = statement.where(
                func.lower(User.first_name).like(lowered)
                | func.lower(User.last_name).like(lowered)
                | func.lower(User.email).like(lowered)
                | func.lower(User.employee_number).like(lowered)
            )
        statement = statement.order_by(
            func.lower(func.coalesce(User.last_name, "")),
            func.lower(func.coalesce(User.first_name, "")),
            User.id.asc(),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        refreshed = await self.get_by_id(user.id)
        if refreshed is None:
            return user
        return refreshed

    async def save(self, user: User) -> User:
        await self.session.commit()
        refreshed = await self.get_by_id(user.id)
        if refreshed is None:
            return user
        return refreshed
