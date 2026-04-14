"""replace education with highest education fields

Revision ID: 0042_highest_education_fields
Revises: 0041_user_approver_distinct_ck
Create Date: 2026-04-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0042_highest_education_fields"
down_revision: Union[str, None] = "0041_user_approver_distinct_ck"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "education")
    op.add_column("users", sa.Column("highest_education_level", sa.String(length=10), nullable=True))
    op.add_column("users", sa.Column("highest_education_program", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "highest_education_program")
    op.drop_column("users", "highest_education_level")
    op.add_column("users", sa.Column("education", sa.String(length=10), nullable=True))
