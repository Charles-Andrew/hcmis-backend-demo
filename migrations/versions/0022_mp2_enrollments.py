"""add mp2 enrollments

Revision ID: 0022_mp2_enrollments
Revises: 0021_min_wage_policy_version
Create Date: 2026-04-07 23:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0022_mp2_enrollments"
down_revision = "0021_min_wage_policy_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mp2_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("mp2_account_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'ended')",
            name="ck_mp2_enrollments_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_mp2_enrollments_user_id"), "mp2_enrollments", ["user_id"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO mp2_enrollments (
                user_id,
                amount,
                effective_from,
                effective_to,
                status,
                mp2_account_number,
                notes,
                created_at,
                updated_at
            )
            SELECT
                mu.user_id,
                ma.amount,
                CAST(COALESCE(ma.created_at, ma.updated_at, NOW()) AS DATE),
                NULL,
                'active',
                NULL,
                'Backfilled from legacy MP2 membership settings.',
                COALESCE(ma.created_at, NOW()),
                COALESCE(ma.updated_at, NOW())
            FROM mp2_users mu
            JOIN mp2_accounts ma ON ma.id = mu.mp2_id
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_mp2_enrollments_user_id"), table_name="mp2_enrollments")
    op.drop_table("mp2_enrollments")
