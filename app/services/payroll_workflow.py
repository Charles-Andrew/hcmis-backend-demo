from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.models.payroll import PayrollPolicyVersion
from app.repositories.payroll import (
    PayrollPolicyRuleRepository,
    PayrollPolicySourceRepository,
    PayrollPolicyVersionRepository,
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
)


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
