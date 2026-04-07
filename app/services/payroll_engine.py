from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.payroll import (
    FixedCompensationRepository,
    PayrollPolicyRuleRepository,
    PayrollPolicyVersionRepository,
    PayrollRunInputRepository,
    PayslipRepository,
)
from app.schemas.payroll import (
    PayrollComputationRead,
    PayslipSummaryComparisonRead,
    PayslipSummaryRead,
)
from app.services.payroll import (
    get_active_mp2_for_user,
    get_payslip_summary,
    resolve_mp2_effective_date,
)


PH_POLICY_KEY = "PH_STATUTORY"


def _to_decimal(value: Decimal | int | str | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _decimal_attr(rule: object, *names: str, default: Decimal | int | str | float | None = None) -> Decimal:
    for name in names:
        if hasattr(rule, name):
            return _to_decimal(getattr(rule, name))
    return _to_decimal(default)


def _optional_decimal_attr(rule: object, *names: str) -> Decimal | None:
    for name in names:
        if hasattr(rule, name):
            value = getattr(rule, name)
            return _to_decimal(value) if value is not None else None
    return None


def _pick_rule_by_compensation(rules: list[object], compensation: Decimal):
    if not rules:
        return None

    for rule in rules:
        min_compensation = _decimal_attr(
            rule,
            "compensation_range_from",
            "min_compensation",
            default=0,
        )
        max_value = _optional_decimal_attr(
            rule,
            "compensation_range_to",
            "max_compensation",
        )
        if compensation >= min_compensation and (
            max_value is None or compensation <= max_value
        ):
            return rule

    eligible = [
        rule
        for rule in rules
        if compensation >= _decimal_attr(
            rule,
            "compensation_range_from",
            "min_compensation",
            default=0,
        )
    ]
    if eligible:
        return max(
            eligible,
            key=lambda item: _decimal_attr(
                item,
                "compensation_range_from",
                "min_compensation",
                default=0,
            ),
        )
    return min(
        rules,
        key=lambda item: _decimal_attr(
            item,
            "compensation_range_from",
            "min_compensation",
            default=0,
        ),
    )


def _compute_sss_deduction(gross_pay: Decimal, sss_brackets: list[object]) -> Decimal:
    rule = _pick_rule_by_compensation(sss_brackets, gross_pay)
    if rule is None:
        return Decimal("0.00")
    regular = _decimal_attr(rule, "employee_contribution", "employee_share", default=0)
    mpf = _decimal_attr(rule, "mpf_employee_contribution", default=0)
    return _quantize(regular + mpf)


def _compute_philhealth_deduction(gross_pay: Decimal, philhealth_rules: list[object]) -> Decimal:
    rule = _pick_rule_by_compensation(philhealth_rules, gross_pay)
    if rule is None:
        return Decimal("0.00")

    min_compensation = _decimal_attr(
        rule,
        "compensation_range_from",
        "min_compensation",
        default=0,
    )
    max_compensation = _optional_decimal_attr(
        rule,
        "compensation_range_to",
        "max_compensation",
    )
    premium_base = gross_pay
    if premium_base < min_compensation:
        premium_base = min_compensation
    if max_compensation is not None and premium_base > max_compensation:
        premium_base = max_compensation

    rate = _decimal_attr(rule, "premium_rate", "rate", default=0)
    employee_share_ratio = _to_decimal(getattr(rule, "employee_share_ratio", 0))
    return _quantize(premium_base * rate * employee_share_ratio)


def _compute_pagibig_deduction(gross_pay: Decimal, pagibig_rules: list[object]) -> Decimal:
    applicable = [
        rule
        for rule in pagibig_rules
        if gross_pay >= _decimal_attr(
            rule,
            "compensation_range_from",
            "min_compensation",
            default=0,
        )
    ]
    if applicable:
        rule = max(
            applicable,
            key=lambda item: _decimal_attr(
                item,
                "compensation_range_from",
                "min_compensation",
                default=0,
            ),
        )
    elif pagibig_rules:
        rule = min(
            pagibig_rules,
            key=lambda item: _decimal_attr(
                item,
                "compensation_range_from",
                "min_compensation",
                default=0,
            ),
        )
    else:
        return Decimal("0.00")

    cap = _decimal_attr(rule, "compensation_cap", "monthly_compensation_cap", default=0)
    employee_rate = _to_decimal(getattr(rule, "employee_rate", 0))
    deduction = min(gross_pay, cap) * employee_rate

    max_employee_share = getattr(rule, "employee_share_cap", getattr(rule, "max_employee_share", None))
    if max_employee_share is not None:
        deduction = min(deduction, _to_decimal(max_employee_share))
    return _quantize(deduction)


def _compute_tax_deduction(gross_per_cutoff: Decimal, bir_brackets: list[object]) -> Decimal:
    semi_monthly_brackets = [
        rule for rule in bir_brackets if getattr(rule, "payroll_period", "") == "SEMI_MONTHLY"
    ]
    if not semi_monthly_brackets:
        return Decimal("0.00")

    rule = _pick_rule_by_compensation(semi_monthly_brackets, gross_per_cutoff)
    if rule is None:
        return Decimal("0.00")

    base_tax = _to_decimal(getattr(rule, "base_tax", 0))
    marginal_rate = _to_decimal(getattr(rule, "marginal_rate", 0))
    over_amount = _decimal_attr(rule, "excess_over", "over_amount", default=0)
    taxable_excess = max(gross_per_cutoff - over_amount, Decimal("0.00"))
    return _quantize(base_tax + (taxable_excess * marginal_rate))


async def _resolve_policy_version_id_for_payslip(
    session: AsyncSession,
    payslip_id: int,
    payslip_month: int | None,
    payslip_year: int | None,
    policy_version_id: int | None,
) -> int:
    version_repository = PayrollPolicyVersionRepository(session)

    if policy_version_id is not None:
        version = await version_repository.get_by_id(policy_version_id)
        if version is None:
            raise NotFoundError("Payroll policy version not found.")
        return version.id

    if payslip_month is None or payslip_year is None:
        raise ConflictError("Payslip period is required to resolve policy version.")

    effective_date = date(payslip_year, payslip_month, 1)
    version = await version_repository.get_active_effective(
        PH_POLICY_KEY,
        effective_date,
    )
    if version is None:
        raise ConflictError("No active payroll policy version is configured for this payslip period.")
    return version.id


async def _compute_mandatory_deductions_from_policy(
    session: AsyncSession,
    gross_pay: Decimal,
    gross_per_cutoff: Decimal,
    policy_version_id: int,
) -> dict[str, Decimal]:
    policy_rules = await PayrollPolicyRuleRepository(session).get_policy_rules(policy_version_id)
    sss_brackets = policy_rules["sss_brackets"]
    philhealth_rules = policy_rules["philhealth_rules"]
    pagibig_rules = policy_rules["pagibig_rules"]
    bir_brackets = policy_rules["bir_withholding_brackets"]

    return {
        "sss": _compute_sss_deduction(gross_pay, sss_brackets),
        "philhealth": _compute_philhealth_deduction(gross_pay, philhealth_rules),
        "pag_ibig": _compute_pagibig_deduction(gross_pay, pagibig_rules),
        "tax": _compute_tax_deduction(gross_per_cutoff, bir_brackets),
    }


async def _compute_mp2_deduction_for_user(
    session: AsyncSession,
    user_id,
    effective_date: date,
) -> Decimal:
    enrollment = await get_active_mp2_for_user(session, user_id, effective_date)
    if enrollment is not None:
        return _to_decimal(enrollment.amount).quantize(Decimal("0.01"))
    return Decimal("0.00")


async def compute_payslip_summary_v2(
    session: AsyncSession,
    payslip_id: int,
    policy_version_id: int | None = None,
    payroll_run_id: int | None = None,
    include_unapproved_run_inputs: bool = False,
) -> PayrollComputationRead:
    payslip = await PayslipRepository(session).get_by_id(payslip_id)
    if payslip is None:
        raise NotFoundError("Payslip not found.")

    resolved_policy_version_id = await _resolve_policy_version_id_for_payslip(
        session,
        payslip.id,
        payslip.month,
        payslip.year,
        policy_version_id,
    )
    fixed_compensations = await FixedCompensationRepository(session).list(
        month=payslip.month, year=payslip.year
    )

    base_salary = _to_decimal(payslip.salary)
    fixed_total = sum(
        (_to_decimal(comp.amount) / Decimal("2") for comp in fixed_compensations if payslip.user in comp.users),
        Decimal("0.00"),
    )
    if payroll_run_id is not None:
        run_inputs = await PayrollRunInputRepository(session).list_for_run_user(
            payroll_run_id,
            payslip.user_id,
            approved_only=not include_unapproved_run_inputs,
        )
        variable_comp_total = sum(
            (_to_decimal(item.amount) for item in run_inputs if item.item_type.category == "earning"),
            Decimal("0.00"),
        )
        variable_ded_total = sum(
            (_to_decimal(item.amount) for item in run_inputs if item.item_type.category == "deduction"),
            Decimal("0.00"),
        )
    else:
        variable_comp_total = sum(
            (_to_decimal(item.amount) for item in payslip.variable_compensations),
            Decimal("0.00"),
        )
        variable_ded_total = sum(
            (_to_decimal(item.amount) for item in payslip.variable_deductions),
            Decimal("0.00"),
        )

    gross_pay = base_salary + fixed_total + variable_comp_total
    gross_per_cutoff = (gross_pay / Decimal("2")).quantize(Decimal("0.01"))
    mandatory = await _compute_mandatory_deductions_from_policy(
        session,
        gross_pay,
        gross_per_cutoff,
        resolved_policy_version_id,
    )
    mandatory_total = sum(mandatory.values(), Decimal("0.00"))
    effective_date = resolve_mp2_effective_date(payslip.month, payslip.year, payslip.period)
    mp2_deduction = await _compute_mp2_deduction_for_user(
        session,
        payslip.user_id,
        effective_date,
    )

    # Existing behavior applies mandatory deductions on second cutoff only.
    total_deductions = variable_ded_total
    notes: list[str] = []
    if payslip.period == "2ND":
        total_deductions += mandatory_total + mp2_deduction
    elif mp2_deduction > Decimal("0.00"):
        notes.append("MP2 deduction skipped for non-second cutoff period.")

    total_deductions = total_deductions.quantize(Decimal("0.01"))
    net_pay = (gross_per_cutoff - total_deductions).quantize(Decimal("0.01"))

    return PayrollComputationRead(
        gross_pay=gross_per_cutoff,
        total_deductions=total_deductions,
        net_pay=net_pay,
        mandatory_deductions=mandatory,
        variable_deductions=variable_ded_total.quantize(Decimal("0.01")),
        mp2_deduction=mp2_deduction,
        included_in_total_deductions=True,
        notes=notes,
    )


async def compare_payslip_summary(
    session: AsyncSession,
    payslip_id: int,
) -> PayslipSummaryComparisonRead:
    legacy_raw = await get_payslip_summary(session, payslip_id)
    legacy_summary = PayslipSummaryRead.model_validate(legacy_raw)
    new_summary = await compute_payslip_summary_v2(session, payslip_id)

    legacy_gross = _to_decimal(legacy_summary.gross_pay)
    legacy_total_deductions = _to_decimal(legacy_summary.total_deductions)
    legacy_net = _to_decimal(legacy_summary.net_salary)

    return PayslipSummaryComparisonRead(
        payslip_id=payslip_id,
        legacy_summary=legacy_summary,
        new_engine=new_summary,
        differences={
            "gross_pay": (new_summary.gross_pay - legacy_gross).quantize(Decimal("0.01")),
            "total_deductions": (
                new_summary.total_deductions - legacy_total_deductions
            ).quantize(Decimal("0.01")),
            "net_pay": (new_summary.net_pay - legacy_net).quantize(Decimal("0.01")),
        },
    )
