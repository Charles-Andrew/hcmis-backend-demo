"""payroll core

Revision ID: 0006_payroll_core
Revises: 0005_leave_core
Create Date: 2026-03-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_payroll_core"
down_revision = "0005_leave_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payroll_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "minimum_wage_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("deduction_config", sa.JSON(), nullable=False),
        sa.Column(
            "basic_salary_multiplier",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="1.0000",
        ),
        sa.Column(
            "basic_salary_step_multiplier",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="1.0000",
        ),
        sa.Column("basic_salary_steps", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_job_rank", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "mp2_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("salary_grade", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_jobs_id"), "jobs", ["id"], unique=False)
    op.create_index(op.f("ix_jobs_code"), "jobs", ["code"], unique=False)

    op.create_table(
        "job_departments",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("job_id", "department_id"),
    )

    op.create_table(
        "mp2_users",
        sa.Column("mp2_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["mp2_id"], ["mp2_accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("mp2_id", "user_id"),
    )

    op.create_table(
        "fixed_compensations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        op.f("ix_fixed_compensations_id"), "fixed_compensations", ["id"], unique=False
    )

    op.create_table(
        "fixed_compensation_users",
        sa.Column("fixed_compensation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["fixed_compensation_id"], ["fixed_compensations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("fixed_compensation_id", "user_id"),
    )

    op.create_table(
        "payslips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.String(length=500), nullable=True),
        sa.Column("salary", sa.Numeric(12, 2), nullable=True),
        sa.Column("period", sa.String(length=3), nullable=True),
        sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_payslips_id"), "payslips", ["id"], unique=False)
    op.create_index(op.f("ix_payslips_user_id"), "payslips", ["user_id"], unique=False)
    op.create_index(op.f("ix_payslips_month"), "payslips", ["month"], unique=False)
    op.create_index(op.f("ix_payslips_year"), "payslips", ["year"], unique=False)

    op.create_table(
        "payslip_variable_compensations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payslip_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"]),
    )
    op.create_index(
        op.f("ix_payslip_variable_compensations_id"),
        "payslip_variable_compensations",
        ["id"],
        unique=False,
    )

    op.create_table(
        "payslip_variable_deductions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payslip_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"]),
    )
    op.create_index(
        op.f("ix_payslip_variable_deductions_id"),
        "payslip_variable_deductions",
        ["id"],
        unique=False,
    )

    op.create_table(
        "thirteenth_month_pays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_thirteenth_month_pays_id"), "thirteenth_month_pays", ["id"], unique=False
    )

    op.create_table(
        "thirteenth_month_pay_variable_deductions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thirteenth_month_pay_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thirteenth_month_pay_id"], ["thirteenth_month_pays.id"]),
    )
    op.create_index(
        op.f("ix_thirteenth_month_pay_variable_deductions_id"),
        "thirteenth_month_pay_variable_deductions",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_thirteenth_month_pay_variable_deductions_id"),
        table_name="thirteenth_month_pay_variable_deductions",
    )
    op.drop_table("thirteenth_month_pay_variable_deductions")
    op.drop_index(op.f("ix_thirteenth_month_pays_id"), table_name="thirteenth_month_pays")
    op.drop_table("thirteenth_month_pays")
    op.drop_index(
        op.f("ix_payslip_variable_deductions_id"), table_name="payslip_variable_deductions"
    )
    op.drop_table("payslip_variable_deductions")
    op.drop_index(
        op.f("ix_payslip_variable_compensations_id"),
        table_name="payslip_variable_compensations",
    )
    op.drop_table("payslip_variable_compensations")
    op.drop_index(op.f("ix_payslips_year"), table_name="payslips")
    op.drop_index(op.f("ix_payslips_month"), table_name="payslips")
    op.drop_index(op.f("ix_payslips_user_id"), table_name="payslips")
    op.drop_index(op.f("ix_payslips_id"), table_name="payslips")
    op.drop_table("payslips")
    op.drop_table("fixed_compensation_users")
    op.drop_index(op.f("ix_fixed_compensations_id"), table_name="fixed_compensations")
    op.drop_table("fixed_compensations")
    op.drop_table("mp2_users")
    op.drop_table("job_departments")
    op.drop_index(op.f("ix_jobs_code"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_id"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("mp2_accounts")
    op.drop_table("payroll_settings")
