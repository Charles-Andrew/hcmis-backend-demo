"""add user employment movement history

Revision ID: 0049_user_emp_movements
Revises: 0048_drop_cert_att_type
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0049_user_emp_movements"
down_revision: str | None = "0048_drop_cert_att_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_employment_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.String(length=500), nullable=True),
        sa.Column("new_value", sa.String(length=500), nullable=True),
        sa.Column("change_batch_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_employment_movements_id"),
        "user_employment_movements",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_employment_movements_user_id"),
        "user_employment_movements",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_employment_movements_field_name"),
        "user_employment_movements",
        ["field_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_employment_movements_change_batch_id"),
        "user_employment_movements",
        ["change_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_employment_movements_changed_by"),
        "user_employment_movements",
        ["changed_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_employment_movements_changed_at"),
        "user_employment_movements",
        ["changed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_employment_movements_changed_at"),
        table_name="user_employment_movements",
    )
    op.drop_index(
        op.f("ix_user_employment_movements_changed_by"),
        table_name="user_employment_movements",
    )
    op.drop_index(
        op.f("ix_user_employment_movements_change_batch_id"),
        table_name="user_employment_movements",
    )
    op.drop_index(
        op.f("ix_user_employment_movements_field_name"),
        table_name="user_employment_movements",
    )
    op.drop_index(
        op.f("ix_user_employment_movements_user_id"),
        table_name="user_employment_movements",
    )
    op.drop_index(
        op.f("ix_user_employment_movements_id"),
        table_name="user_employment_movements",
    )
    op.drop_table("user_employment_movements")
