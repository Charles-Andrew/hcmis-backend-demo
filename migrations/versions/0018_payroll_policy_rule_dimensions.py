"""add payroll policy rule dimensions for PH statutory support

Revision ID: 0018_payroll_policy_rule_dims
Revises: 0017_payroll_policy_foundation
Create Date: 2026-04-05 23:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_payroll_policy_rule_dims"
down_revision = "0017_payroll_policy_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policy_pagibig_rules",
        sa.Column(
            "min_compensation",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "policy_min_wage_orders",
        sa.Column("sector", sa.String(length=50), nullable=False, server_default="GENERAL"),
    )


def downgrade() -> None:
    op.drop_column("policy_min_wage_orders", "sector")
    op.drop_column("policy_pagibig_rules", "min_compensation")
