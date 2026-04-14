"""leave types

Revision ID: 0051_leave_types
Revises: 0050_drop_emp_move_reason
Create Date: 2026-04-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0051_leave_types"
down_revision = "0050_drop_emp_move_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leave_types",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("max_credits", sa.Integer(), nullable=False),
        sa.Column("credit_mode", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "max_credits >= 0",
            name="ck_leave_types_max_credits_non_negative",
        ),
        sa.CheckConstraint(
            "credit_mode IN ('incremental', 'fixed')",
            name="ck_leave_types_credit_mode",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_leave_types_id"), "leave_types", ["id"], unique=False)
    op.create_index(op.f("ix_leave_types_code"), "leave_types", ["code"], unique=False)
    op.create_index(op.f("ix_leave_types_name"), "leave_types", ["name"], unique=False)

    op.alter_column(
        "leave_requests",
        "leave_type",
        existing_type=sa.String(length=2),
        type_=sa.String(length=24),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "leave_requests",
        "leave_type",
        existing_type=sa.String(length=24),
        type_=sa.String(length=2),
        existing_nullable=False,
    )

    op.drop_index(op.f("ix_leave_types_name"), table_name="leave_types")
    op.drop_index(op.f("ix_leave_types_code"), table_name="leave_types")
    op.drop_index(op.f("ix_leave_types_id"), table_name="leave_types")
    op.drop_table("leave_types")
