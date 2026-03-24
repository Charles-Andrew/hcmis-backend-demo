from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.department import DepartmentRead
from app.schemas.user import UserRead


class PayrollSettingRead(BaseModel):
    id: int
    minimum_wage_amount: Decimal
    deduction_config: list[dict]
    basic_salary_multiplier: Decimal
    basic_salary_step_multiplier: Decimal
    basic_salary_steps: int
    max_job_rank: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Mp2Read(BaseModel):
    id: int
    amount: Decimal
    users: list[UserRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class Mp2UpdateRequest(BaseModel):
    amount: Decimal = Field(ge=0)
    user_ids: list[int] = Field(default_factory=list)


class PayrollSettingUpdateRequest(BaseModel):
    minimum_wage_amount: Decimal | None = Field(default=None, ge=0)
    deduction_config: list[dict] | None = None
    basic_salary_multiplier: Decimal | None = None
    basic_salary_step_multiplier: Decimal | None = None
    basic_salary_steps: int | None = Field(default=None, ge=1)
    max_job_rank: int | None = Field(default=None, ge=1)


class JobRead(BaseModel):
    id: int
    title: str
    code: str
    salary_grade: int
    is_active: bool
    departments: list[DepartmentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobUpsertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    code: str = Field(min_length=1, max_length=10)
    salary_grade: int = Field(ge=1)
    department_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


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
    user_ids: list[int] = Field(default_factory=list)


class FixedCompensationUsersRequest(BaseModel):
    user_ids: list[int] = Field(default_factory=list)


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
    user_id: int
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
    user_id: int
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
    user_id: int
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
    user_id: int
    amount: Decimal = Field(ge=0)
    month: int
    year: int


class ThirteenthMonthPayUpdateRequest(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0)
    released: bool | None = None
