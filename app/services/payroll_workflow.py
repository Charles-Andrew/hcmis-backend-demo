from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.models.payroll import (
    PayrollRunInputAudit,
    PayrollRunInput,
    PayrollPolicyVersion,
    PayrollRun,
    PayrollRunItem,
)
from app.repositories.payroll import (
    PayrollRunInputAuditRepository,
    PayrollRunInputRepository,
    PayrollPolicyRuleRepository,
    PayrollPolicySourceRepository,
    PayrollPolicyVersionRepository,
    PayrollRunItemRepository,
    PayrollRunRepository,
    PayslipVariableCompensationRepository,
    PayslipVariableDeductionRepository,
    PayslipRepository,
)
from app.schemas.payroll import (
    PayrollPolicySourcesDetailRead,
    PayrollPolicySourcesUpdateRequest,
    PayrollPolicyOfficialSeedRequest,
    PayrollPolicyDetailRead,
    PayrollPolicyRulesRead,
    PayrollPolicyRulesUpdateRequest,
    PayrollPolicySeedRequest,
    PayrollPolicySourceRead,
    PayrollPolicyVersionCreateRequest,
    PayrollPolicyVersionRead,
    PayrollRunCreateRequest,
)
from app.services.payroll_engine import compute_payslip_summary_v2


PH_POLICY_KEY = "PH_STATUTORY"
PH_OFFICIAL_POLICY_BASELINE_EFFECTIVE_FROM = date(2025, 1, 1)
SSS_2025_EFFECTIVE_FROM = date(2025, 1, 1)
PHILHEALTH_5_PERCENT_EFFECTIVE_FROM = date(2024, 1, 1)
PAGIBIG_MAX_FUND_SALARY_10K_EFFECTIVE_FROM = date(2024, 2, 1)
PAGIBIG_MEMBERSHIP_GUIDELINES_EFFECTIVE_FROM = date(2010, 1, 1)
BIR_ANNEX_E_2023_EFFECTIVE_FROM = date(2023, 1, 1)
NCR_WAGE_ORDER_26_EFFECTIVE_FROM = date(2025, 7, 18)

SSS_2025_TABLE_URL = "https://www.sss.gov.ph/wp-content/uploads/2024/12/2025-SSS-Contribution-Table-rev.pdf"
SSS_EC_PROGRAM_URL = "https://www.sss.gov.ph/employees-compensation-program/"
PHILHEALTH_CONTRIBUTION_TABLE_URL = (
    "https://www.philhealth.gov.ph/partners/employers/ContributionTable_v2.pdf"
)
PAGIBIG_MEMBERSHIP_CIRCULAR_URL = (
    "https://www.pagibigfund.gov.ph/document/pdf/circulars/provident/"
    "HDMF%20Circular%20No.%20274%20-%20Revised%20Guidelines%20on%20Pag-IBIG%20Fund%20Membership.pdf"
)
PAGIBIG_PAYMENT_GUIDE_URL = (
    "https://www.pagibigfund.gov.ph/document/pdf/payments/"
    "AcceptingPagIBIGPaymentsThroughOTC_24%20JAN%202025.pdf"
)
BIR_ANNEX_E_URL = "https://bir-cdn.bir.gov.ph/local/pdf/Annex%20E%20RR%2011-2018.pdf"
NWPC_NCR_26_URL = "https://nwpc.dole.gov.ph/wp-content/uploads/2025/06/01.-Wage-Order-No.-NCR-26.pdf"


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    return value


async def list_policy_versions(
    session: AsyncSession,
    policy_key: str | None = None,
) -> list[PayrollPolicyVersion]:
    return await PayrollPolicyVersionRepository(session).list(policy_key=policy_key)


async def create_policy_version(
    session: AsyncSession,
    payload: PayrollPolicyVersionCreateRequest,
) -> PayrollPolicyVersion:
    repository = PayrollPolicyVersionRepository(session)
    existing = await repository.get_by_identity(payload.policy_key, payload.version_label)
    if existing is not None:
        raise ConflictError("Policy version already exists.")
    item = PayrollPolicyVersion(
        policy_key=payload.policy_key,
        version_label=payload.version_label,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        is_active=payload.is_active,
    )
    return await repository.create(item)


async def delete_policy_version(
    session: AsyncSession,
    policy_version_id: int,
) -> None:
    version_repository = PayrollPolicyVersionRepository(session)
    rule_repository = PayrollPolicyRuleRepository(session)
    version = await version_repository.get_by_id(policy_version_id)
    if version is None:
        raise NotFoundError("Payroll policy version not found.")
    if version.is_active:
        raise ConflictError("Cannot delete an active payroll policy version.")

    payroll_run = (
        await session.execute(
            select(PayrollRun.id).where(PayrollRun.policy_version_id == policy_version_id).limit(1)
        )
    ).scalar_one_or_none()
    if payroll_run is not None:
        raise ConflictError(
            "Cannot delete a payroll policy version that is already linked to payroll runs."
        )

    await rule_repository.clear_policy_rules(policy_version_id)
    await PayrollPolicySourceRepository(session).replace(
        policy_version_id,
        [],
        applied_by=None,
        applied_at=utc_now(),
    )
    await version_repository.delete(version)


async def activate_policy_version(
    session: AsyncSession,
    policy_version_id: int,
) -> PayrollPolicyVersion:
    version_repository = PayrollPolicyVersionRepository(session)
    version = await version_repository.get_by_id(policy_version_id)
    if version is None:
        raise NotFoundError("Payroll policy version not found.")

    versions = await version_repository.list(policy_key=version.policy_key)
    for item in versions:
        item.is_active = item.id == version.id

    return await version_repository.save(version)


async def seed_ph_policy_baseline(
    session: AsyncSession,
    payload: PayrollPolicySeedRequest,
) -> PayrollPolicyVersion:
    version_repository = PayrollPolicyVersionRepository(session)
    rule_repository = PayrollPolicyRuleRepository(session)
    existing = await version_repository.get_by_identity(PH_POLICY_KEY, payload.version_label)

    if existing is not None and not payload.overwrite_existing:
        raise ConflictError("Policy version already exists. Set overwrite_existing to replace seed data.")

    if existing is None:
        existing = await version_repository.create(
            PayrollPolicyVersion(
                policy_key=PH_POLICY_KEY,
                version_label=payload.version_label,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
                is_active=False,
            )
        )
    else:
        existing.effective_from = payload.effective_from
        existing.effective_to = payload.effective_to
        existing.is_active = False
        existing = await version_repository.save(existing)
        await rule_repository.clear_policy_rules(existing.id)

    await rule_repository.seed_ph_baseline(existing.id)
    return existing


def _build_sss_employee_brackets_2025() -> list[dict[str, Decimal | str | None]]:
    brackets: list[dict[str, Decimal | str | None]] = []
    salary_credits = list(range(5000, 35001, 500))
    for index, msc in enumerate(salary_credits):
        if index == 0:
            min_comp = Decimal("0.00")
            max_comp = Decimal("5249.99")
        elif msc < 35000:
            min_comp = Decimal(msc - 250)
            max_comp = Decimal(f"{msc + 249}.99")
        else:
            min_comp = Decimal("34750.00")
            max_comp = Decimal("999999.99")

        regular_employee = (Decimal(min(msc, 20000)) * Decimal("0.05")).quantize(
            Decimal("0.01")
        )
        mpf_employee = (
            Decimal(max(msc - 20000, 0)) * Decimal("0.05")
        ).quantize(Decimal("0.01"))
        regular_employer = (Decimal(min(msc, 20000)) * Decimal("0.10")).quantize(
            Decimal("0.01")
        )
        mpf_employer = (
            Decimal(max(msc - 20000, 0)) * Decimal("0.10")
        ).quantize(Decimal("0.01"))
        ec_contribution = Decimal("10.00") if msc < 15000 else Decimal("30.00")
        brackets.append(
            {
                "compensation_range_from": min_comp,
                "compensation_range_to": max_comp,
                "monthly_salary_credit": Decimal(msc).quantize(Decimal("0.01")),
                "employee_contribution": regular_employee,
                "employer_contribution": regular_employer,
                "ec_contribution": ec_contribution,
                "mpf_employee_contribution": mpf_employee,
                "mpf_employer_contribution": mpf_employer,
                "source_reference": "SSS Circular No. 2024-006 / 2025 table",
            }
        )
    return brackets


def _build_bir_annex_e_semi_monthly_brackets() -> list[dict[str, Decimal | str | None]]:
    return [
        {
            "payroll_period": "SEMI_MONTHLY",
            "compensation_range_from": Decimal("0.00"),
            "compensation_range_to": Decimal("10416.99"),
            "base_tax": Decimal("0.00"),
            "marginal_rate": Decimal("0.00"),
            "excess_over": Decimal("0.00"),
            "source_reference": "RR No. 11-2018 Annex E",
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "compensation_range_from": Decimal("10417.00"),
            "compensation_range_to": Decimal("16666.99"),
            "base_tax": Decimal("0.00"),
            "marginal_rate": Decimal("0.15"),
            "excess_over": Decimal("10417.00"),
            "source_reference": "RR No. 11-2018 Annex E",
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "compensation_range_from": Decimal("16667.00"),
            "compensation_range_to": Decimal("33332.99"),
            "base_tax": Decimal("937.50"),
            "marginal_rate": Decimal("0.20"),
            "excess_over": Decimal("16667.00"),
            "source_reference": "RR No. 11-2018 Annex E",
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "compensation_range_from": Decimal("33333.00"),
            "compensation_range_to": Decimal("83332.99"),
            "base_tax": Decimal("4270.70"),
            "marginal_rate": Decimal("0.25"),
            "excess_over": Decimal("33333.00"),
            "source_reference": "RR No. 11-2018 Annex E",
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "compensation_range_from": Decimal("83333.00"),
            "compensation_range_to": Decimal("333332.99"),
            "base_tax": Decimal("16770.70"),
            "marginal_rate": Decimal("0.30"),
            "excess_over": Decimal("83333.00"),
            "source_reference": "RR No. 11-2018 Annex E",
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "compensation_range_from": Decimal("333333.00"),
            "compensation_range_to": None,
            "base_tax": Decimal("91770.70"),
            "marginal_rate": Decimal("0.35"),
            "excess_over": Decimal("333333.00"),
            "source_reference": "RR No. 11-2018 Annex E",
        },
    ]


def _build_philhealth_active_rules() -> list[dict[str, Decimal | str | None]]:
    return [
        {
            "compensation_range_from": Decimal("10000.00"),
            "compensation_range_to": Decimal("100000.00"),
            "premium_rate": Decimal("0.05"),
            "employee_share_ratio": Decimal("0.50"),
            "employer_share_ratio": Decimal("0.50"),
            "source_reference": "PhilHealth Contribution Table (5.00%)",
        }
    ]


def _build_pagibig_active_rules() -> list[dict[str, Decimal | str | None]]:
    return [
        {
            "compensation_range_from": Decimal("0.00"),
            "compensation_range_to": Decimal("1500.00"),
            "compensation_cap": Decimal("1500.00"),
            "employee_rate": Decimal("0.01"),
            "employer_rate": Decimal("0.02"),
            "employee_share_cap": None,
            "employer_share_cap": None,
            "source_reference": "HDMF Circular No. 274 + 2025 payment guide",
        },
        {
            "compensation_range_from": Decimal("1500.01"),
            "compensation_range_to": None,
            "compensation_cap": Decimal("10000.00"),
            "employee_rate": Decimal("0.02"),
            "employer_rate": Decimal("0.02"),
            "employee_share_cap": Decimal("200.00"),
            "employer_share_cap": Decimal("200.00"),
            "source_reference": "HDMF Circular No. 274 + 2025 payment guide",
        },
    ]


def _build_ncr_minimum_wage_orders_active() -> list[dict[str, Any]]:
    return [
        {
            "region_code": "NCR",
            "sector": "NON_AGRI",
            "daily_rate": Decimal("695.00"),
            "effective_from": NCR_WAGE_ORDER_26_EFFECTIVE_FROM,
            "effective_to": None,
            "source_reference": "WO No. NCR-26",
        },
        {
            "region_code": "NCR",
            "sector": "AGRI_SRVC_RTL15_MFG_LT10",
            "daily_rate": Decimal("658.00"),
            "effective_from": NCR_WAGE_ORDER_26_EFFECTIVE_FROM,
            "effective_to": None,
            "source_reference": "WO No. NCR-26",
        },
    ]


async def seed_ph_policy_official_core(
    session: AsyncSession,
    payload: PayrollPolicyOfficialSeedRequest,
) -> PayrollPolicyVersion:
    version_repository = PayrollPolicyVersionRepository(session)
    rule_repository = PayrollPolicyRuleRepository(session)
    existing = await version_repository.get_by_identity(PH_POLICY_KEY, payload.version_label)

    if existing is not None and not payload.overwrite_existing:
        raise ConflictError("Policy version already exists. Set overwrite_existing to replace seed data.")

    if existing is None:
        existing = await version_repository.create(
            PayrollPolicyVersion(
                policy_key=PH_POLICY_KEY,
                version_label=payload.version_label,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
                is_active=False,
            )
        )
    else:
        existing.effective_from = payload.effective_from
        existing.effective_to = payload.effective_to
        existing.is_active = False
        existing = await version_repository.save(existing)

    # Core PH statutory rates seeded from official circular frameworks.
    await rule_repository.replace_policy_rules(
        existing.id,
        {
            "sss_brackets": _build_sss_employee_brackets_2025(),
            "philhealth_rules": _build_philhealth_active_rules(),
            "pagibig_rules": _build_pagibig_active_rules(),
            "bir_withholding_brackets": _build_bir_annex_e_semi_monthly_brackets(),
            "minimum_wage_orders": _build_ncr_minimum_wage_orders_active(),
        },
    )
    await PayrollPolicySourceRepository(session).replace(
        existing.id,
        _official_core_sources(payload.effective_from, payload.effective_to),
        applied_by=None,
        applied_at=utc_now(),
    )
    return existing


async def get_policy_version_rules(
    session: AsyncSession,
    policy_version_id: int,
) -> PayrollPolicyDetailRead:
    version = await PayrollPolicyVersionRepository(session).get_by_id(policy_version_id)
    if version is None:
        raise NotFoundError("Payroll policy version not found.")
    rules = await PayrollPolicyRuleRepository(session).get_policy_rules(policy_version_id)
    return PayrollPolicyDetailRead(
        version=PayrollPolicyVersionRead.model_validate(version),
        rules=PayrollPolicyRulesRead.model_validate(rules),
    )


async def update_policy_version_rules(
    session: AsyncSession,
    policy_version_id: int,
    payload: PayrollPolicyRulesUpdateRequest,
) -> PayrollPolicyDetailRead:
    version = await PayrollPolicyVersionRepository(session).get_by_id(policy_version_id)
    if version is None:
        raise NotFoundError("Payroll policy version not found.")
    await PayrollPolicyRuleRepository(session).replace_policy_rules(
        policy_version_id,
        payload.model_dump(),
    )
    return await get_policy_version_rules(session, policy_version_id)


async def get_policy_version_sources(
    session: AsyncSession,
    policy_version_id: int,
) -> PayrollPolicySourcesDetailRead:
    version = await PayrollPolicyVersionRepository(session).get_by_id(policy_version_id)
    if version is None:
        raise NotFoundError("Payroll policy version not found.")
    sources = await PayrollPolicySourceRepository(session).list(policy_version_id)
    return PayrollPolicySourcesDetailRead(
        version=PayrollPolicyVersionRead.model_validate(version),
        sources=[PayrollPolicySourceRead.model_validate(item) for item in sources],
    )


async def update_policy_version_sources(
    session: AsyncSession,
    policy_version_id: int,
    payload: PayrollPolicySourcesUpdateRequest,
    applied_by: UUID | None,
) -> PayrollPolicySourcesDetailRead:
    version = await PayrollPolicyVersionRepository(session).get_by_id(policy_version_id)
    if version is None:
        raise NotFoundError("Payroll policy version not found.")
    await PayrollPolicySourceRepository(session).replace(
        policy_version_id,
        payload.model_dump()["sources"],
        applied_by=applied_by,
        applied_at=utc_now(),
    )
    return await get_policy_version_sources(session, policy_version_id)


async def list_payroll_runs(
    session: AsyncSession,
    month: int | None = None,
    year: int | None = None,
) -> list[PayrollRun]:
    return await PayrollRunRepository(session).list(month=month, year=year)


async def create_payroll_run(
    session: AsyncSession,
    payload: PayrollRunCreateRequest,
    created_by: UUID | None,
) -> PayrollRun:
    repository = PayrollRunRepository(session)
    existing = await repository.get_by_identity(payload.month, payload.year, payload.period)
    if existing is not None:
        raise ConflictError("Payroll run for this period already exists.")
    policy = await PayrollPolicyVersionRepository(session).get_by_id(
        payload.policy_version_id
    )
    if policy is None:
        raise NotFoundError("Payroll policy version not found.")
    if not policy.is_active:
        raise ConflictError("Selected payroll policy version is not active.")
    item = PayrollRun(
        month=payload.month,
        year=payload.year,
        period=payload.period,
        policy_version_id=payload.policy_version_id,
        created_by=created_by,
        status="DRAFT",
    )
    return await repository.create(item)


async def validate_payroll_run(session: AsyncSession, payroll_run_id: int) -> PayrollRun:
    run_repository = PayrollRunRepository(session)
    item_repository = PayrollRunItemRepository(session)
    payslip_repository = PayslipRepository(session)

    payroll_run = await run_repository.get_by_id(payroll_run_id)
    if payroll_run is None:
        raise NotFoundError("Payroll run not found.")
    if payroll_run.status not in {"DRAFT", "VALIDATED"}:
        raise ConflictError("Only draft or validated runs can be validated.")
    if payroll_run.policy_version_id is None:
        raise ConflictError("Payroll run policy version is required.")

    payslips = await payslip_repository.list(
        month=payroll_run.month,
        year=payroll_run.year,
        period=payroll_run.period,
    )
    if not payslips:
        raise ConflictError("No payslips found for this payroll run period.")

    await item_repository.clear(payroll_run.id)

    run_items: list[PayrollRunItem] = []
    for payslip in payslips:
        summary = await compute_payslip_summary_v2(
            session,
            payslip.id,
            policy_version_id=payroll_run.policy_version_id,
            payroll_run_id=payroll_run.id,
            include_unapproved_run_inputs=True,
        )
        run_items.append(
            PayrollRunItem(
                payroll_run_id=payroll_run.id,
                user_id=payslip.user_id,
                payslip_id=payslip.id,
                gross_pay=summary.gross_pay,
                total_deductions=summary.total_deductions,
                net_pay=summary.net_pay,
                breakdown=_to_json_safe(summary.model_dump()),
                status="READY",
            )
        )
    await item_repository.create_many(run_items)

    payroll_run.status = "VALIDATED"
    payroll_run.started_at = payroll_run.started_at or utc_now()
    return await run_repository.save(payroll_run)


async def approve_payroll_run(
    session: AsyncSession,
    payroll_run_id: int,
    approved_by: UUID | None,
) -> PayrollRun:
    run_repository = PayrollRunRepository(session)
    input_repository = PayrollRunInputRepository(session)
    payroll_run = await run_repository.get_by_id(payroll_run_id)
    if payroll_run is None:
        raise NotFoundError("Payroll run not found.")
    if payroll_run.status != "VALIDATED":
        raise ConflictError("Only validated runs can be approved.")

    run_inputs = await input_repository.list(payroll_run.id)
    audit_repository = PayrollRunInputAuditRepository(session)
    approval_time = utc_now()
    for run_input in run_inputs:
        run_input.status = "approved"
        run_input.approved_by = approved_by
        run_input.approved_at = approval_time
    if run_inputs:
        await session.commit()
        for run_input in run_inputs:
            await audit_repository.create(
                PayrollRunInputAudit(
                    payroll_run_input_id=run_input.id,
                    action="approved",
                    actor_id=approved_by,
                    payload_json={
                        "status": "approved",
                        "approved_at": approval_time.isoformat(),
                    },
                )
            )

    payroll_run.status = "APPROVED"
    return await run_repository.save(payroll_run)


def _build_snapshot_payloads(run_inputs: list[PayrollRunInput]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    earning_items = [
        {"name": item.item_type.name, "amount": item.amount}
        for item in run_inputs
        if item.item_type.category == "earning"
    ]
    deduction_items = [
        {"name": item.item_type.name, "amount": item.amount}
        for item in run_inputs
        if item.item_type.category == "deduction"
    ]
    return earning_items, deduction_items


async def post_payroll_run(session: AsyncSession, payroll_run_id: int) -> PayrollRun:
    repository = PayrollRunRepository(session)
    input_repository = PayrollRunInputRepository(session)
    payslip_repository = PayslipRepository(session)
    payroll_run = await repository.get_by_id(payroll_run_id)
    if payroll_run is None:
        raise NotFoundError("Payroll run not found.")
    if payroll_run.status != "APPROVED":
        raise ConflictError("Only approved runs can be posted.")

    run_items = await PayrollRunItemRepository(session).list(payroll_run.id)
    compensation_repository = PayslipVariableCompensationRepository(session)
    deduction_repository = PayslipVariableDeductionRepository(session)
    for run_item in run_items:
        if run_item.payslip_id is None:
            continue
        payslip = await payslip_repository.get_by_id(run_item.payslip_id)
        if payslip is None:
            continue
        run_inputs = await input_repository.list_for_run_user(
            payroll_run.id,
            run_item.user_id,
            approved_only=True,
        )
        earning_items, deduction_items = _build_snapshot_payloads(run_inputs)
        await compensation_repository.replace_for_payslip(payslip.id, earning_items)
        await deduction_repository.replace_for_payslip(payslip.id, deduction_items)

    payroll_run.status = "POSTED"
    payroll_run.posted_at = utc_now()
    payroll_run.locked_at = utc_now()
    return await repository.save(payroll_run)


async def release_payroll_run(session: AsyncSession, payroll_run_id: int) -> PayrollRun:
    repository = PayrollRunRepository(session)
    payroll_run = await repository.get_by_id(payroll_run_id)
    if payroll_run is None:
        raise NotFoundError("Payroll run not found.")
    if payroll_run.status != "POSTED":
        raise ConflictError("Only posted runs can be released.")
    payroll_run.status = "RELEASED"
    payroll_run.released_at = utc_now()
    payroll_run.locked_at = payroll_run.locked_at or utc_now()
    return await repository.save(payroll_run)


async def list_payroll_run_items(session: AsyncSession, payroll_run_id: int) -> list[PayrollRunItem]:
    run = await PayrollRunRepository(session).get_by_id(payroll_run_id)
    if run is None:
        raise NotFoundError("Payroll run not found.")
    return await PayrollRunItemRepository(session).list(payroll_run_id)
def _official_core_sources(effective_from, effective_to) -> list[dict[str, Any]]:
    return [
        {
            "document_type": "SSS Circular",
            "reference_code": "Circular No. 2024-006",
            "title": "2025 SSS Contribution Table",
            "source_url": SSS_2025_TABLE_URL,
            "published_at": None,
            "effective_from": SSS_2025_EFFECTIVE_FROM,
            "effective_to": None,
        },
        {
            "document_type": "SSS Web Guidance",
            "reference_code": "Employees Compensation Program",
            "title": "SSS Employees' Compensation Program",
            "source_url": SSS_EC_PROGRAM_URL,
            "published_at": None,
            "effective_from": SSS_2025_EFFECTIVE_FROM,
            "effective_to": None,
        },
        {
            "document_type": "PhilHealth Circular",
            "reference_code": "ContributionTable_v2 / Circular No. 2019-0009",
            "title": "PhilHealth Premium Contribution Table for Direct Contributors",
            "source_url": PHILHEALTH_CONTRIBUTION_TABLE_URL,
            "published_at": None,
            "effective_from": PHILHEALTH_5_PERCENT_EFFECTIVE_FROM,
            "effective_to": None,
        },
        {
            "document_type": "Pag-IBIG Circular",
            "reference_code": "HDMF Circular No. 274",
            "title": "Revised Guidelines on Pag-IBIG Fund Membership",
            "source_url": PAGIBIG_MEMBERSHIP_CIRCULAR_URL,
            "published_at": None,
            "effective_from": PAGIBIG_MEMBERSHIP_GUIDELINES_EFFECTIVE_FROM,
            "effective_to": None,
        },
        {
            "document_type": "Pag-IBIG Payment Guide",
            "reference_code": "OTC Payment Guide 24 Jan 2025",
            "title": "Guide on Banks and Non-Banks Payment Facilities Accepting Pag-IBIG Fund Payments Through OTC",
            "source_url": PAGIBIG_PAYMENT_GUIDE_URL,
            "published_at": None,
            "effective_from": PAGIBIG_MAX_FUND_SALARY_10K_EFFECTIVE_FROM,
            "effective_to": None,
        },
        {
            "document_type": "BIR Revenue Regulation",
            "reference_code": "Annex E RR 11-2018",
            "title": "Revised Withholding Tax Table (Annex E, effective January 1, 2023 onwards)",
            "source_url": BIR_ANNEX_E_URL,
            "published_at": None,
            "effective_from": BIR_ANNEX_E_2023_EFFECTIVE_FROM,
            "effective_to": None,
        },
        {
            "document_type": "Wage Order",
            "reference_code": "Wage Order No. NCR-26",
            "title": "NCR Wage Order No. NCR-26",
            "source_url": NWPC_NCR_26_URL,
            "published_at": None,
            "effective_from": NCR_WAGE_ORDER_26_EFFECTIVE_FROM,
            "effective_to": None,
        },
    ]
