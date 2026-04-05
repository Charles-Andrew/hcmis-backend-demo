from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from app.schemas.department import DepartmentRead
from app.schemas.user import UserRead


class PayrollSettingRead(BaseModel):
    id: int
    minimum_wage_amount: Decimal
    deduction_config: list[dict]
    basic_salary_multiplier: Decimal
    basic_salary_step_multiplier: Decimal
    basic_salary_steps: int
    max_position_rank: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollPolicyVersionRead(BaseModel):
    id: int
    policy_key: str
    version_label: str
    effective_from: date
    effective_to: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollPolicyVersionCreateRequest(BaseModel):
    policy_key: str = Field(min_length=1, max_length=100)
    version_label: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_to: date | None = None
    is_active: bool = True


class PayrollPolicySeedRequest(BaseModel):
    version_label: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_to: date | None = None
    overwrite_existing: bool = False


class PayrollPolicyOfficialSeedRequest(BaseModel):
    version_label: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_to: date | None = None
    overwrite_existing: bool = False


class PayrollPolicySourceRead(BaseModel):
    id: int
    source_type: str
    reference_code: str
    source_url: str
    effective_from: date
    effective_to: date | None = None
    applied_by: UUID | None = None
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollPolicySourceWrite(BaseModel):
    source_type: str = Field(min_length=1, max_length=50)
    reference_code: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=500)
    effective_from: date
    effective_to: date | None = None


class PayrollPolicySourcesUpdateRequest(BaseModel):
    sources: list[PayrollPolicySourceWrite] = Field(default_factory=list)


class PolicySssBracketRead(BaseModel):
    id: int
    min_compensation: Decimal
    max_compensation: Decimal
    employee_share: Decimal
    employer_share: Decimal

    model_config = ConfigDict(from_attributes=True)


class PolicySssBracketWrite(BaseModel):
    min_compensation: Decimal = Field(ge=0)
    max_compensation: Decimal = Field(ge=0)
    employee_share: Decimal = Field(ge=0)
    employer_share: Decimal = Field(ge=0)


class PolicyPhilhealthRuleRead(BaseModel):
    id: int
    min_compensation: Decimal
    max_compensation: Decimal
    rate: Decimal
    employee_share_ratio: Decimal

    model_config = ConfigDict(from_attributes=True)


class PolicyPhilhealthRuleWrite(BaseModel):
    min_compensation: Decimal = Field(ge=0)
    max_compensation: Decimal = Field(ge=0)
    rate: Decimal = Field(ge=0)
    employee_share_ratio: Decimal = Field(ge=0)


class PolicyPagibigRuleRead(BaseModel):
    id: int
    min_compensation: Decimal
    monthly_compensation_cap: Decimal
    employee_rate: Decimal
    employer_rate: Decimal
    max_employee_share: Decimal | None = None
    max_employer_share: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyPagibigRuleWrite(BaseModel):
    min_compensation: Decimal = Field(ge=0)
    monthly_compensation_cap: Decimal = Field(ge=0)
    employee_rate: Decimal = Field(ge=0)
    employer_rate: Decimal = Field(ge=0)
    max_employee_share: Decimal | None = Field(default=None, ge=0)
    max_employer_share: Decimal | None = Field(default=None, ge=0)


class PolicyBirWithholdingBracketRead(BaseModel):
    id: int
    payroll_period: str
    min_compensation: Decimal
    max_compensation: Decimal | None = None
    base_tax: Decimal
    marginal_rate: Decimal
    over_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class PolicyBirWithholdingBracketWrite(BaseModel):
    payroll_period: str = Field(pattern="^(DAILY|WEEKLY|SEMI_MONTHLY|MONTHLY|ANNUAL)$")
    min_compensation: Decimal = Field(ge=0)
    max_compensation: Decimal | None = Field(default=None, ge=0)
    base_tax: Decimal = Field(ge=0)
    marginal_rate: Decimal = Field(ge=0)
    over_amount: Decimal = Field(ge=0)


class PolicyMinimumWageOrderRead(BaseModel):
    id: int
    region_code: str
    sector: str
    daily_wage_amount: Decimal
    effective_from: date
    effective_to: date | None = None
    source_reference: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyMinimumWageOrderWrite(BaseModel):
    region_code: str = Field(min_length=1, max_length=20)
    sector: str = Field(default="GENERAL", min_length=1, max_length=50)
    daily_wage_amount: Decimal = Field(ge=0)
    effective_from: date
    effective_to: date | None = None
    source_reference: str | None = Field(default=None, max_length=255)


class PayrollPolicyRulesRead(BaseModel):
    sss_brackets: list[PolicySssBracketRead] = Field(default_factory=list)
    philhealth_rules: list[PolicyPhilhealthRuleRead] = Field(default_factory=list)
    pagibig_rules: list[PolicyPagibigRuleRead] = Field(default_factory=list)
    bir_withholding_brackets: list[PolicyBirWithholdingBracketRead] = Field(default_factory=list)
    minimum_wage_orders: list[PolicyMinimumWageOrderRead] = Field(default_factory=list)


class PayrollPolicyRulesUpdateRequest(BaseModel):
    sss_brackets: list[PolicySssBracketWrite] = Field(default_factory=list)
    philhealth_rules: list[PolicyPhilhealthRuleWrite] = Field(default_factory=list)
    pagibig_rules: list[PolicyPagibigRuleWrite] = Field(default_factory=list)
    bir_withholding_brackets: list[PolicyBirWithholdingBracketWrite] = Field(default_factory=list)
    minimum_wage_orders: list[PolicyMinimumWageOrderWrite] = Field(default_factory=list)


class PayrollPolicyDetailRead(BaseModel):
    version: PayrollPolicyVersionRead
    rules: PayrollPolicyRulesRead


class PayrollPolicySourcesDetailRead(BaseModel):
    version: PayrollPolicyVersionRead
    sources: list[PayrollPolicySourceRead] = Field(default_factory=list)


class Mp2Read(BaseModel):
    id: int
    amount: Decimal
    users: list[UserRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class Mp2UpdateRequest(BaseModel):
    amount: Decimal = Field(ge=0)
    user_ids: list[UUID] = Field(default_factory=list)


class PayrollSettingUpdateRequest(BaseModel):
    minimum_wage_amount: Decimal | None = Field(default=None, ge=0)
    deduction_config: list[dict] | None = None
    basic_salary_multiplier: Decimal | None = None
    basic_salary_step_multiplier: Decimal | None = None
    basic_salary_steps: int | None = Field(default=None, ge=1)
    max_position_rank: int | None = Field(default=None, ge=1)


class PositionRead(BaseModel):
    id: int
    title: str
    code: str
    salary_grade: int
    is_active: bool
    departments: list[DepartmentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PositionUpsertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    code: str = Field(min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$")
    salary_grade: int = Field(ge=1)
    department_ids: list[int] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value


class FixedCompensationRead(BaseModel):
    id: int
    name: str
    amount: Decimal
    month: int
    year: int
    users: list[UserRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FixedCompensationUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(ge=0)
    month: int
    year: int
    user_ids: list[UUID] = Field(default_factory=list)


class FixedCompensationUsersRequest(BaseModel):
    user_ids: list[UUID] = Field(default_factory=list)


class PayslipVariableCompensationRead(BaseModel):
    id: int
    payslip_id: int
    name: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayslipVariableCompensationUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(ge=0)


class PayslipVariableDeductionRead(BaseModel):
    id: int
    payslip_id: int
    name: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayslipVariableDeductionUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(ge=0)


class PayslipRead(BaseModel):
    id: int
    user_id: UUID
    rank: str | None = None
    salary: Decimal | None = None
    period: str | None = None
    released: bool
    release_date: datetime | None = None
    month: int | None = None
    year: int | None = None
    user: UserRead | None = None
    variable_compensations: list[PayslipVariableCompensationRead] = Field(default_factory=list)
    variable_deductions: list[PayslipVariableDeductionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayslipCreateRequest(BaseModel):
    user_id: UUID
    month: int
    year: int
    period: str = Field(pattern="^(1ST|2ND)$")


class PayslipUpdateRequest(BaseModel):
    rank: str | None = Field(default=None, max_length=500)
    salary: Decimal | None = Field(default=None, ge=0)
    released: bool | None = None


class PayslipSummaryRead(BaseModel):
    period: str | None = None
    salary: Decimal | None = None
    compensations: list[FixedCompensationRead] = Field(default_factory=list)
    variable_compensations: list[PayslipVariableCompensationRead] = Field(default_factory=list)
    gross_pay: Decimal | None = None
    variable_deductions: list[PayslipVariableDeductionRead] = Field(default_factory=list)
    total_deductions: Decimal | None = None
    net_salary: Decimal | None = None
    sss_deduction: Decimal | None = None
    philhealth_deduction: Decimal | None = None
    pag_ibig_deduction: Decimal | None = None
    mp2_deduction: Decimal | None = None
    tax_deduction: Decimal | None = None


class PayrollComputationRead(BaseModel):
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    mandatory_deductions: dict[str, Decimal] = Field(default_factory=dict)
    variable_deductions: Decimal
    mp2_deduction: Decimal
    included_in_total_deductions: bool = True
    notes: list[str] = Field(default_factory=list)


class PayslipSummaryComparisonRead(BaseModel):
    payslip_id: int
    legacy_summary: PayslipSummaryRead
    new_engine: PayrollComputationRead
    differences: dict[str, Decimal] = Field(default_factory=dict)


class PayrollRunRead(BaseModel):
    id: int
    month: int
    year: int
    period: str
    status: str
    policy_version_id: int | None = None
    started_at: datetime | None = None
    posted_at: datetime | None = None
    released_at: datetime | None = None
    locked_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollRunCreateRequest(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000)
    period: str = Field(pattern="^(1ST|2ND)$")
    policy_version_id: int = Field(ge=1)


class PayrollRunItemRead(BaseModel):
    id: int
    payroll_run_id: int
    user_id: UUID
    payslip_id: int | None = None
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    breakdown: dict = Field(default_factory=dict)
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThirteenthMonthPayVariableDeductionRead(BaseModel):
    id: int
    thirteenth_month_pay_id: int
    name: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThirteenthMonthPayVariableDeductionUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(ge=0)


class ThirteenthMonthPayRead(BaseModel):
    id: int
    user_id: UUID
    amount: Decimal | None = None
    month: int | None = None
    year: int | None = None
    released: bool
    release_date: datetime | None = None
    user: UserRead | None = None
    variable_deductions: list[ThirteenthMonthPayVariableDeductionRead] = Field(
        default_factory=list
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThirteenthMonthPayCreateRequest(BaseModel):
    user_id: UUID
    amount: Decimal = Field(ge=0)
    month: int
    year: int


class ThirteenthMonthPayUpdateRequest(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0)
    released: bool | None = None
