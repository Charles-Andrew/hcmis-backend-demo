from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.payroll import (
    FixedCompensation,
    Job,
    Mp2Account,
    PayrollSetting,
    Payslip,
    PayslipVariableCompensation,
    PayslipVariableDeduction,
    ThirteenthMonthPay,
    ThirteenthMonthPayVariableDeduction,
)
from app.models.user import User


class PayrollSettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_first(self) -> PayrollSetting | None:
        result = await self.session.execute(select(PayrollSetting).limit(1))
        return result.scalar_one_or_none()

    async def create(self, settings: PayrollSetting) -> PayrollSetting:
        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    async def save(self, settings: PayrollSetting) -> PayrollSetting:
        await self.session.commit()
        await self.session.refresh(settings)
        return settings


class Mp2Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_first(self) -> Mp2Account | None:
        result = await self.session.execute(
            select(Mp2Account).options(selectinload(Mp2Account.users)).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, mp2: Mp2Account) -> Mp2Account:
        self.session.add(mp2)
        await self.session.commit()
        await self.session.refresh(mp2)
        return mp2

    async def save(self, mp2: Mp2Account) -> Mp2Account:
        await self.session.commit()
        await self.session.refresh(mp2)
        return mp2


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, department_id: int | None = None) -> list[Job]:
        statement = select(Job).options(selectinload(Job.departments)).order_by(Job.title)
        if department_id is not None:
            statement = statement.join(Job.departments).where(Department.id == department_id)
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_by_id(self, job_id: int) -> Job | None:
        result = await self.session.execute(
            select(Job).options(selectinload(Job.departments)).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Job | None:
        result = await self.session.execute(
            select(Job).options(selectinload(Job.departments)).where(func.lower(Job.code) == code.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def save(self, job: Job) -> Job:
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete(self, job: Job) -> None:
        await self.session.delete(job)
        await self.session.commit()


class FixedCompensationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, month: int | None = None, year: int | None = None) -> list[FixedCompensation]:
        statement = select(FixedCompensation).options(
            selectinload(FixedCompensation.users).selectinload(User.department)
        ).order_by(FixedCompensation.year.desc(), FixedCompensation.month.desc(), FixedCompensation.name)
        if month is not None:
            statement = statement.where(FixedCompensation.month == month)
        if year is not None:
            statement = statement.where(FixedCompensation.year == year)
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_by_id(self, compensation_id: int) -> FixedCompensation | None:
        result = await self.session.execute(
            select(FixedCompensation)
            .options(selectinload(FixedCompensation.users).selectinload(User.department))
            .where(FixedCompensation.id == compensation_id)
        )
        return result.scalar_one_or_none()

    async def create(self, compensation: FixedCompensation) -> FixedCompensation:
        self.session.add(compensation)
        await self.session.commit()
        await self.session.refresh(compensation)
        return compensation

    async def save(self, compensation: FixedCompensation) -> FixedCompensation:
        await self.session.commit()
        await self.session.refresh(compensation)
        return compensation

    async def delete(self, compensation: FixedCompensation) -> None:
        await self.session.delete(compensation)
        await self.session.commit()


class PayslipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        user_id: int | None = None,
        month: int | None = None,
        year: int | None = None,
        period: str | None = None,
        released: bool | None = None,
    ) -> list[Payslip]:
        statement = select(Payslip).options(
            selectinload(Payslip.user).selectinload(User.department),
            selectinload(Payslip.variable_compensations),
            selectinload(Payslip.variable_deductions),
        )
        if user_id is not None:
            statement = statement.where(Payslip.user_id == user_id)
        if month is not None:
            statement = statement.where(Payslip.month == month)
        if year is not None:
            statement = statement.where(Payslip.year == year)
        if period is not None:
            statement = statement.where(Payslip.period == period)
        if released is not None:
            statement = statement.where(Payslip.released.is_(released))
        statement = statement.order_by(Payslip.year.desc(), Payslip.month.desc(), Payslip.period.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, payslip_id: int) -> Payslip | None:
        result = await self.session.execute(
            select(Payslip)
            .options(
                selectinload(Payslip.user).selectinload(User.department),
                selectinload(Payslip.variable_compensations),
                selectinload(Payslip.variable_deductions),
            )
            .where(Payslip.id == payslip_id)
        )
        return result.scalar_one_or_none()

    async def get_by_identity(self, user_id: int, month: int, year: int, period: str) -> Payslip | None:
        result = await self.session.execute(
            select(Payslip).where(
                Payslip.user_id == user_id,
                Payslip.month == month,
                Payslip.year == year,
                Payslip.period == period,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, payslip: Payslip) -> Payslip:
        self.session.add(payslip)
        await self.session.commit()
        await self.session.refresh(payslip)
        return payslip

    async def save(self, payslip: Payslip) -> Payslip:
        await self.session.commit()
        await self.session.refresh(payslip)
        return payslip

    async def delete(self, payslip: Payslip) -> None:
        await self.session.delete(payslip)
        await self.session.commit()


class PayslipVariableCompensationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, item: PayslipVariableCompensation) -> PayslipVariableCompensation:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_by_id(self, item_id: int) -> PayslipVariableCompensation | None:
        result = await self.session.execute(
            select(PayslipVariableCompensation).where(PayslipVariableCompensation.id == item_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, item: PayslipVariableCompensation) -> None:
        await self.session.delete(item)
        await self.session.commit()


class PayslipVariableDeductionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, item: PayslipVariableDeduction) -> PayslipVariableDeduction:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_by_id(self, item_id: int) -> PayslipVariableDeduction | None:
        result = await self.session.execute(
            select(PayslipVariableDeduction).where(PayslipVariableDeduction.id == item_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, item: PayslipVariableDeduction) -> None:
        await self.session.delete(item)
        await self.session.commit()


class ThirteenthMonthPayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        user_id: int | None = None,
        month: int | None = None,
        year: int | None = None,
        released: bool | None = None,
    ) -> list[ThirteenthMonthPay]:
        statement = select(ThirteenthMonthPay).options(
            selectinload(ThirteenthMonthPay.user).selectinload(User.department),
            selectinload(ThirteenthMonthPay.variable_deductions),
        )
        if user_id is not None:
            statement = statement.where(ThirteenthMonthPay.user_id == user_id)
        if month is not None:
            statement = statement.where(ThirteenthMonthPay.month == month)
        if year is not None:
            statement = statement.where(ThirteenthMonthPay.year == year)
        if released is not None:
            statement = statement.where(ThirteenthMonthPay.released.is_(released))
        statement = statement.order_by(
            ThirteenthMonthPay.year.desc(),
            ThirteenthMonthPay.month.desc(),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, item_id: int) -> ThirteenthMonthPay | None:
        result = await self.session.execute(
            select(ThirteenthMonthPay)
            .options(
                selectinload(ThirteenthMonthPay.user).selectinload(User.department),
                selectinload(ThirteenthMonthPay.variable_deductions),
            )
            .where(ThirteenthMonthPay.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_by_identity(
        self, user_id: int, month: int, year: int
    ) -> ThirteenthMonthPay | None:
        result = await self.session.execute(
            select(ThirteenthMonthPay).where(
                ThirteenthMonthPay.user_id == user_id,
                ThirteenthMonthPay.month == month,
                ThirteenthMonthPay.year == year,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, item: ThirteenthMonthPay) -> ThirteenthMonthPay:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save(self, item: ThirteenthMonthPay) -> ThirteenthMonthPay:
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: ThirteenthMonthPay) -> None:
        await self.session.delete(item)
        await self.session.commit()


class ThirteenthMonthPayVariableDeductionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, item: ThirteenthMonthPayVariableDeduction
    ) -> ThirteenthMonthPayVariableDeduction:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_by_id(self, item_id: int) -> ThirteenthMonthPayVariableDeduction | None:
        result = await self.session.execute(
            select(ThirteenthMonthPayVariableDeduction).where(
                ThirteenthMonthPayVariableDeduction.id == item_id
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, item: ThirteenthMonthPayVariableDeduction) -> None:
        await self.session.delete(item)
        await self.session.commit()
