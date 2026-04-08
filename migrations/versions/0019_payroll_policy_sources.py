"""add payroll policy source metadata table

Revision ID: 0019_payroll_policy_sources
Revises: 0018_payroll_policy_rule_dims
Create Date: 2026-04-06 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_payroll_policy_sources"
down_revision = "0018_payroll_policy_rule_dims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payroll_policy_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("reference_code", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("applied_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_version_id"], ["payroll_policy_versions.id"]),
        sa.ForeignKeyConstraint(["applied_by"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_payroll_policy_sources_id"),
        "payroll_policy_sources",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payroll_policy_sources_policy_version_id"),
        "payroll_policy_sources",
        ["policy_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_payroll_policy_sources_policy_version_id"),
        table_name="payroll_policy_sources",
    )
    op.drop_index(op.f("ix_payroll_policy_sources_id"), table_name="payroll_policy_sources")
    op.drop_table("payroll_policy_sources")
