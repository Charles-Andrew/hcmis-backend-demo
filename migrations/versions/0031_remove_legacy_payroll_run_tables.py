"""remove legacy payroll run tables

Revision ID: 0031_drop_legacy_runs
Revises: 0030_overtime_approvers
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0031_drop_legacy_runs"
down_revision = "0030_overtime_approvers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("payroll_run_input_audits")
    op.drop_table("payroll_run_inputs")
    op.drop_table("payroll_item_types")
    op.drop_table("payroll_run_items")
    op.execute("ALTER TABLE payroll_adjustments DROP COLUMN IF EXISTS payroll_run_id CASCADE")
    op.drop_table("payroll_runs")


def downgrade() -> None:
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
    op.create_index(op.f("ix_payroll_run_items_id"), "payroll_run_items", ["id"], unique=False)
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

    op.add_column("payroll_adjustments", sa.Column("payroll_run_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_payroll_adjustments_payroll_run_id_payroll_runs",
        "payroll_adjustments",
        "payroll_runs",
        ["payroll_run_id"],
        ["id"],
    )

    op.create_table(
        "payroll_item_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("behavior", sa.String(length=20), nullable=False),
        sa.Column("taxable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('earning', 'deduction')",
            name="ck_payroll_item_types_category",
        ),
        sa.CheckConstraint(
            "behavior IN ('fixed', 'formula', 'variable')",
            name="ck_payroll_item_types_behavior",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_payroll_item_types_code"),
    )
    op.create_index(
        op.f("ix_payroll_item_types_code"), "payroll_item_types", ["code"], unique=False
    )
    op.create_index(op.f("ix_payroll_item_types_id"), "payroll_item_types", ["id"], unique=False)

    op.create_table(
        "payroll_run_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_run_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("payroll_item_type_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('manual', 'import', 'system')",
            name="ck_payroll_run_inputs_source",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved')",
            name="ck_payroll_run_inputs_status",
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["payroll_item_type_id"], ["payroll_item_types.id"]),
        sa.ForeignKeyConstraint(["payroll_run_id"], ["payroll_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payroll_run_inputs_id"), "payroll_run_inputs", ["id"], unique=False)
    op.create_index(
        op.f("ix_payroll_run_inputs_payroll_item_type_id"),
        "payroll_run_inputs",
        ["payroll_item_type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_run_inputs_payroll_run_id"),
        "payroll_run_inputs",
        ["payroll_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_run_inputs_user_id"),
        "payroll_run_inputs",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "payroll_run_input_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_run_input_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["payroll_run_input_id"], ["payroll_run_inputs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payroll_run_input_audits_id"),
        "payroll_run_input_audits",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_run_input_audits_payroll_run_input_id"),
        "payroll_run_input_audits",
        ["payroll_run_input_id"],
        unique=False,
    )
