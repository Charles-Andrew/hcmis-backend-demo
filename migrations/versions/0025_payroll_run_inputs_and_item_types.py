"""add payroll run inputs and item types

Revision ID: 0025_payroll_run_inputs_and_item_types
Revises: 0024_remove_paused_mp2_status
Create Date: 2026-04-08 11:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = "0025_payroll_run_inputs_and_item_types"
down_revision = "0024_remove_paused_mp2_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
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
    op.create_index(
        op.f("ix_payroll_item_types_id"), "payroll_item_types", ["id"], unique=False
    )

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
    op.create_index(
        op.f("ix_payroll_run_inputs_id"), "payroll_run_inputs", ["id"], unique=False
    )
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
        op.f("ix_payroll_run_inputs_user_id"), "payroll_run_inputs", ["user_id"], unique=False
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

    op.bulk_insert(
        sa.table(
            "payroll_item_types",
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("category", sa.String),
            sa.column("behavior", sa.String),
            sa.column("taxable", sa.Boolean),
            sa.column("is_active", sa.Boolean),
            sa.column("display_order", sa.Integer),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "code": "OVERTIME",
                "name": "Overtime",
                "category": "earning",
                "behavior": "variable",
                "taxable": True,
                "is_active": True,
                "display_order": 10,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "HOLIDAY_PAY",
                "name": "Holiday Pay",
                "category": "earning",
                "behavior": "variable",
                "taxable": True,
                "is_active": True,
                "display_order": 20,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "NIGHT_DIFF",
                "name": "Night Differential",
                "category": "earning",
                "behavior": "variable",
                "taxable": True,
                "is_active": True,
                "display_order": 30,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "BONUS",
                "name": "Bonus",
                "category": "earning",
                "behavior": "variable",
                "taxable": True,
                "is_active": True,
                "display_order": 40,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "ALLOWANCE_ADJ",
                "name": "Allowance Adjustment",
                "category": "earning",
                "behavior": "variable",
                "taxable": True,
                "is_active": True,
                "display_order": 50,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "RETRO_PAY",
                "name": "Retro Pay",
                "category": "earning",
                "behavior": "variable",
                "taxable": True,
                "is_active": True,
                "display_order": 60,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "LOAN",
                "name": "Loan Deduction",
                "category": "deduction",
                "behavior": "variable",
                "taxable": False,
                "is_active": True,
                "display_order": 110,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "CASH_ADVANCE",
                "name": "Cash Advance",
                "category": "deduction",
                "behavior": "variable",
                "taxable": False,
                "is_active": True,
                "display_order": 120,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "SALARY_ADJ",
                "name": "Salary Adjustment",
                "category": "deduction",
                "behavior": "variable",
                "taxable": False,
                "is_active": True,
                "display_order": 130,
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "ABSENCE_LATE_ADJ",
                "name": "Absence Or Late Adjustment",
                "category": "deduction",
                "behavior": "variable",
                "taxable": False,
                "is_active": True,
                "display_order": 140,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_payroll_run_input_audits_payroll_run_input_id"),
        table_name="payroll_run_input_audits",
    )
    op.drop_index(op.f("ix_payroll_run_input_audits_id"), table_name="payroll_run_input_audits")
    op.drop_table("payroll_run_input_audits")

    op.drop_index(op.f("ix_payroll_run_inputs_user_id"), table_name="payroll_run_inputs")
    op.drop_index(
        op.f("ix_payroll_run_inputs_payroll_run_id"), table_name="payroll_run_inputs"
    )
    op.drop_index(
        op.f("ix_payroll_run_inputs_payroll_item_type_id"), table_name="payroll_run_inputs"
    )
    op.drop_index(op.f("ix_payroll_run_inputs_id"), table_name="payroll_run_inputs")
    op.drop_table("payroll_run_inputs")

    op.drop_index(op.f("ix_payroll_item_types_id"), table_name="payroll_item_types")
    op.drop_index(op.f("ix_payroll_item_types_code"), table_name="payroll_item_types")
    op.drop_table("payroll_item_types")
