from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, List, cast
from uuid import UUID

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.core.exceptions import ConflictError
from app.models.payroll import PayrollPolicyVersion, PayrollRun, PayrollRunItem, Payslip
from app.schemas.payroll import (
    PayrollComputationRead,
    PayrollPolicyOfficialSeedRequest,
    PayrollPolicySourcesUpdateRequest,
    PayrollPolicyRulesUpdateRequest,
    PayrollPolicyVersionCreateRequest,
    PayrollPolicySourceWrite,
    PolicySssBracketWrite,
    PayrollPolicySeedRequest,
    PayrollRunCreateRequest,
)
from app.services import payroll_workflow


class FakePolicyVersionRepository:
    items: dict[int, PayrollPolicyVersion] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, policy_key=None):
        values = list(self.items.values())
        if policy_key is not None:
            values = [item for item in values if item.policy_key == policy_key]
        return values

    async def get_by_id(self, policy_version_id: int):
        return self.items.get(policy_version_id)

    async def get_by_identity(self, policy_key: str, version_label: str):
        for item in self.items.values():
            if item.policy_key == policy_key and item.version_label == version_label:
                return item
        return None

    async def create(self, item: PayrollPolicyVersion):
        item.id = type(self).next_id
        type(self).next_id += 1
        item.created_at = item.created_at or utc_now()
        item.updated_at = item.updated_at or utc_now()
        self.items[item.id] = item
        return item

    async def save(self, item: PayrollPolicyVersion):
        item.updated_at = utc_now()
        self.items[item.id] = item
        return item

    async def delete(self, item: PayrollPolicyVersion):
        self.items.pop(item.id, None)


class FakePolicyRuleRepository:
    seeded_policy_ids: list[int] = []
    cleared_policy_ids: list[int] = []
    rules_by_policy_id: dict[int, dict] = {}

    def __init__(self, session):
        self.session = session

    async def clear_policy_rules(self, policy_version_id: int):
        self.cleared_policy_ids.append(policy_version_id)
        self.rules_by_policy_id[policy_version_id] = {
            "sss_brackets": [],
            "philhealth_rules": [],
            "pagibig_rules": [],
            "bir_withholding_brackets": [],
            "minimum_wage_orders": [],
        }

    async def seed_ph_baseline(self, policy_version_id: int):
        self.seeded_policy_ids.append(policy_version_id)
        self.rules_by_policy_id[policy_version_id] = {
            "sss_brackets": [],
            "philhealth_rules": [],
            "pagibig_rules": [],
            "bir_withholding_brackets": [],
            "minimum_wage_orders": [],
        }

    async def get_policy_rules(self, policy_version_id: int):
        return self.rules_by_policy_id.get(
            policy_version_id,
            {
                "sss_brackets": [],
                "philhealth_rules": [],
                "pagibig_rules": [],
                "bir_withholding_brackets": [],
                "minimum_wage_orders": [],
            },
        )

    async def replace_policy_rules(self, policy_version_id: int, payload: dict):
        shaped = {}
        for key, items in payload.items():
            shaped[key] = [{**item, "id": index + 1} for index, item in enumerate(items)]
        self.rules_by_policy_id[policy_version_id] = shaped


class FakePolicySourceRepository:
    sources_by_policy_id: dict[int, List[dict[str, Any]]] = {}

    def __init__(self, session):
        self.session = session

    async def list(self, policy_version_id: int):
        return self.sources_by_policy_id.get(policy_version_id, [])

    async def replace(
        self,
        policy_version_id: int,
        sources: List[dict[str, Any]],
        applied_by,
        applied_at,
    ):
        shaped = []
        for index, source in enumerate(sources):
            shaped.append(
                {
                    "id": index + 1,
                    **source,
                    "applied_by": applied_by,
                    "applied_at": applied_at,
                    "created_at": applied_at,
                    "updated_at": applied_at,
                }
            )
        self.sources_by_policy_id[policy_version_id] = shaped
        return shaped


class FakeRunRepository:
    items: dict[int, PayrollRun] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, month=None, year=None):
        values = list(self.items.values())
        if month is not None:
            values = [item for item in values if item.month == month]
        if year is not None:
            values = [item for item in values if item.year == year]
        return values

    async def get_by_id(self, payroll_run_id: int):
        return self.items.get(payroll_run_id)

    async def get_by_identity(self, month: int, year: int, period: str):
        for item in self.items.values():
            if item.month == month and item.year == year and item.period == period:
                return item
        return None

    async def create(self, item: PayrollRun):
        item.id = type(self).next_id
        type(self).next_id += 1
        self.items[item.id] = item
        return item

    async def save(self, item: PayrollRun):
        self.items[item.id] = item
        return item


class FakeRunItemRepository:
    items: dict[int, List[PayrollRunItem]] = {}

    def __init__(self, session):
        self.session = session

    async def list(self, payroll_run_id: int):
        return self.items.get(payroll_run_id, [])

    async def clear(self, payroll_run_id: int):
        self.items[payroll_run_id] = []

    async def create_many(self, items: List[PayrollRunItem]):
        if not items:
            return items
        run_id = items[0].payroll_run_id
        self.items[run_id] = items
        return items


class FakePayslipRepository:
    items: List[Payslip] = []

    def __init__(self, session):
        self.session = session

    async def list(self, user_id=None, month=None, year=None, period=None, released=None):
        data = list(self.items)
        if month is not None:
            data = [item for item in data if item.month == month]
        if year is not None:
            data = [item for item in data if item.year == year]
        if period is not None:
            data = [item for item in data if item.period == period]
        return data


def _reset():
    FakePolicyVersionRepository.items = {}
    FakePolicyVersionRepository.next_id = 1
    FakePolicyRuleRepository.seeded_policy_ids = []
    FakePolicyRuleRepository.cleared_policy_ids = []
    FakePolicyRuleRepository.rules_by_policy_id = {}
    FakePolicySourceRepository.sources_by_policy_id = {}
    FakeRunRepository.items = {}
    FakeRunRepository.next_id = 1
    FakeRunItemRepository.items = {}
    FakePayslipRepository.items = []


def test_seed_policy_and_validate_run(monkeypatch):
    _reset()
    monkeypatch.setattr(
        payroll_workflow, "PayrollPolicyVersionRepository", FakePolicyVersionRepository
    )
    monkeypatch.setattr(payroll_workflow, "PayrollPolicyRuleRepository", FakePolicyRuleRepository)
    monkeypatch.setattr(payroll_workflow, "PayrollPolicySourceRepository", FakePolicySourceRepository)
    monkeypatch.setattr(payroll_workflow, "PayrollRunRepository", FakeRunRepository)
    monkeypatch.setattr(payroll_workflow, "PayrollRunItemRepository", FakeRunItemRepository)
    monkeypatch.setattr(payroll_workflow, "PayslipRepository", FakePayslipRepository)

    async def fake_compute_summary(_session, _payslip_id, **_kwargs):
        return PayrollComputationRead(
            gross_pay=Decimal("1000.00"),
            total_deductions=Decimal("100.00"),
            net_pay=Decimal("900.00"),
            mandatory_deductions={"sss": Decimal("50.00")},
            variable_deductions=Decimal("50.00"),
            mp2_deduction=Decimal("0.00"),
            included_in_total_deductions=True,
            notes=[],
        )

    monkeypatch.setattr(payroll_workflow, "compute_payslip_summary_v2", fake_compute_summary)

    seeded = anyio.run(
        payroll_workflow.seed_ph_policy_baseline,
        cast(AsyncSession, object()),
        PayrollPolicySeedRequest(
            version_label="BASELINE-2026",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            overwrite_existing=False,
        ),
    )
    assert seeded.id == 1
    assert seeded.is_active is False
    assert FakePolicyRuleRepository.seeded_policy_ids == [1]

    activated = anyio.run(
        payroll_workflow.activate_policy_version,
        cast(AsyncSession, object()),
        seeded.id,
    )
    assert activated.is_active is True

    run = anyio.run(
        payroll_workflow.create_payroll_run,
        cast(AsyncSession, object()),
        PayrollRunCreateRequest(month=4, year=2026, period="2ND", policy_version_id=seeded.id),
        UUID(int=1),
    )
    assert run.status == "DRAFT"

    FakePayslipRepository.items = [
        Payslip(
            id=1,
            user_id=UUID(int=2),
            month=4,
            year=2026,
            period="2ND",
            rank="OPS-1",
            salary=Decimal("1000.00"),
            released=False,
        )
    ]

    validated = anyio.run(
        payroll_workflow.validate_payroll_run, cast(AsyncSession, object()), run.id
    )
    assert validated.status == "VALIDATED"
    run_items = anyio.run(
        payroll_workflow.list_payroll_run_items, cast(AsyncSession, object()), run.id
    )
    assert len(run_items) == 1
    assert run_items[0].net_pay == Decimal("900.00")


def test_update_policy_rules(monkeypatch):
    _reset()
    monkeypatch.setattr(
        payroll_workflow, "PayrollPolicyVersionRepository", FakePolicyVersionRepository
    )
    monkeypatch.setattr(payroll_workflow, "PayrollPolicyRuleRepository", FakePolicyRuleRepository)
    monkeypatch.setattr(payroll_workflow, "PayrollPolicySourceRepository", FakePolicySourceRepository)

    created = anyio.run(
        payroll_workflow.create_policy_version,
        cast(AsyncSession, object()),
        PayrollPolicyVersionCreateRequest(
            policy_key="PH_STATUTORY",
            version_label="PH-2026-A",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            is_active=True,
        ),
    )
    detail = anyio.run(
        payroll_workflow.update_policy_version_rules,
        cast(AsyncSession, object()),
        created.id,
        PayrollPolicyRulesUpdateRequest(
            sss_brackets=[
                PolicySssBracketWrite(
                    compensation_range_from=Decimal("0.00"),
                    compensation_range_to=Decimal("999999.00"),
                    monthly_salary_credit=Decimal("10000.00"),
                    employee_contribution=Decimal("500.00"),
                    employer_contribution=Decimal("1000.00"),
                    ec_contribution=Decimal("10.00"),
                    mpf_employee_contribution=Decimal("0.00"),
                    mpf_employer_contribution=Decimal("0.00"),
                )
            ],
            philhealth_rules=[],
            pagibig_rules=[],
            bir_withholding_brackets=[],
            minimum_wage_orders=[],
        ),
    )
    assert detail.version.id == created.id
    assert len(detail.rules.sss_brackets) == 1


def test_seed_official_core(monkeypatch):
    _reset()
    monkeypatch.setattr(
        payroll_workflow, "PayrollPolicyVersionRepository", FakePolicyVersionRepository
    )
    monkeypatch.setattr(payroll_workflow, "PayrollPolicyRuleRepository", FakePolicyRuleRepository)
    monkeypatch.setattr(payroll_workflow, "PayrollPolicySourceRepository", FakePolicySourceRepository)

    seeded = anyio.run(
        payroll_workflow.seed_ph_policy_official_core,
        cast(AsyncSession, object()),
        PayrollPolicyOfficialSeedRequest(
            version_label="PH-OFFICIAL-CORE-2026",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            overwrite_existing=False,
        ),
    )
    assert seeded.id == 1
    assert seeded.is_active is False
    rules = FakePolicyRuleRepository.rules_by_policy_id[seeded.id]
    assert len(rules["sss_brackets"]) >= 50
    assert rules["sss_brackets"][0]["ec_contribution"] == Decimal("10.00")
    assert rules["sss_brackets"][-1]["ec_contribution"] == Decimal("30.00")
    assert len(rules["philhealth_rules"]) == 1
    assert rules["philhealth_rules"][0]["premium_rate"] == Decimal("0.05")
    assert len(rules["pagibig_rules"]) == 2
    assert rules["pagibig_rules"][1]["compensation_cap"] == Decimal("10000.00")
    assert rules["pagibig_rules"][1]["employee_share_cap"] == Decimal("200.00")
    assert len(rules["bir_withholding_brackets"]) == 6
    assert len(rules["minimum_wage_orders"]) == 2
    assert rules["minimum_wage_orders"][0]["effective_from"] == date(2025, 7, 18)
    assert len(FakePolicySourceRepository.sources_by_policy_id[seeded.id]) >= 7


def test_activate_policy_version(monkeypatch):
    _reset()
    monkeypatch.setattr(
        payroll_workflow, "PayrollPolicyVersionRepository", FakePolicyVersionRepository
    )

    first = anyio.run(
        payroll_workflow.create_policy_version,
        cast(AsyncSession, object()),
        PayrollPolicyVersionCreateRequest(
            policy_key="PH_STATUTORY",
            version_label="PH-2025-A",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            is_active=True,
        ),
    )
    second = anyio.run(
        payroll_workflow.create_policy_version,
        cast(AsyncSession, object()),
        PayrollPolicyVersionCreateRequest(
            policy_key="PH_STATUTORY",
            version_label="PH-2025-B",
            effective_from=date(2025, 7, 1),
            effective_to=None,
            is_active=False,
        ),
    )

    activated = anyio.run(
        payroll_workflow.activate_policy_version,
        cast(AsyncSession, object()),
        second.id,
    )

    assert activated.id == second.id
    assert FakePolicyVersionRepository.items[first.id].is_active is False
    assert FakePolicyVersionRepository.items[second.id].is_active is True


def test_delete_active_policy_version_rejected(monkeypatch):
    _reset()
    monkeypatch.setattr(
        payroll_workflow, "PayrollPolicyVersionRepository", FakePolicyVersionRepository
    )

    created = anyio.run(
        payroll_workflow.create_policy_version,
        cast(AsyncSession, object()),
        PayrollPolicyVersionCreateRequest(
            policy_key="PH_STATUTORY",
            version_label="PH-2025-ACTIVE",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            is_active=True,
        ),
    )

    try:
        anyio.run(
            payroll_workflow.delete_policy_version,
            cast(AsyncSession, object()),
            created.id,
        )
        assert False, "Expected ConflictError for active policy delete."
    except ConflictError as error:
        assert str(error) == "Cannot delete an active payroll policy version."


def test_update_policy_sources(monkeypatch):
    _reset()
    monkeypatch.setattr(
        payroll_workflow, "PayrollPolicyVersionRepository", FakePolicyVersionRepository
    )
    monkeypatch.setattr(payroll_workflow, "PayrollPolicySourceRepository", FakePolicySourceRepository)

    created = anyio.run(
        payroll_workflow.create_policy_version,
        cast(AsyncSession, object()),
        PayrollPolicyVersionCreateRequest(
            policy_key="PH_STATUTORY",
            version_label="PH-2026-SOURCES",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            is_active=True,
        ),
    )
    detail = anyio.run(
        payroll_workflow.update_policy_version_sources,
        cast(AsyncSession, object()),
        created.id,
        PayrollPolicySourcesUpdateRequest(
            sources=[
                PayrollPolicySourceWrite(
                    document_type="BIR Revenue Regulation",
                    reference_code="RR 11-2018",
                    title="BIR Revenue Regulation No. 11-2018",
                    source_url="https://bir-cdn.bir.gov.ph/local/pdf/RR%20No.%2011-2018.pdf",
                    published_at=None,
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                )
            ]
        ),
        UUID(int=1),
    )
    assert detail.version.id == created.id
    assert len(detail.sources) == 1
    assert detail.sources[0].document_type == "BIR Revenue Regulation"
