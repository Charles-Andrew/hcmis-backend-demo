"""scope minimum wage uniqueness to policy version

Revision ID: 0021_min_wage_policy_version
Revises: 0020_min_wage_region_sector_eff
Create Date: 2026-04-07 22:45:00.000000
"""

from alembic import op


revision = "0021_min_wage_policy_version"
down_revision = "0020_min_wage_region_sector_eff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_min_wage_region_sector_effective",
        "policy_min_wage_orders",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_min_wage_policy_region_sector_effective",
        "policy_min_wage_orders",
        ["policy_version_id", "region_code", "sector", "effective_from"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_min_wage_policy_region_sector_effective",
        "policy_min_wage_orders",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_min_wage_region_sector_effective",
        "policy_min_wage_orders",
        ["region_code", "sector", "effective_from"],
    )
