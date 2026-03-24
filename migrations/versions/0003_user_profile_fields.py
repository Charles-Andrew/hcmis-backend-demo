"""add remaining user profile fields

Revision ID: 0003_user_profile_fields
Revises: 0002_app_logs
Create Date: 2026-03-24 00:00:02.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_user_profile_fields"
down_revision: str | None = "0002_app_logs"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gender", sa.String(length=10), nullable=True))
    op.add_column("users", sa.Column("education", sa.String(length=10), nullable=True))
    op.add_column(
        "users", sa.Column("civil_status", sa.String(length=10), nullable=True)
    )
    op.add_column("users", sa.Column("religion", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("rank", sa.String(length=100), nullable=True))
    op.add_column(
        "users",
        sa.Column("can_modify_shift", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "can_modify_shift")
    op.drop_column("users", "rank")
    op.drop_column("users", "religion")
    op.drop_column("users", "civil_status")
    op.drop_column("users", "education")
    op.drop_column("users", "gender")

