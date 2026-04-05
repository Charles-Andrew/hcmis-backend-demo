"""payroll policy and run foundation

Revision ID: 0017_payroll_policy_foundation
Revises: 0016_payroll_positions_rename
Create Date: 2026-04-05 23:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_payroll_policy_foundation"
down_revision = "0016_payroll_positions_rename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payroll_policy_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_key", sa.String(length=100), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("policy_key", "version_label", name="uq_policy_key_version"),
    )
    op.create_index(
        op.f("ix_payroll_policy_versions_id"),
        "payroll_policy_versions",
        ["id"],
        unique=False,
    )

    op.create_table(
        "policy_sss_brackets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("min_compensation", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_compensation", sa.Numeric(12, 2), nullable=False),
        sa.Column("employee_share", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("employer_share", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
    )
    op.create_index(op.f("ix_policy_sss_brackets_id"), "policy_sss_brackets", ["id"], unique=False)
    op.create_index(
        op.f("ix_policy_sss_brackets_policy_version_id"),
        "policy_sss_brackets",
        ["policy_version_id"],
        unique=False,
    )

    op.create_table(
        "policy_philhealth_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("min_compensation", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_compensation", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate", sa.Numeric(8, 6), nullable=False),
        sa.Column(
            "employee_share_ratio",
            sa.Numeric(8, 6),
            nullable=False,
            server_default="0.500000",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
    )
    op.create_index(
        op.f("ix_policy_philhealth_rules_id"),
        "policy_philhealth_rules",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_philhealth_rules_policy_version_id"),
        "policy_philhealth_rules",
        ["policy_version_id"],
        unique=False,
    )

    op.create_table(
        "policy_pagibig_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("monthly_compensation_cap", sa.Numeric(12, 2), nullable=False),
        sa.Column("employee_rate", sa.Numeric(8, 6), nullable=False),
        sa.Column("employer_rate", sa.Numeric(8, 6), nullable=False),
        sa.Column("max_employee_share", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_employer_share", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
    )
    op.create_index(
        op.f("ix_policy_pagibig_rules_id"),
        "policy_pagibig_rules",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_pagibig_rules_policy_version_id"),
        "policy_pagibig_rules",
        ["policy_version_id"],
        unique=False,
    )

    op.create_table(
        "policy_bir_withholding_brackets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("payroll_period", sa.String(length=20), nullable=False),
        sa.Column("min_compensation", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_compensation", sa.Numeric(12, 2), nullable=True),
        sa.Column("base_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("marginal_rate", sa.Numeric(8, 6), nullable=False),
        sa.Column("over_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
    )
    op.create_index(
        op.f("ix_policy_bir_withholding_brackets_id"),
        "policy_bir_withholding_brackets",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_bir_withholding_brackets_policy_version_id"),
        "policy_bir_withholding_brackets",
        ["policy_version_id"],
        unique=False,
    )

    op.create_table(
        "policy_min_wage_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("region_code", sa.String(length=20), nullable=False),
        sa.Column("daily_wage_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
        sa.UniqueConstraint("region_code", "effective_from", name="uq_min_wage_region_effective"),
    )
    op.create_index(
        op.f("ix_policy_min_wage_orders_id"),
        "policy_min_wage_orders",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_min_wage_orders_policy_version_id"),
        "policy_min_wage_orders",
        ["policy_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_min_wage_orders_region_code"),
        "policy_min_wage_orders",
        ["region_code"],
        unique=False,
    )

    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("policy_version_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_payroll_runs_month"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("month", "year", "period", name="uq_payroll_runs_period"),
    )
    op.create_index(op.f("ix_payroll_runs_id"), "payroll_runs", ["id"], unique=False)

    op.create_table(
        "payroll_run_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payroll_run_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("payslip_id", sa.Integer(), nullable=True),
        sa.Column("gross_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_deductions", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payroll_run_id"], ["payroll_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"]),
        sa.UniqueConstraint("payroll_run_id", "user_id", name="uq_payroll_run_items_user"),
    )
    op.create_index(
        op.f("ix_payroll_run_items_id"),
        "payroll_run_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_run_items_payroll_run_id"),
        "payroll_run_items",
        ["payroll_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_run_items_user_id"),
        "payroll_run_items",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "payroll_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("payroll_run_id", sa.Integer(), nullable=True),
        sa.Column("payslip_id", sa.Integer(), nullable=True),
        sa.Column("adjustment_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["payroll_run_id"], ["payroll_runs.id"]),
        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_payroll_adjustments_id"),
        "payroll_adjustments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_adjustments_user_id"),
        "payroll_adjustments",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "payslip_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payslip_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index(op.f("ix_payslip_events_id"), "payslip_events", ["id"], unique=False)
    op.create_index(
        op.f("ix_payslip_events_payslip_id"),
        "payslip_events",
        ["payslip_id"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_payslips_identity",
        "payslips",
        ["user_id", "month", "year", "period"],
    )
    op.create_check_constraint(
        "ck_fixed_compensations_month",
        "fixed_compensations",
        "month >= 1 AND month <= 12",
    )
    op.create_check_constraint(
        "ck_payslips_period",
        "payslips",
        "period IS NULL OR period IN ('1ST', '2ND')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payslips_period", "payslips", type_="check")
    op.drop_constraint("ck_fixed_compensations_month", "fixed_compensations", type_="check")
    op.drop_constraint("uq_payslips_identity", "payslips", type_="unique")

    op.drop_index(op.f("ix_payslip_events_payslip_id"), table_name="payslip_events")
    op.drop_index(op.f("ix_payslip_events_id"), table_name="payslip_events")
    op.drop_table("payslip_events")

    op.drop_index(op.f("ix_payroll_adjustments_user_id"), table_name="payroll_adjustments")
    op.drop_index(op.f("ix_payroll_adjustments_id"), table_name="payroll_adjustments")
    op.drop_table("payroll_adjustments")

    op.drop_index(op.f("ix_payroll_run_items_user_id"), table_name="payroll_run_items")
    op.drop_index(
        op.f("ix_payroll_run_items_payroll_run_id"),
        table_name="payroll_run_items",
    )
    op.drop_index(op.f("ix_payroll_run_items_id"), table_name="payroll_run_items")
    op.drop_table("payroll_run_items")

    op.drop_index(op.f("ix_payroll_runs_id"), table_name="payroll_runs")
    op.drop_table("payroll_runs")

    op.drop_index(
        op.f("ix_policy_min_wage_orders_region_code"),
        table_name="policy_min_wage_orders",
    )
    op.drop_index(
        op.f("ix_policy_min_wage_orders_policy_version_id"),
        table_name="policy_min_wage_orders",
    )
    op.drop_index(op.f("ix_policy_min_wage_orders_id"), table_name="policy_min_wage_orders")
    op.drop_table("policy_min_wage_orders")

    op.drop_index(
        op.f("ix_policy_bir_withholding_brackets_policy_version_id"),
        table_name="policy_bir_withholding_brackets",
    )
    op.drop_index(
        op.f("ix_policy_bir_withholding_brackets_id"),
        table_name="policy_bir_withholding_brackets",
    )
    op.drop_table("policy_bir_withholding_brackets")

    op.drop_index(
        op.f("ix_policy_pagibig_rules_policy_version_id"),
        table_name="policy_pagibig_rules",
    )
    op.drop_index(op.f("ix_policy_pagibig_rules_id"), table_name="policy_pagibig_rules")
    op.drop_table("policy_pagibig_rules")

    op.drop_index(
        op.f("ix_policy_philhealth_rules_policy_version_id"),
        table_name="policy_philhealth_rules",
    )
    op.drop_index(
        op.f("ix_policy_philhealth_rules_id"),
        table_name="policy_philhealth_rules",
    )
    op.drop_table("policy_philhealth_rules")

    op.drop_index(
        op.f("ix_policy_sss_brackets_policy_version_id"),
        table_name="policy_sss_brackets",
    )
    op.drop_index(op.f("ix_policy_sss_brackets_id"), table_name="policy_sss_brackets")
    op.drop_table("policy_sss_brackets")

    op.drop_index(op.f("ix_payroll_policy_versions_id"), table_name="payroll_policy_versions")
    op.drop_table("payroll_policy_versions")
