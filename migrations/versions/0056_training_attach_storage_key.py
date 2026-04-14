"""add training attachment storage key

Revision ID: 0056_training_attach_storage_key
Revises: 0055_trainings_status_pending
Create Date: 2026-04-15 00:00:05.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0056_training_attach_storage_key"
down_revision = "0055_trainings_status_pending"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "training_participant_attachments",
        sa.Column("storage_key", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("training_participant_attachments", "storage_key")
