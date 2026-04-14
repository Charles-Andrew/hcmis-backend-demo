"""clear leave types

Revision ID: 0052_clear_leave_types
Revises: 0051_leave_types
Create Date: 2026-04-15 00:00:01.000000
"""

from alembic import op


revision = "0052_clear_leave_types"
down_revision = "0051_leave_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM leave_types")


def downgrade() -> None:
    # Data-only cleanup migration; no downgrade data restoration.
    pass
