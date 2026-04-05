from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.models.payroll import PayrollPolicyVersion, PayrollRun, PayrollRunItem
from app.repositories.payroll import (
    PayrollPolicyRuleRepository,
    PayrollPolicySourceRepository,
    PayrollPolicyVersionRepository,
    PayrollRunItemRepository,
    PayrollRunRepository,
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
                is_active=True,
            )
        )
    else:
        existing.effective_from = payload.effective_from
        existing.effective_to = payload.effective_to
        existing = await version_repository.save(existing)
        await rule_repository.clear_policy_rules(existing.id)

    await rule_repository.seed_ph_baseline(existing.id)
    return existing


def _build_sss_employee_brackets_2025() -> list[dict[str, Decimal]]:
    brackets: list[dict[str, Decimal]] = []
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
        brackets.append(
            {
                "min_compensation": min_comp,
                "max_compensation": max_comp,
                "employee_share": regular_employee + mpf_employee,
                "employer_share": regular_employer + mpf_employer,
            }
        )
    return brackets


def _build_bir_annex_e_semi_monthly_brackets() -> list[dict[str, Decimal | str | None]]:
    return [
        {
            "payroll_period": "SEMI_MONTHLY",
            "min_compensation": Decimal("0.00"),
            "max_compensation": Decimal("10416.99"),
            "base_tax": Decimal("0.00"),
            "marginal_rate": Decimal("0.00"),
            "over_amount": Decimal("0.00"),
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "min_compensation": Decimal("10417.00"),
            "max_compensation": Decimal("16666.99"),
            "base_tax": Decimal("0.00"),
            "marginal_rate": Decimal("0.15"),
            "over_amount": Decimal("10417.00"),
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "min_compensation": Decimal("16667.00"),
            "max_compensation": Decimal("33332.99"),
            "base_tax": Decimal("937.50"),
            "marginal_rate": Decimal("0.20"),
            "over_amount": Decimal("16667.00"),
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "min_compensation": Decimal("33333.00"),
            "max_compensation": Decimal("83332.99"),
            "base_tax": Decimal("4270.70"),
            "marginal_rate": Decimal("0.25"),
            "over_amount": Decimal("33333.00"),
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "min_compensation": Decimal("83333.00"),
            "max_compensation": Decimal("333332.99"),
            "base_tax": Decimal("16770.70"),
            "marginal_rate": Decimal("0.30"),
            "over_amount": Decimal("83333.00"),
        },
        {
            "payroll_period": "SEMI_MONTHLY",
            "min_compensation": Decimal("333333.00"),
            "max_compensation": None,
            "base_tax": Decimal("91770.70"),
            "marginal_rate": Decimal("0.35"),
            "over_amount": Decimal("333333.00"),
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
                is_active=True,
            )
        )
    else:
        existing.effective_from = payload.effective_from
        existing.effective_to = payload.effective_to
        existing = await version_repository.save(existing)

    # Core PH statutory rates seeded from official circular frameworks.
    await rule_repository.replace_policy_rules(
        existing.id,
        {
            "sss_brackets": _build_sss_employee_brackets_2025(),
            "philhealth_rules": [
                {
                    "min_compensation": Decimal("10000.00"),
                    "max_compensation": Decimal("100000.00"),
                    "rate": Decimal("0.05"),
                    "employee_share_ratio": Decimal("0.50"),
                }
            ],
            "pagibig_rules": [
                {
                    "min_compensation": Decimal("0.00"),
                    "monthly_compensation_cap": Decimal("1500.00"),
                    "employee_rate": Decimal("0.01"),
                    "employer_rate": Decimal("0.02"),
                    "max_employee_share": None,
                    "max_employer_share": None,
                },
                {
                    "min_compensation": Decimal("1500.01"),
                    "monthly_compensation_cap": Decimal("5000.00"),
                    "employee_rate": Decimal("0.02"),
                    "employer_rate": Decimal("0.02"),
                    "max_employee_share": Decimal("100.00"),
                    "max_employer_share": Decimal("100.00"),
                },
            ],
            "bir_withholding_brackets": _build_bir_annex_e_semi_monthly_brackets(),
            "minimum_wage_orders": [
                {
                    "region_code": "NCR",
                    "sector": "NON_AGRI",
                    "daily_wage_amount": Decimal("695.00"),
                    "effective_from": payload.effective_from,
                    "effective_to": payload.effective_to,
                    "source_reference": "Wage Order No. NCR-26",
                },
                {
                    "region_code": "NCR",
                    "sector": "AGRI_SERVICE_RETAIL_MANUFACTURING_LESS_10",
                    "daily_wage_amount": Decimal("658.00"),
                    "effective_from": payload.effective_from,
                    "effective_to": payload.effective_to,
                    "source_reference": "Wage Order No. NCR-26",
                },
            ],
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


async def post_payroll_run(session: AsyncSession, payroll_run_id: int) -> PayrollRun:
    repository = PayrollRunRepository(session)
    payroll_run = await repository.get_by_id(payroll_run_id)
    if payroll_run is None:
        raise NotFoundError("Payroll run not found.")
    if payroll_run.status != "VALIDATED":
        raise ConflictError("Only validated runs can be posted.")
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
            "source_type": "SSS",
            "reference_code": "Circular No. 2024-006",
            "source_url": "https://www.sss.gov.ph/wp-content/uploads/2024/12/2025-SSS-Contribution-Table-rev.pdf",
            "effective_from": effective_from,
            "effective_to": effective_to,
        },
        {
            "source_type": "PhilHealth",
            "reference_code": "UHC Premium Schedule",
            "source_url": "https://www.philhealth.gov.ph/uhc/",
            "effective_from": effective_from,
            "effective_to": effective_to,
        },
        {
            "source_type": "BIR",
            "reference_code": "RR No. 11-2018 Annex E",
            "source_url": "https://bir-cdn.bir.gov.ph/local/pdf/RR%20No.%2011-2018.pdf",
            "effective_from": effective_from,
            "effective_to": effective_to,
        },
        {
            "source_type": "NWPC",
            "reference_code": "Wage Order No. NCR-26",
            "source_url": "https://nwpc.dole.gov.ph/",
            "effective_from": effective_from,
            "effective_to": effective_to,
        },
    ]
