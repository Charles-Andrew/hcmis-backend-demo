from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.time import utc_now
from app.models.base import Base

job_departments = Table(
    "job_departments",
    Base.metadata,
    Column("job_id", ForeignKey("jobs.id"), primary_key=True),
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
    max_job_rank: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
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


class Job(Base):
    __tablename__ = "jobs"

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

    departments = relationship("Department", secondary=job_departments)


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
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
