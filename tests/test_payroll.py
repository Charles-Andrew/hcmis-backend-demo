import anyio
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.department import Department
from app.models.payroll import FixedCompensation, Job, PayrollSetting, Payslip, ThirteenthMonthPay
from app.models.user import User
from app.schemas.payroll import (
    JobUpsertRequest,
    PayrollSettingUpdateRequest,
    PayslipCreateRequest,
    PayslipVariableCompensationUpsertRequest,
    PayslipVariableDeductionUpsertRequest,
    ThirteenthMonthPayCreateRequest,
    ThirteenthMonthPayUpdateRequest,
    ThirteenthMonthPayVariableDeductionUpsertRequest,
)
from app.services import payroll as payroll_service


class FakeDepartmentRepository:
    departments: dict[int, Department] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, department_id: int):
        return self.departments.get(department_id)


class FakeUserRepository:
    users: dict[UUID, User] = {}

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id: UUID):
        return self.users.get(user_id)

    async def list(self, include_superusers: bool = False, **kwargs):
        return list(self.users.values())


class FakePayrollSettingRepository:
    setting: PayrollSetting | None = None

    def __init__(self, session):
        self.session = session

    async def get_first(self):
        return self.setting

    async def create(self, settings: PayrollSetting):
        self.setting = settings
        return settings

    async def save(self, settings: PayrollSetting):
        self.setting = settings
        return settings


class FakeMp2Repository:
    mp2 = None

    def __init__(self, session):
        self.session = session

    async def get_first(self):
        return FakeMp2Repository.mp2

    async def create(self, mp2):
        FakeMp2Repository.mp2 = mp2
        return mp2

    async def save(self, mp2):
        FakeMp2Repository.mp2 = mp2
        return mp2


class FakeJobRepository:
    jobs: dict[int, Job] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, department_id=None):
        jobs = list(self.jobs.values())
        if department_id is not None:
            jobs = [job for job in jobs if any(dep.id == department_id for dep in job.departments)]
        return jobs

    async def get_by_id(self, job_id: int):
        return self.jobs.get(job_id)

    async def get_by_code(self, code: str):
        for job in self.jobs.values():
            if job.code.lower() == code.lower():
                return job
        return None

    async def create(self, job: Job):
        job.id = self.next_id
        self.next_id += 1
        self.jobs[job.id] = job
        return job

    async def save(self, job: Job):
        self.jobs[job.id] = job
        return job

    async def delete(self, job: Job):
        self.jobs.pop(job.id, None)


class FakeFixedCompensationRepository:
    items: dict[int, FixedCompensation] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, month=None, year=None):
        items = list(self.items.values())
        if month is not None:
            items = [item for item in items if item.month == month]
        if year is not None:
            items = [item for item in items if item.year == year]
        return items

    async def get_by_id(self, compensation_id: int):
        return self.items.get(compensation_id)

    async def create(self, compensation: FixedCompensation):
        compensation.id = self.next_id
        self.next_id += 1
        self.items[compensation.id] = compensation
        return compensation

    async def save(self, compensation: FixedCompensation):
        self.items[compensation.id] = compensation
        return compensation

    async def delete(self, compensation: FixedCompensation):
        self.items.pop(compensation.id, None)


class FakePayslipRepository:
    items: dict[int, Payslip] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, user_id=None, month=None, year=None, period=None, released=None):
        items = list(self.items.values())
        if user_id is not None:
            items = [item for item in items if item.user_id == user_id]
        if month is not None:
            items = [item for item in items if item.month == month]
        if year is not None:
            items = [item for item in items if item.year == year]
        if period is not None:
            items = [item for item in items if item.period == period]
        if released is not None:
            items = [item for item in items if item.released == released]
        return items

    async def get_by_id(self, payslip_id: int):
        return self.items.get(payslip_id)

    async def get_by_identity(self, user_id: UUID, month: int, year: int, period: str):
        for item in self.items.values():
            if (
                item.user_id == user_id
                and item.month == month
                and item.year == year
                and item.period == period
            ):
                return item
        return None

    async def create(self, payslip: Payslip):
        payslip.id = self.next_id
        self.next_id += 1
        payslip.created_at = payslip.created_at or utc_now()
        payslip.updated_at = payslip.updated_at or utc_now()
        payslip.user = FakeUserRepository.users.get(payslip.user_id)
        self.items[payslip.id] = payslip
        return payslip

    async def save(self, payslip: Payslip):
        payslip.updated_at = utc_now()
        payslip.user = FakeUserRepository.users.get(payslip.user_id)
        self.items[payslip.id] = payslip
        return payslip

    async def delete(self, payslip: Payslip):
        self.items.pop(payslip.id, None)


class FakePayslipVariableCompensationRepository:
    items: dict[int, object] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def create(self, item):
        item.id = self.next_id
        self.next_id += 1
        self.items[item.id] = item
        return item

    async def get_by_id(self, item_id: int):
        return self.items.get(item_id)

    async def delete(self, item):
        self.items.pop(item.id, None)


class FakePayslipVariableDeductionRepository(FakePayslipVariableCompensationRepository):
    pass


class FakeThirteenthMonthPayRepository:
    items: dict[int, ThirteenthMonthPay] = {}
    next_id = 1

    def __init__(self, session):
        self.session = session

    async def list(self, user_id=None, month=None, year=None, released=None):
        items = list(self.items.values())
        if user_id is not None:
            items = [item for item in items if item.user_id == user_id]
        if month is not None:
            items = [item for item in items if item.month == month]
        if year is not None:
            items = [item for item in items if item.year == year]
        if released is not None:
            items = [item for item in items if item.released == released]
        return items

    async def get_by_id(self, item_id: int):
        return self.items.get(item_id)

    async def get_by_identity(self, user_id: UUID, month: int, year: int):
        for item in self.items.values():
            if item.user_id == user_id and item.month == month and item.year == year:
                return item
        return None

    async def create(self, item: ThirteenthMonthPay):
        item.id = self.next_id
        self.next_id += 1
        self.items[item.id] = item
        return item

    async def save(self, item: ThirteenthMonthPay):
        self.items[item.id] = item
        return item

    async def delete(self, item: ThirteenthMonthPay):
        self.items.pop(item.id, None)


class FakeThirteenthMonthPayVariableDeductionRepository(FakePayslipVariableCompensationRepository):
    pass


def _reset():
    FakePayrollSettingRepository.setting = None
    FakeMp2Repository.mp2 = None
    FakeJobRepository.jobs = {}
    FakeJobRepository.next_id = 1
    FakeFixedCompensationRepository.items = {}
    FakeFixedCompensationRepository.next_id = 1
    FakePayslipRepository.items = {}
    FakePayslipRepository.next_id = 1
    FakePayslipVariableCompensationRepository.items = {}
    FakePayslipVariableCompensationRepository.next_id = 1
    FakePayslipVariableDeductionRepository.items = {}
    FakePayslipVariableDeductionRepository.next_id = 1
    FakeThirteenthMonthPayRepository.items = {}
    FakeThirteenthMonthPayRepository.next_id = 1
    FakeThirteenthMonthPayVariableDeductionRepository.items = {}
    FakeThirteenthMonthPayVariableDeductionRepository.next_id = 1
    FakeUserRepository.users = {}
    FakeDepartmentRepository.departments = {}


def _seed():
    dept = Department(id=1, name="Operations", code="OPS", is_active=True, workweek=[])
    FakeDepartmentRepository.departments[1] = dept
    job = Job(id=1, title="Operations Staff", code="OPS", salary_grade=1, is_active=True)
    job.departments = [dept]
    FakeJobRepository.jobs[1] = job
    user = User(
        id=UUID(int=1),
        email="employee@example.com",
        password_hash="hashed",
        first_name="Employee",
        last_name="One",
        rank="OPS-1",
        department_id=1,
        can_modify_shift=False,
        is_active=True,
        is_superuser=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    user.department = dept
    FakeUserRepository.users[UUID(int=1)] = user

    FakePayrollSettingRepository.setting = PayrollSetting(
        id=1,
        minimum_wage_amount=Decimal("1000.00"),
        deduction_config=payroll_service.DEFAULT_DEDUCTION_CONFIG,
        basic_salary_multiplier=Decimal("1.0000"),
        basic_salary_step_multiplier=Decimal("1.0000"),
        basic_salary_steps=2,
        max_job_rank=3,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    FakeMp2Repository.mp2 = None


def test_payroll_settings_and_jobs(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(payroll_service, "PayrollSettingRepository", FakePayrollSettingRepository)
    monkeypatch.setattr(payroll_service, "Mp2Repository", FakeMp2Repository)
    monkeypatch.setattr(payroll_service, "JobRepository", FakeJobRepository)
    monkeypatch.setattr(payroll_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(payroll_service, "UserRepository", FakeUserRepository)

    settings = anyio.run(payroll_service.get_settings, cast(AsyncSession, object()))
    assert settings.minimum_wage_amount == Decimal("1000.00")

    updated = anyio.run(
        payroll_service.update_settings,
        cast(AsyncSession, object()),
        PayrollSettingUpdateRequest(minimum_wage_amount=Decimal("1200.00")),
    )
    assert updated.minimum_wage_amount == Decimal("1200.00")

    job = anyio.run(
        payroll_service.create_job,
        cast(AsyncSession, object()),
        JobUpsertRequest(title="Staff", code="STAFF", salary_grade=1, department_ids=[1]),
    )
    assert job.code == "STAFF"


def test_payslip_calculation_and_variable_adjustments(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(payroll_service, "PayrollSettingRepository", FakePayrollSettingRepository)
    monkeypatch.setattr(payroll_service, "Mp2Repository", FakeMp2Repository)
    monkeypatch.setattr(payroll_service, "JobRepository", FakeJobRepository)
    monkeypatch.setattr(payroll_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(payroll_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(payroll_service, "FixedCompensationRepository", FakeFixedCompensationRepository)
    monkeypatch.setattr(payroll_service, "PayslipRepository", FakePayslipRepository)
    monkeypatch.setattr(payroll_service, "PayslipVariableCompensationRepository", FakePayslipVariableCompensationRepository)
    monkeypatch.setattr(payroll_service, "PayslipVariableDeductionRepository", FakePayslipVariableDeductionRepository)

    fixed = FixedCompensation(
        id=1,
        name="Rice Allowance",
        amount=Decimal("200.00"),
        month=1,
        year=2026,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    fixed.users = [FakeUserRepository.users[UUID(int=1)]]
    FakeFixedCompensationRepository.items[1] = fixed

    payslip = anyio.run(
        payroll_service.get_or_create_payslip,
        cast(AsyncSession, object()),
        PayslipCreateRequest(user_id=UUID(int=1), month=1, year=2026, period="2ND"),
    )
    assert payslip.salary == Decimal("1000.00")

    comp = anyio.run(
        payroll_service.add_payslip_variable_compensation,
        cast(AsyncSession, object()),
        payslip.id,
        PayslipVariableCompensationUpsertRequest(name="Bonus", amount=Decimal("100.00")),
    )
    assert comp.name == "Bonus"

    ded = anyio.run(
        payroll_service.add_payslip_variable_deduction,
        cast(AsyncSession, object()),
        payslip.id,
        PayslipVariableDeductionUpsertRequest(name="Loan", amount=Decimal("50.00")),
    )
    assert ded.name == "Loan"

    summary = anyio.run(
        payroll_service.get_payslip_summary,
        cast(AsyncSession, object()),
        payslip.id,
    )
    assert summary["net_salary"] is not None


def test_mp2_update_and_summary_deduction(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(payroll_service, "PayrollSettingRepository", FakePayrollSettingRepository)
    monkeypatch.setattr(payroll_service, "Mp2Repository", FakeMp2Repository)
    monkeypatch.setattr(payroll_service, "JobRepository", FakeJobRepository)
    monkeypatch.setattr(payroll_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(payroll_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(payroll_service, "FixedCompensationRepository", FakeFixedCompensationRepository)
    monkeypatch.setattr(payroll_service, "PayslipRepository", FakePayslipRepository)
    monkeypatch.setattr(payroll_service, "PayslipVariableCompensationRepository", FakePayslipVariableCompensationRepository)
    monkeypatch.setattr(payroll_service, "PayslipVariableDeductionRepository", FakePayslipVariableDeductionRepository)

    async def _update_mp2():
        return await payroll_service.update_mp2(
            cast(AsyncSession, object()),
            amount=Decimal("123.45"),
            user_ids=[UUID(int=1)],
        )

    mp2 = anyio.run(_update_mp2)
    assert mp2.amount == Decimal("123.45")
    assert mp2.users[0].id == UUID(int=1)

    fixed = FixedCompensation(
        id=1,
        name="Rice Allowance",
        amount=Decimal("200.00"),
        month=1,
        year=2026,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    fixed.users = [FakeUserRepository.users[UUID(int=1)]]
    FakeFixedCompensationRepository.items[1] = fixed

    payslip = anyio.run(
        payroll_service.get_or_create_payslip,
        cast(AsyncSession, object()),
        PayslipCreateRequest(user_id=UUID(int=1), month=1, year=2026, period="2ND"),
    )
    summary = anyio.run(
        payroll_service.get_payslip_summary,
        cast(AsyncSession, object()),
        payslip.id,
    )
    assert summary["mp2_deduction"] == Decimal("123.45")


def test_thirteenth_month_pay_flow(monkeypatch):
    _reset()
    _seed()
    monkeypatch.setattr(payroll_service, "PayrollSettingRepository", FakePayrollSettingRepository)
    monkeypatch.setattr(payroll_service, "Mp2Repository", FakeMp2Repository)
    monkeypatch.setattr(payroll_service, "JobRepository", FakeJobRepository)
    monkeypatch.setattr(payroll_service, "DepartmentRepository", FakeDepartmentRepository)
    monkeypatch.setattr(payroll_service, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(payroll_service, "ThirteenthMonthPayRepository", FakeThirteenthMonthPayRepository)
    monkeypatch.setattr(payroll_service, "ThirteenthMonthPayVariableDeductionRepository", FakeThirteenthMonthPayVariableDeductionRepository)

    pay = anyio.run(
        payroll_service.create_thirteenth_month_pay,
        cast(AsyncSession, object()),
        ThirteenthMonthPayCreateRequest(user_id=UUID(int=1), amount=Decimal("5000.00"), month=12, year=2026),
    )
    assert pay.amount == Decimal("5000.00")

    updated = anyio.run(
        payroll_service.update_thirteenth_month_pay,
        cast(AsyncSession, object()),
        pay.id,
        ThirteenthMonthPayUpdateRequest(amount=Decimal("5500.00")),
    )
    assert updated.amount == Decimal("5500.00")

    deduction = anyio.run(
        payroll_service.add_thirteenth_month_pay_variable_deduction,
        cast(AsyncSession, object()),
        pay.id,
        ThirteenthMonthPayVariableDeductionUpsertRequest(name="Gov Loan", amount=Decimal("500.00")),
    )
    assert deduction.amount == Decimal("500.00")
