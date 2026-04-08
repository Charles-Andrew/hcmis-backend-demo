"""rework thirteenth month as first version

Revision ID: 0032_thirteenth_month_v1
Revises: 0031_drop_legacy_runs
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0032_thirteenth_month_v1"
down_revision = "0031_drop_legacy_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        op.f("ix_thirteenth_month_pay_variable_deductions_id"),
        table_name="thirteenth_month_pay_variable_deductions",
    )
    op.drop_table("thirteenth_month_pay_variable_deductions")
    op.drop_index(op.f("ix_thirteenth_month_pays_id"), table_name="thirteenth_month_pays")
    op.drop_table("thirteenth_month_pays")

    op.create_table(
        "thirteenth_month_payouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'RELEASED')",
            name="ck_thirteenth_month_payouts_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "year", name="uq_thirteenth_month_payout_user_year"),
    )
    op.create_index(op.f("ix_thirteenth_month_payouts_id"), "thirteenth_month_payouts", ["id"])
    op.create_index(
        op.f("ix_thirteenth_month_payouts_user_id"),
        "thirteenth_month_payouts",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_thirteenth_month_payouts_year"),
        "thirteenth_month_payouts",
        ["year"],
    )

    op.create_table(
        "thirteenth_month_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payout_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "type IN ('ADD', 'DEDUCT')",
            name="ck_thirteenth_month_adjustments_type",
        ),
        sa.ForeignKeyConstraint(["payout_id"], ["thirteenth_month_payouts.id"]),
    )
    op.create_index(
        op.f("ix_thirteenth_month_adjustments_id"), "thirteenth_month_adjustments", ["id"]
    )
    op.create_index(
        op.f("ix_thirteenth_month_adjustments_payout_id"),
        "thirteenth_month_adjustments",
        ["payout_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_thirteenth_month_adjustments_payout_id"),
        table_name="thirteenth_month_adjustments",
    )
    op.drop_index(op.f("ix_thirteenth_month_adjustments_id"), table_name="thirteenth_month_adjustments")
    op.drop_table("thirteenth_month_adjustments")

    op.drop_index(op.f("ix_thirteenth_month_payouts_year"), table_name="thirteenth_month_payouts")
    op.drop_index(op.f("ix_thirteenth_month_payouts_user_id"), table_name="thirteenth_month_payouts")
    op.drop_index(op.f("ix_thirteenth_month_payouts_id"), table_name="thirteenth_month_payouts")
    op.drop_table("thirteenth_month_payouts")

    op.create_table(
        "thirteenth_month_pays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_thirteenth_month_pays_id"), "thirteenth_month_pays", ["id"], unique=False)

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
