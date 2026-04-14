"""add required training date

Revision ID: 0057_training_date_required
Revises: 0056_training_attach_storage_key
Create Date: 2026-04-15 00:00:07.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0057_training_date_required"
down_revision = "0056_training_attach_storage_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trainings", sa.Column("training_date", sa.Date(), nullable=True))
    op.execute("UPDATE trainings SET training_date = (created_at AT TIME ZONE 'UTC')::date WHERE training_date IS NULL")
    op.alter_column("trainings", "training_date", nullable=False)
    op.create_index(op.f("ix_trainings_training_date"), "trainings", ["training_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_trainings_training_date"), table_name="trainings")
    op.drop_column("trainings", "training_date")
