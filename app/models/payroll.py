from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base

position_departments = Table(
    "position_departments",
    Base.metadata,
    Column("position_id", ForeignKey("positions.id"), primary_key=True),
    Column("department_id", ForeignKey("departments.id"), primary_key=True),
)

mp2_users = Table(
    "mp2_users",
    Base.metadata,
    Column("mp2_id", ForeignKey("mp2_accounts.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)

fixed_compensation_users = Table(
    "fixed_compensation_users",
    Base.metadata,
    Column("fixed_compensation_id", ForeignKey("fixed_compensations.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


class PayrollSetting(Base):
    __tablename__ = "payroll_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    minimum_wage_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    deduction_config: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    basic_salary_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("1.0000"), nullable=False
    )
    basic_salary_step_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("1.0000"), nullable=False
    )
    basic_salary_steps: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_position_rank: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Mp2Account(Base):
    __tablename__ = "mp2_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    users = relationship("User", secondary=mp2_users)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    salary_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    departments = relationship("Department", secondary=position_departments)


class FixedCompensation(Base):
    __tablename__ = "fixed_compensations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    users = relationship("User", secondary=fixed_compensation_users)


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "month",
            "year",
            "period",
            name="uq_payslips_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    rank: Mapped[str | None] = mapped_column(String(500), nullable=True)
    salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    period: Mapped[str | None] = mapped_column(String(3), nullable=True)
    released: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="payslips")
    variable_compensations = relationship(
        "PayslipVariableCompensation", back_populates="payslip", cascade="all, delete-orphan"
    )
    variable_deductions = relationship(
        "PayslipVariableDeduction", back_populates="payslip", cascade="all, delete-orphan"
    )


class PayslipVariableCompensation(Base):
    __tablename__ = "payslip_variable_compensations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payslip_id: Mapped[int] = mapped_column(ForeignKey("payslips.id"), index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    payslip = relationship("Payslip", back_populates="variable_compensations")


class PayslipVariableDeduction(Base):
    __tablename__ = "payslip_variable_deductions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payslip_id: Mapped[int] = mapped_column(ForeignKey("payslips.id"), index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    payslip = relationship("Payslip", back_populates="variable_deductions")


class ThirteenthMonthPay(Base):
    __tablename__ = "thirteenth_month_pays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    released: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="thirteenth_month_pays")
    variable_deductions = relationship(
        "ThirteenthMonthPayVariableDeduction",
        back_populates="thirteenth_month_pay",
        cascade="all, delete-orphan",
    )


class ThirteenthMonthPayVariableDeduction(Base):
    __tablename__ = "thirteenth_month_pay_variable_deductions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thirteenth_month_pay_id: Mapped[int] = mapped_column(
        ForeignKey("thirteenth_month_pays.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    thirteenth_month_pay = relationship(
        "ThirteenthMonthPay", back_populates="variable_deductions"
    )


class PayrollPolicyVersion(Base):
    __tablename__ = "payroll_policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_key", "version_label", name="uq_policy_key_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version_label: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PolicySssBracket(Base):
    __tablename__ = "policy_sss_brackets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=False, index=True
    )
    min_compensation: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_compensation: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    employee_share: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    employer_share: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PolicyPhilhealthRule(Base):
    __tablename__ = "policy_philhealth_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=False, index=True
    )
    min_compensation: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_compensation: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    employee_share_ratio: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), default=Decimal("0.500000"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PolicyPagibigRule(Base):
    __tablename__ = "policy_pagibig_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=False, index=True
    )
    min_compensation: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    monthly_compensation_cap: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    employee_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    employer_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_employee_share: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_employer_share: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PolicyBirWithholdingBracket(Base):
    __tablename__ = "policy_bir_withholding_brackets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=False, index=True
    )
    payroll_period: Mapped[str] = mapped_column(String(20), nullable=False)
    min_compensation: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_compensation: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    base_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    marginal_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    over_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PolicyMinimumWageOrder(Base):
    __tablename__ = "policy_min_wage_orders"
    __table_args__ = (
        UniqueConstraint("region_code", "effective_from", name="uq_min_wage_region_effective"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=False, index=True
    )
    region_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sector: Mapped[str] = mapped_column(String(50), default="GENERAL", nullable=False)
    daily_wage_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint("month", "year", "period", name="uq_payroll_runs_period"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_payroll_runs_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    policy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PayrollRunItem(Base):
    __tablename__ = "payroll_run_items"
    __table_args__ = (
        UniqueConstraint("payroll_run_id", "user_id", name="uq_payroll_run_items_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payroll_run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    payslip_id: Mapped[int | None] = mapped_column(ForeignKey("payslips.id"), nullable=True)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PayrollAdjustment(Base):
    __tablename__ = "payroll_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    payroll_run_id: Mapped[int | None] = mapped_column(ForeignKey("payroll_runs.id"), nullable=True)
    payslip_id: Mapped[int | None] = mapped_column(ForeignKey("payslips.id"), nullable=True)
    adjustment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PayslipEvent(Base):
    __tablename__ = "payslip_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payslip_id: Mapped[int] = mapped_column(ForeignKey("payslips.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class PayrollPolicySource(Base):
    __tablename__ = "payroll_policy_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_policy_versions.id"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_code: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    applied_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
