"""drop holiday is_regular

Revision ID: 0036_drop_holiday_is_regular
Revises: 0035_holiday_constraints
Create Date: 2026-04-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0036_drop_holiday_is_regular"
down_revision: str | None = "0035_holiday_constraints"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("holidays", "is_regular")


def downgrade() -> None:
    op.add_column(
        "holidays",
        sa.Column("is_regular", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
