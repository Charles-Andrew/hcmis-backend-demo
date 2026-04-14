"""align trainings status to pending/completed

Revision ID: 0055_trainings_status_pending
Revises: 0054_trainings_core
Create Date: 2026-04-15 00:00:04.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0055_trainings_status_pending"
down_revision = "0054_trainings_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE trainings SET status = 'pending' WHERE status = 'draft'")
    op.drop_constraint("ck_trainings_status", "trainings", type_="check")
    op.create_check_constraint(
        "ck_trainings_status",
        "trainings",
        "status IN ('pending', 'completed')",
    )
    op.alter_column(
        "trainings",
        "status",
        existing_type=sa.String(length=20),
        server_default="pending",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("UPDATE trainings SET status = 'draft' WHERE status = 'pending'")
    op.drop_constraint("ck_trainings_status", "trainings", type_="check")
    op.create_check_constraint(
        "ck_trainings_status",
        "trainings",
        "status IN ('draft', 'completed')",
    )
    op.alter_column(
        "trainings",
        "status",
        existing_type=sa.String(length=20),
        server_default="draft",
        existing_nullable=False,
    )
