"""make minimum wage uniqueness sector-aware

Revision ID: 0020_min_wage_region_sector_eff
Revises: 0019_statutory_rule_rework
Create Date: 2026-04-07 22:30:00.000000
"""

from alembic import op


revision = "0020_min_wage_region_sector_eff"
down_revision = "0019_statutory_rule_rework"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_min_wage_region_effective",
        "policy_min_wage_orders",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_min_wage_region_sector_effective",
        "policy_min_wage_orders",
        ["region_code", "sector", "effective_from"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_min_wage_region_sector_effective",
        "policy_min_wage_orders",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_min_wage_region_effective",
        "policy_min_wage_orders",
        ["region_code", "effective_from"],
    )
