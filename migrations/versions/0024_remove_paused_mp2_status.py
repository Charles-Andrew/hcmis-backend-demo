"""remove paused mp2 status

Revision ID: 0024_remove_paused_mp2_status
Revises: 0023_drop_legacy_mp2_tables
Create Date: 2026-04-08 01:10:00.000000
"""

from alembic import op


revision = "0024_remove_paused_mp2_status"
down_revision = "0023_drop_legacy_mp2_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_mp2_enrollments_status", "mp2_enrollments", type_="check")
    op.create_check_constraint(
        "ck_mp2_enrollments_status",
        "mp2_enrollments",
        "status IN ('active', 'ended')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_mp2_enrollments_status", "mp2_enrollments", type_="check")
    op.create_check_constraint(
        "ck_mp2_enrollments_status",
        "mp2_enrollments",
        "status IN ('active', 'paused', 'ended')",
    )
