from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department


class DepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[Department]:
        statement = select(Department).order_by(Department.name)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, department_id: int) -> Department | None:
        statement = (
            select(Department)
            .options(
                selectinload(Department.shift_templates),
                selectinload(Department.department_roster_days),
            )
            .where(Department.id == department_id)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Department | None:
        statement = select(Department).where(func.lower(Department.name) == name.lower())
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Department | None:
        statement = select(Department).where(func.lower(Department.code) == code.lower())
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, department: Department) -> Department:
        self.session.add(department)
        await self.session.commit()
        await self.session.refresh(department)
        return department

    async def save(self, department: Department) -> Department:
        await self.session.commit()
        await self.session.refresh(department)
        return department

    async def delete(self, department: Department) -> None:
        await self.session.delete(department)
        await self.session.commit()
