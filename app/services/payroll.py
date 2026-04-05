from __future__ import annotations

import re
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.models.payroll import (
    FixedCompensation,
    Position,
    Mp2Account,
    PayrollSetting,
    Payslip,
    PayslipVariableCompensation,
    PayslipVariableDeduction,
    ThirteenthMonthPay,
    ThirteenthMonthPayVariableDeduction,
)
from app.models.department import Department
from app.models.user import User
from app.repositories.departments import DepartmentRepository
from app.repositories.payroll import (
    FixedCompensationRepository,
    PositionRepository,
    Mp2Repository,
    PayrollSettingRepository,
    PayslipRepository,
    PayslipVariableCompensationRepository,
    PayslipVariableDeductionRepository,
    ThirteenthMonthPayRepository,
    ThirteenthMonthPayVariableDeductionRepository,
)
from app.repositories.users import UserRepository
from app.services.notifications import create_notification_if_possible
from app.schemas.payroll import (
    FixedCompensationUpsertRequest,
    FixedCompensationUsersRequest,
    PositionUpsertRequest,
    PayrollSettingUpdateRequest,
    PayslipCreateRequest,
    PayslipUpdateRequest,
    PayslipVariableCompensationUpsertRequest,
    PayslipVariableDeductionUpsertRequest,
    ThirteenthMonthPayCreateRequest,
    ThirteenthMonthPayUpdateRequest,
    ThirteenthMonthPayVariableDeductionUpsertRequest,
)


DEFAULT_DEDUCTION_CONFIG = [
    {
        "name": "SSS",
        "data": {
            "min_compensation": "0",
            "max_compensation": "999999",
            "min_contribution": "0",
            "max_contribution": "0",
            "contribution_difference": "0",
        },
    },
    {
        "name": "PHILHEALTH",
        "data": {
            "min_compensation": "0",
            "max_compensation": "999999",
            "min_contribution": "0",
            "max_contribution": "0",
            "rate": "0",
        },
    },
    {
        "name": "TAX",
        "data": {
            "compensation_range": "0",
            "percentage": "0",
            "base_tax": "0",
        },
    },
    {
        "name": "PAG-IBIG",
        "data": {"amount": "0"},
    },
]


def _to_decimal(value: Decimal | int | str | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _month_period_pattern() -> re.Pattern[str]:
    return re.compile(r"^(?P<position_code>[A-Z0-9]+)-(?P<rank>\d+)(?: - STEP (?P<step>\d+))?$")


async def get_settings(session: AsyncSession) -> PayrollSetting:
    repository = PayrollSettingRepository(session)
    settings = await repository.get_first()
    if settings is None:
        settings = PayrollSetting(
            id=1,
            minimum_wage_amount=Decimal("0.00"),
            deduction_config=DEFAULT_DEDUCTION_CONFIG,
            basic_salary_multiplier=Decimal("1.0000"),
            basic_salary_step_multiplier=Decimal("1.0000"),
            basic_salary_steps=10,
            max_position_rank=10,
        )
        return await repository.create(settings)
    return settings


async def update_settings(
    session: AsyncSession, payload: PayrollSettingUpdateRequest
) -> PayrollSetting:
    settings = await get_settings(session)
    data = payload.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(settings, field_name, value)
    return await PayrollSettingRepository(session).save(settings)


async def get_mp2(session: AsyncSession) -> Mp2Account:
    repository = Mp2Repository(session)
    mp2 = await repository.get_first()
    if mp2 is None:
        mp2 = Mp2Account(id=1, amount=Decimal("0.00"))
        return await repository.create(mp2)
    return mp2


async def update_mp2(
    session: AsyncSession, amount: Decimal, user_ids: list[UUID]
) -> Mp2Account:
    mp2 = await get_mp2(session)
    mp2.amount = amount
    user_repository = UserRepository(session)
    users = []
    for user_id in user_ids:
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        users.append(user)
    mp2.users = users
    return await Mp2Repository(session).save(mp2)


def list_deduction_config() -> list[dict]:
    return [item.copy() for item in DEFAULT_DEDUCTION_CONFIG]


def _salary_grade_amount(settings: PayrollSetting, grade: int) -> Decimal:
    if grade < 1:
        raise ConflictError("Salary grade must be greater than zero.")
    base = _to_decimal(settings.minimum_wage_amount)
    multiplier = _to_decimal(settings.basic_salary_multiplier)
    value = base
    for _ in range(grade - 1):
        value *= multiplier
    return value


def _salary_steps(settings: PayrollSetting, base_salary: Decimal) -> list[dict[str, Decimal]]:
    steps: list[dict[str, Decimal]] = []
    current = base_salary
    step_multiplier = _to_decimal(settings.basic_salary_step_multiplier)
    for step in range(1, settings.basic_salary_steps + 1):
        current = current * step_multiplier
        steps.append({f"STEP {step}": current.quantize(Decimal("0.01"))})
    return steps


async def list_positions(session: AsyncSession, department_id: int | None = None) -> list[Position]:
    return await PositionRepository(session).list(department_id=department_id)


async def _resolve_departments(
    session: AsyncSession, department_ids: list[int]
) -> list[Department]:
    department_repository = DepartmentRepository(session)
    departments = []
    for department_id in dict.fromkeys(department_ids):
        department = await department_repository.get_by_id(department_id)
        if department is None:
            raise NotFoundError("Department not found.")
        departments.append(department)
    return departments


async def create_position(session: AsyncSession, payload: PositionUpsertRequest) -> Position:
    repository = PositionRepository(session)
    if await repository.get_by_code(payload.code):
        raise ConflictError("Position code already exists.")
    position = Position(
        title=payload.title,
        code=payload.code.upper(),
        salary_grade=payload.salary_grade,
        is_active=payload.is_active,
    )
    created = await repository.create(position)
    if payload.department_ids:
        departments = await _resolve_departments(session, payload.department_ids)
        created.departments = departments
        created = await repository.save(created)
    hydrated = await repository.get_by_id(created.id)
    if hydrated is None:
        raise NotFoundError("Position not found.")
    return hydrated


async def update_position(
    session: AsyncSession, position_id: int, payload: PositionUpsertRequest
) -> Position:
    repository = PositionRepository(session)
    position = await repository.get_by_id(position_id)
    if position is None:
        raise NotFoundError("Position not found.")
    existing = await repository.get_by_code(payload.code)
    if existing is not None and existing.id != position_id:
        raise ConflictError("Position code already exists.")
    position.title = payload.title
    position.code = payload.code.upper()
    position.salary_grade = payload.salary_grade
    position.is_active = payload.is_active
    position.departments = await _resolve_departments(session, payload.department_ids)
    saved = await repository.save(position)
    hydrated = await repository.get_by_id(saved.id)
    if hydrated is None:
        raise NotFoundError("Position not found.")
    return hydrated


async def delete_position(session: AsyncSession, position_id: int) -> None:
    repository = PositionRepository(session)
    position = await repository.get_by_id(position_id)
    if position is None:
        raise NotFoundError("Position not found.")
    await repository.delete(position)


async def list_fixed_compensations(
    session: AsyncSession, month: int | None = None, year: int | None = None
) -> list[FixedCompensation]:
    return await FixedCompensationRepository(session).list(month=month, year=year)


async def create_fixed_compensation(
    session: AsyncSession, payload: FixedCompensationUpsertRequest
) -> FixedCompensation:
    repository = FixedCompensationRepository(session)
    compensation = FixedCompensation(
        name=payload.name.strip().title(),
        amount=payload.amount,
        month=payload.month,
        year=payload.year,
    )
    created = await repository.create(compensation)
    if payload.user_ids:
        created.users = await _resolve_users(session, payload.user_ids)
        created = await repository.save(created)
    return created


async def update_fixed_compensation(
    session: AsyncSession, compensation_id: int, payload: FixedCompensationUpsertRequest
) -> FixedCompensation:
    repository = FixedCompensationRepository(session)
    compensation = await repository.get_by_id(compensation_id)
    if compensation is None:
        raise NotFoundError("Fixed compensation not found.")
    compensation.name = payload.name.strip().title()
    compensation.amount = payload.amount
    compensation.month = payload.month
    compensation.year = payload.year
    compensation.users = await _resolve_users(session, payload.user_ids)
    return await repository.save(compensation)


async def delete_fixed_compensation(session: AsyncSession, compensation_id: int) -> None:
    repository = FixedCompensationRepository(session)
    compensation = await repository.get_by_id(compensation_id)
    if compensation is None:
        raise NotFoundError("Fixed compensation not found.")
    await repository.delete(compensation)


async def update_fixed_compensation_users(
    session: AsyncSession, compensation_id: int, payload: FixedCompensationUsersRequest
) -> FixedCompensation:
    repository = FixedCompensationRepository(session)
    compensation = await repository.get_by_id(compensation_id)
    if compensation is None:
        raise NotFoundError("Fixed compensation not found.")
    compensation.users = await _resolve_users(session, payload.user_ids)
    return await repository.save(compensation)


async def _resolve_users(session: AsyncSession, user_ids: list[UUID]) -> list[User]:
    user_repository = UserRepository(session)
    users: list[User] = []
    for user_id in user_ids:
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        users.append(user)
    return users


async def get_payslips(
    session: AsyncSession,
    user_id: UUID | None = None,
    month: int | None = None,
    year: int | None = None,
    period: str | None = None,
    released: bool | None = None,
) -> list[Payslip]:
    return await PayslipRepository(session).list(
        user_id=user_id, month=month, year=year, period=period, released=released
    )


async def _current_salary_for_user(session: AsyncSession, user: User) -> tuple[str | None, Decimal | None]:
    if not user.rank or user.department_id is None:
        return None, None
    settings = await get_settings(session)
    position_code_match = _month_period_pattern().match(user.rank)
    if position_code_match is None:
        return user.rank, None
    position_code = position_code_match.group("position_code")
    rank = int(position_code_match.group("rank"))
    if rank < 1 or rank > settings.max_position_rank:
        return user.rank, None
    step = position_code_match.group("step")
    step_number = int(step) if step is not None else None
    if step_number is not None and (step_number < 1 or step_number > settings.basic_salary_steps):
        return user.rank, None
    position = await PositionRepository(session).get_by_code(position_code)
    if position is None:
        return user.rank, None
    grade = position.salary_grade + max(rank - 1, 0)
    base_salary = _salary_grade_amount(settings, grade)
    if step_number is not None:
        for _ in range(step_number):
            base_salary *= _to_decimal(settings.basic_salary_step_multiplier)
    return user.rank, base_salary.quantize(Decimal("0.01"))


async def _mp2_deduction_for_user(session: AsyncSession, user: User) -> Decimal:
    mp2 = await get_mp2(session)
    if any(mp2_user.id == user.id for mp2_user in mp2.users):
        return _to_decimal(mp2.amount).quantize(Decimal("0.01"))
    return Decimal("0.00")


async def get_or_create_payslip(
    session: AsyncSession, payload: PayslipCreateRequest
) -> Payslip:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    repository = PayslipRepository(session)
    payslip = await repository.get_by_identity(
        payload.user_id, payload.month, payload.year, payload.period
    )
    if payslip is None:
        rank, salary = await _current_salary_for_user(session, user)
        payslip = Payslip(
            user_id=payload.user_id,
            month=payload.month,
            year=payload.year,
            period=payload.period,
            rank=rank,
            salary=salary,
        )
        payslip = await repository.create(payslip)
    elif not payslip.released:
        rank, salary = await _current_salary_for_user(session, user)
        payslip.rank = rank
        payslip.salary = salary
        payslip = await repository.save(payslip)
    return payslip


async def update_payslip(
    session: AsyncSession, payslip_id: int, payload: PayslipUpdateRequest
) -> Payslip:
    repository = PayslipRepository(session)
    payslip = await repository.get_by_id(payslip_id)
    if payslip is None:
        raise NotFoundError("Payslip not found.")
    was_released = payslip.released
    if payload.rank is not None:
        payslip.rank = payload.rank
    if payload.salary is not None:
        payslip.salary = payload.salary
    if payload.released is not None:
        payslip.released = payload.released
        payslip.release_date = utc_now() if payload.released else None
    payslip = await repository.save(payslip)
    if not was_released and payslip.released:
        await create_notification_if_possible(
            session,
            recipient_id=payslip.user_id,
            content=(
                f"Your payslip for {payslip.month}/{payslip.year} "
                f"({payslip.period}) is now available."
            ),
            url=f"/my-payslips?payslip_id={payslip.id}",
        )
    return payslip


async def toggle_payslip_release(session: AsyncSession, payslip_id: int) -> Payslip:
    repository = PayslipRepository(session)
    payslip = await repository.get_by_id(payslip_id)
    if payslip is None:
        raise NotFoundError("Payslip not found.")
    payslip.released = not payslip.released
    payslip.release_date = utc_now() if payslip.released else None
    payslip = await repository.save(payslip)
    if payslip.released:
        await create_notification_if_possible(
            session,
            recipient_id=payslip.user_id,
            content=(
                f"Your payslip for {payslip.month}/{payslip.year} "
                f"({payslip.period}) is now available."
            ),
            url=f"/my-payslips?payslip_id={payslip.id}",
        )
    return payslip


def _get_config_item(settings: PayrollSetting, name: str) -> dict:
    for item in settings.deduction_config:
        if item.get("name") == name:
            return item
    return {"data": {}}


def _compute_deductions(settings: PayrollSetting, gross_pay: Decimal) -> dict[str, Decimal]:
    sss = _get_config_item(settings, "SSS").get("data", {})
    philhealth = _get_config_item(settings, "PHILHEALTH").get("data", {})
    pagibig = _get_config_item(settings, "PAG-IBIG").get("data", {})

    sss_deduction = Decimal(sss.get("min_contribution", "0"))
    philhealth_rate = _to_decimal(philhealth.get("rate"))
    philhealth_deduction = (gross_pay * philhealth_rate) / Decimal("200") if philhealth_rate else Decimal("0.00")
    tax_deduction = Decimal("0.00")
    pag_ibig_deduction = _to_decimal(pagibig.get("amount"))

    return {
        "sss": sss_deduction,
        "philhealth": philhealth_deduction.quantize(Decimal("0.01")),
        "tax": tax_deduction,
        "pag_ibig": pag_ibig_deduction.quantize(Decimal("0.01")),
    }


async def get_payslip_summary(session: AsyncSession, payslip_id: int) -> dict:
    repository = PayslipRepository(session)
    payslip = await repository.get_by_id(payslip_id)
    if payslip is None:
        raise NotFoundError("Payslip not found.")
    settings = await get_settings(session)
    fixed_compensations = await FixedCompensationRepository(session).list(
        month=payslip.month, year=payslip.year
    )
    base_salary = _to_decimal(payslip.salary)
    fixed_total = sum(
        (_to_decimal(comp.amount) / Decimal("2") for comp in fixed_compensations if payslip.user in comp.users),
        Decimal("0.00"),
    )
    variable_compensations = payslip.variable_compensations
    variable_deductions = payslip.variable_deductions
    variable_comp_total = sum((_to_decimal(item.amount) for item in variable_compensations), Decimal("0.00"))
    variable_ded_total = sum((_to_decimal(item.amount) for item in variable_deductions), Decimal("0.00"))
    gross_pay = base_salary + fixed_total + variable_comp_total
    gross_per_cutoff = gross_pay / Decimal("2")
    mandatory = _compute_deductions(settings, gross_pay)
    mandatory_total = sum(mandatory.values(), Decimal("0.00"))
    mp2_deduction = await _mp2_deduction_for_user(session, payslip.user)
    total_deductions = variable_ded_total
    if payslip.period == "2ND":
        total_deductions += mandatory_total + mp2_deduction
    return {
        "period": payslip.period,
        "salary": base_salary / Decimal("2") if base_salary else None,
        "compensations": fixed_compensations,
        "variable_compensations": variable_compensations,
        "gross_pay": gross_per_cutoff.quantize(Decimal("0.01")),
        "variable_deductions": variable_deductions,
        "total_deductions": total_deductions.quantize(Decimal("0.01")),
        "net_salary": (gross_per_cutoff - total_deductions).quantize(Decimal("0.01")),
        "sss_deduction": mandatory["sss"],
        "philhealth_deduction": mandatory["philhealth"],
        "pag_ibig_deduction": mandatory["pag_ibig"],
        "mp2_deduction": mp2_deduction,
        "tax_deduction": mandatory["tax"],
    }


async def add_payslip_variable_compensation(
    session: AsyncSession,
    payslip_id: int,
    payload: PayslipVariableCompensationUpsertRequest,
) -> PayslipVariableCompensation:
    repository = PayslipVariableCompensationRepository(session)
    payslip = await PayslipRepository(session).get_by_id(payslip_id)
    if payslip is None:
        raise NotFoundError("Payslip not found.")
    item = PayslipVariableCompensation(
        payslip_id=payslip_id, name=payload.name.strip(), amount=payload.amount
    )
    return await repository.create(item)


async def remove_payslip_variable_compensation(
    session: AsyncSession, item_id: int
) -> None:
    repository = PayslipVariableCompensationRepository(session)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise NotFoundError("Variable compensation not found.")
    await repository.delete(item)


async def add_payslip_variable_deduction(
    session: AsyncSession,
    payslip_id: int,
    payload: PayslipVariableDeductionUpsertRequest,
) -> PayslipVariableDeduction:
    repository = PayslipVariableDeductionRepository(session)
    payslip = await PayslipRepository(session).get_by_id(payslip_id)
    if payslip is None:
        raise NotFoundError("Payslip not found.")
    item = PayslipVariableDeduction(
        payslip_id=payslip_id, name=payload.name.strip(), amount=payload.amount
    )
    return await repository.create(item)


async def remove_payslip_variable_deduction(
    session: AsyncSession, item_id: int
) -> None:
    repository = PayslipVariableDeductionRepository(session)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise NotFoundError("Variable deduction not found.")
    await repository.delete(item)


async def list_thirteenth_month_pays(
    session: AsyncSession,
    user_id: UUID | None = None,
    month: int | None = None,
    year: int | None = None,
    released: bool | None = None,
) -> list[ThirteenthMonthPay]:
    return await ThirteenthMonthPayRepository(session).list(
        user_id=user_id, month=month, year=year, released=released
    )


async def create_thirteenth_month_pay(
    session: AsyncSession, payload: ThirteenthMonthPayCreateRequest
) -> ThirteenthMonthPay:
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    repository = ThirteenthMonthPayRepository(session)
    existing = await repository.get_by_identity(payload.user_id, payload.month, payload.year)
    if existing is not None:
        raise ConflictError("13th month pay record already exists.")
    item = ThirteenthMonthPay(
        user_id=payload.user_id,
        amount=payload.amount,
        month=payload.month,
        year=payload.year,
    )
    return await repository.create(item)


async def update_thirteenth_month_pay(
    session: AsyncSession, item_id: int, payload: ThirteenthMonthPayUpdateRequest
) -> ThirteenthMonthPay:
    repository = ThirteenthMonthPayRepository(session)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise NotFoundError("13th month pay not found.")
    was_released = item.released
    if payload.amount is not None:
        item.amount = payload.amount
    if payload.released is not None:
        item.released = payload.released
        item.release_date = utc_now() if payload.released else None
    item = await repository.save(item)
    if not was_released and item.released:
        await create_notification_if_possible(
            session,
            recipient_id=item.user_id,
            content=f"Your 13th month pay for {item.month}/{item.year} is now available.",
            url=f"/my-payslips?thirteenth_month_pay_id={item.id}",
        )
    return item


async def toggle_thirteenth_month_pay_release(
    session: AsyncSession, item_id: int
) -> ThirteenthMonthPay:
    repository = ThirteenthMonthPayRepository(session)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise NotFoundError("13th month pay not found.")
    item.released = not item.released
    item.release_date = utc_now() if item.released else None
    item = await repository.save(item)
    if item.released:
        await create_notification_if_possible(
            session,
            recipient_id=item.user_id,
            content=f"Your 13th month pay for {item.month}/{item.year} is now available.",
            url=f"/my-payslips?thirteenth_month_pay_id={item.id}",
        )
    return item


async def delete_thirteenth_month_pay(session: AsyncSession, item_id: int) -> None:
    repository = ThirteenthMonthPayRepository(session)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise NotFoundError("13th month pay not found.")
    await repository.delete(item)


async def add_thirteenth_month_pay_variable_deduction(
    session: AsyncSession,
    item_id: int,
    payload: ThirteenthMonthPayVariableDeductionUpsertRequest,
) -> ThirteenthMonthPayVariableDeduction:
    repository = ThirteenthMonthPayVariableDeductionRepository(session)
    pay = await ThirteenthMonthPayRepository(session).get_by_id(item_id)
    if pay is None:
        raise NotFoundError("13th month pay not found.")
    item = ThirteenthMonthPayVariableDeduction(
        thirteenth_month_pay_id=item_id,
        name=payload.name.strip(),
        amount=payload.amount,
    )
    return await repository.create(item)


async def remove_thirteenth_month_pay_variable_deduction(
    session: AsyncSession, item_id: int
) -> None:
    repository = ThirteenthMonthPayVariableDeductionRepository(session)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise NotFoundError("13th month pay variable deduction not found.")
    await repository.delete(item)
