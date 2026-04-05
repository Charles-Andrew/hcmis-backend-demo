from __future__ import annotations

from datetime import date
from typing import Any, List
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.payroll import (
    FixedCompensation,
    Position,
    Mp2Account,
    PayrollPolicyVersion,
    PayrollPolicySource,
    PayrollRun,
    PayrollRunItem,
    PolicySssBracket,
    PolicyPhilhealthRule,
    PolicyPagibigRule,
    PolicyBirWithholdingBracket,
    PolicyMinimumWageOrder,
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


class PayrollPolicyVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, policy_key: str | None = None) -> List[PayrollPolicyVersion]:
        statement = select(PayrollPolicyVersion).order_by(
            PayrollPolicyVersion.effective_from.desc(),
            PayrollPolicyVersion.created_at.desc(),
        )
        if policy_key is not None:
            statement = statement.where(PayrollPolicyVersion.policy_key == policy_key)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, policy_version_id: int) -> PayrollPolicyVersion | None:
        result = await self.session.execute(
            select(PayrollPolicyVersion).where(PayrollPolicyVersion.id == policy_version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_identity(self, policy_key: str, version_label: str) -> PayrollPolicyVersion | None:
        result = await self.session.execute(
            select(PayrollPolicyVersion).where(
                PayrollPolicyVersion.policy_key == policy_key,
                PayrollPolicyVersion.version_label == version_label,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_effective(
        self,
        policy_key: str,
        effective_date: date,
    ) -> PayrollPolicyVersion | None:
        result = await self.session.execute(
            select(PayrollPolicyVersion)
            .where(
                and_(
                    PayrollPolicyVersion.policy_key == policy_key,
                    PayrollPolicyVersion.is_active.is_(True),
                    PayrollPolicyVersion.effective_from <= effective_date,
                    or_(
                        PayrollPolicyVersion.effective_to.is_(None),
                        PayrollPolicyVersion.effective_to >= effective_date,
                    ),
                )
            )
            .order_by(
                PayrollPolicyVersion.effective_from.desc(),
                PayrollPolicyVersion.created_at.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, item: PayrollPolicyVersion) -> PayrollPolicyVersion:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save(self, item: PayrollPolicyVersion) -> PayrollPolicyVersion:
        await self.session.commit()
        await self.session.refresh(item)
        return item


class PayrollPolicySourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, policy_version_id: int) -> List[PayrollPolicySource]:
        result = await self.session.execute(
            select(PayrollPolicySource)
            .where(PayrollPolicySource.policy_version_id == policy_version_id)
            .order_by(
                PayrollPolicySource.effective_from.desc(),
                PayrollPolicySource.id.asc(),
            )
        )
        return list(result.scalars().all())

    async def replace(
        self,
        policy_version_id: int,
        sources: List[dict[str, Any]],
        applied_by,
        applied_at,
    ) -> List[PayrollPolicySource]:
        await self.session.execute(
            delete(PayrollPolicySource).where(
                PayrollPolicySource.policy_version_id == policy_version_id
            )
        )
        items = [
            PayrollPolicySource(
                policy_version_id=policy_version_id,
                source_type=item["source_type"],
                reference_code=item["reference_code"],
                source_url=item["source_url"],
                effective_from=item["effective_from"],
                effective_to=item.get("effective_to"),
                applied_by=applied_by,
                applied_at=applied_at,
            )
            for item in sources
        ]
        self.session.add_all(items)
        await self.session.commit()
        for item in items:
            await self.session.refresh(item)
        return items


class PayrollPolicyRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def clear_policy_rules(self, policy_version_id: int) -> None:
        await self.session.execute(
            delete(PolicySssBracket).where(PolicySssBracket.policy_version_id == policy_version_id)
        )
        await self.session.execute(
            delete(PolicyPhilhealthRule).where(
                PolicyPhilhealthRule.policy_version_id == policy_version_id
            )
        )
        await self.session.execute(
            delete(PolicyPagibigRule).where(PolicyPagibigRule.policy_version_id == policy_version_id)
        )
        await self.session.execute(
            delete(PolicyBirWithholdingBracket).where(
                PolicyBirWithholdingBracket.policy_version_id == policy_version_id
            )
        )
        await self.session.execute(
            delete(PolicyMinimumWageOrder).where(
                PolicyMinimumWageOrder.policy_version_id == policy_version_id
            )
        )

    async def seed_ph_baseline(self, policy_version_id: int) -> None:
        self.session.add_all(
            [
                PolicySssBracket(
                    policy_version_id=policy_version_id,
                    min_compensation=0,
                    max_compensation=999999,
                    employee_share=0,
                    employer_share=0,
                ),
                PolicyPhilhealthRule(
                    policy_version_id=policy_version_id,
                    min_compensation=0,
                    max_compensation=999999,
                    rate=0,
                    employee_share_ratio=0.5,
                ),
                PolicyPagibigRule(
                    policy_version_id=policy_version_id,
                    min_compensation=0,
                    monthly_compensation_cap=100000,
                    employee_rate=0,
                    employer_rate=0,
                    max_employee_share=0,
                    max_employer_share=0,
                ),
                PolicyBirWithholdingBracket(
                    policy_version_id=policy_version_id,
                    payroll_period="SEMI_MONTHLY",
                    min_compensation=0,
                    max_compensation=None,
                    base_tax=0,
                    marginal_rate=0,
                    over_amount=0,
                ),
                PolicyMinimumWageOrder(
                    policy_version_id=policy_version_id,
                    region_code="NCR",
                    sector="GENERAL",
                    daily_wage_amount=0,
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    source_reference="To be calibrated against official wage order.",
                ),
            ]
        )
        await self.session.commit()

    async def get_policy_rules(self, policy_version_id: int) -> dict[str, list[Any]]:
        sss_result = await self.session.execute(
            select(PolicySssBracket)
            .where(PolicySssBracket.policy_version_id == policy_version_id)
            .order_by(PolicySssBracket.min_compensation.asc())
        )
        philhealth_result = await self.session.execute(
            select(PolicyPhilhealthRule)
            .where(PolicyPhilhealthRule.policy_version_id == policy_version_id)
            .order_by(PolicyPhilhealthRule.min_compensation.asc())
        )
        pagibig_result = await self.session.execute(
            select(PolicyPagibigRule)
            .where(PolicyPagibigRule.policy_version_id == policy_version_id)
            .order_by(PolicyPagibigRule.id.asc())
        )
        bir_result = await self.session.execute(
            select(PolicyBirWithholdingBracket)
            .where(PolicyBirWithholdingBracket.policy_version_id == policy_version_id)
            .order_by(
                PolicyBirWithholdingBracket.payroll_period.asc(),
                PolicyBirWithholdingBracket.min_compensation.asc(),
            )
        )
        wage_result = await self.session.execute(
            select(PolicyMinimumWageOrder)
            .where(PolicyMinimumWageOrder.policy_version_id == policy_version_id)
            .order_by(
                PolicyMinimumWageOrder.region_code.asc(),
                PolicyMinimumWageOrder.effective_from.desc(),
            )
        )
        return {
            "sss_brackets": list(sss_result.scalars().all()),
            "philhealth_rules": list(philhealth_result.scalars().all()),
            "pagibig_rules": list(pagibig_result.scalars().all()),
            "bir_withholding_brackets": list(bir_result.scalars().all()),
            "minimum_wage_orders": list(wage_result.scalars().all()),
        }

    async def replace_policy_rules(
        self,
        policy_version_id: int,
        payload: dict[str, list[dict[str, Any]]],
    ) -> None:
        await self.clear_policy_rules(policy_version_id)
        self.session.add_all(
            [
                PolicySssBracket(policy_version_id=policy_version_id, **item)
                for item in payload["sss_brackets"]
            ]
            + [
                PolicyPhilhealthRule(policy_version_id=policy_version_id, **item)
                for item in payload["philhealth_rules"]
            ]
            + [
                PolicyPagibigRule(policy_version_id=policy_version_id, **item)
                for item in payload["pagibig_rules"]
            ]
            + [
                PolicyBirWithholdingBracket(policy_version_id=policy_version_id, **item)
                for item in payload["bir_withholding_brackets"]
            ]
            + [
                PolicyMinimumWageOrder(policy_version_id=policy_version_id, **item)
                for item in payload["minimum_wage_orders"]
            ]
        )
        await self.session.commit()


class PayrollRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, month: int | None = None, year: int | None = None) -> List[PayrollRun]:
        statement = select(PayrollRun).order_by(
            PayrollRun.year.desc(),
            PayrollRun.month.desc(),
            PayrollRun.period.desc(),
        )
        if month is not None:
            statement = statement.where(PayrollRun.month == month)
        if year is not None:
            statement = statement.where(PayrollRun.year == year)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, payroll_run_id: int) -> PayrollRun | None:
        result = await self.session.execute(select(PayrollRun).where(PayrollRun.id == payroll_run_id))
        return result.scalar_one_or_none()

    async def get_by_identity(self, month: int, year: int, period: str) -> PayrollRun | None:
        result = await self.session.execute(
            select(PayrollRun).where(
                PayrollRun.month == month,
                PayrollRun.year == year,
                PayrollRun.period == period,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, item: PayrollRun) -> PayrollRun:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save(self, item: PayrollRun) -> PayrollRun:
        await self.session.commit()
        await self.session.refresh(item)
        return item


class PayrollRunItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, payroll_run_id: int) -> List[PayrollRunItem]:
        result = await self.session.execute(
            select(PayrollRunItem)
            .where(PayrollRunItem.payroll_run_id == payroll_run_id)
            .order_by(PayrollRunItem.id.asc())
        )
        return list(result.scalars().all())

    async def clear(self, payroll_run_id: int) -> None:
        await self.session.execute(
            delete(PayrollRunItem).where(PayrollRunItem.payroll_run_id == payroll_run_id)
        )
        await self.session.commit()

    async def create_many(self, items: List[PayrollRunItem]) -> List[PayrollRunItem]:
        self.session.add_all(items)
        await self.session.commit()
        for item in items:
            await self.session.refresh(item)
        return items


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


class PositionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, department_id: int | None = None) -> List[Position]:
        statement = select(Position).options(selectinload(Position.departments)).order_by(Position.title)
        if department_id is not None:
            statement = statement.join(Position.departments).where(Department.id == department_id)
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_by_id(self, position_id: int) -> Position | None:
        result = await self.session.execute(
            select(Position).options(selectinload(Position.departments)).where(Position.id == position_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Position | None:
        result = await self.session.execute(
            select(Position).options(selectinload(Position.departments)).where(func.lower(Position.code) == code.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, position: Position) -> Position:
        self.session.add(position)
        await self.session.commit()
        await self.session.refresh(position)
        return position

    async def save(self, position: Position) -> Position:
        await self.session.commit()
        await self.session.refresh(position)
        return position

    async def delete(self, position: Position) -> None:
        await self.session.delete(position)
        await self.session.commit()


class FixedCompensationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, month: int | None = None, year: int | None = None) -> List[FixedCompensation]:
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
        user_id: UUID | None = None,
        month: int | None = None,
        year: int | None = None,
        period: str | None = None,
        released: bool | None = None,
    ) -> List[Payslip]:
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

    async def get_by_identity(self, user_id: UUID, month: int, year: int, period: str) -> Payslip | None:
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
        user_id: UUID | None = None,
        month: int | None = None,
        year: int | None = None,
        released: bool | None = None,
    ) -> List[ThirteenthMonthPay]:
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
        self, user_id: UUID, month: int, year: int
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
