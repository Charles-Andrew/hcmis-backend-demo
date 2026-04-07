"""drop legacy mp2 tables

Revision ID: 0023_drop_legacy_mp2_tables
Revises: 0022_mp2_enrollments
Create Date: 2026-04-08 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0023_drop_legacy_mp2_tables"
down_revision = "0022_mp2_enrollments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("mp2_users")
    op.drop_table("mp2_accounts")


def downgrade() -> None:
    op.create_table(
        "mp2_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "mp2_users",
        sa.Column("mp2_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["mp2_id"], ["mp2_accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("mp2_id", "user_id"),
    )
