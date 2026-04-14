"""add employee type and employment status fields

Revision ID: 0044_user_emp_class_fields
Revises: 0043_user_shift_templates
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0044_user_emp_class_fields"
down_revision: Union[str, None] = "0043_user_shift_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("employee_type", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("employment_status", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "employment_status")
    op.drop_column("users", "employee_type")
