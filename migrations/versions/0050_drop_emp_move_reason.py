"""drop reason from user employment movements

Revision ID: 0050_drop_emp_move_reason
Revises: 0049_user_emp_movements
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0050_drop_emp_move_reason"
down_revision: str | None = "0049_user_emp_movements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("user_employment_movements")}
    if "reason" in column_names:
        op.drop_column("user_employment_movements", "reason")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("user_employment_movements")}
    if "reason" not in column_names:
        op.add_column(
            "user_employment_movements",
            sa.Column("reason", sa.String(length=500), nullable=True),
        )
