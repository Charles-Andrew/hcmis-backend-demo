"""add user shift templates mapping

Revision ID: 0043_user_shift_templates
Revises: 0042_highest_education_fields
Create Date: 2026-04-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0043_user_shift_templates"
down_revision: Union[str, None] = "0042_highest_education_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_shifts",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("shift_id", sa.Integer(), sa.ForeignKey("shifts.id"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "shift_id"),
    )

    op.execute(
        """
        INSERT INTO user_shifts (user_id, shift_id)
        SELECT users.id, department_shifts.shift_id
        FROM users
        JOIN department_shifts ON department_shifts.department_id = users.department_id
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("user_shifts")
