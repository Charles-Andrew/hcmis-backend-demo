"""rework payroll statutory rule contracts

Revision ID: 0019_payroll_statutory_rule_contract_rework
Revises: 0018_payroll_policy_rule_dimensions
Create Date: 2026-04-07 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_payroll_statutory_rule_contract_rework"
down_revision = "0019_payroll_policy_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policy_sss_brackets",
        sa.Column("compensation_range_from", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column("compensation_range_to", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column(
            "monthly_salary_credit",
            sa.Numeric(12, 2),
            nullable=True,
        ),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column(
            "employee_contribution",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column(
            "employer_contribution",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column(
            "ec_contribution",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column(
            "mpf_employee_contribution",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column(
            "mpf_employer_contribution",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "policy_sss_brackets",
        sa.Column("source_reference", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "policy_philhealth_rules",
        sa.Column("compensation_range_from", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_philhealth_rules",
        sa.Column("compensation_range_to", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_philhealth_rules",
        sa.Column("premium_rate", sa.Numeric(8, 6), nullable=True),
    )
    op.add_column(
        "policy_philhealth_rules",
        sa.Column(
            "employer_share_ratio",
            sa.Numeric(8, 6),
            nullable=False,
            server_default="0.500000",
        ),
    )
    op.add_column(
        "policy_philhealth_rules",
        sa.Column("source_reference", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "policy_pagibig_rules",
        sa.Column("compensation_range_from", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_pagibig_rules",
        sa.Column("compensation_range_to", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_pagibig_rules",
        sa.Column("compensation_cap", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_pagibig_rules",
        sa.Column("employee_share_cap", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_pagibig_rules",
        sa.Column("employer_share_cap", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_pagibig_rules",
        sa.Column("source_reference", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "policy_bir_withholding_brackets",
        sa.Column("compensation_range_from", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_bir_withholding_brackets",
        sa.Column("compensation_range_to", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_bir_withholding_brackets",
        sa.Column("excess_over", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "policy_bir_withholding_brackets",
        sa.Column("source_reference", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "policy_min_wage_orders",
        sa.Column("daily_rate", sa.Numeric(12, 2), nullable=True),
    )

    op.add_column(
        "payroll_policy_sources",
        sa.Column("document_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "payroll_policy_sources",
        sa.Column("title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "payroll_policy_sources",
        sa.Column("published_at", sa.Date(), nullable=True),
    )

    op.execute(
        """
        UPDATE policy_sss_brackets
        SET compensation_range_from = min_compensation,
            compensation_range_to = max_compensation,
            monthly_salary_credit = max_compensation,
            employee_contribution = employee_share,
            employer_contribution = employer_share,
            ec_contribution = 0,
            mpf_employee_contribution = 0,
            mpf_employer_contribution = 0
        """
    )
    op.execute(
        """
        UPDATE policy_philhealth_rules
        SET compensation_range_from = min_compensation,
            compensation_range_to = max_compensation,
            premium_rate = rate,
            employer_share_ratio = 1 - employee_share_ratio
        """
    )
    op.execute(
        """
        UPDATE policy_pagibig_rules
        SET compensation_range_from = min_compensation,
            compensation_range_to = NULL,
            compensation_cap = monthly_compensation_cap,
            employee_share_cap = max_employee_share,
            employer_share_cap = max_employer_share
        """
    )
    op.execute(
        """
        UPDATE policy_bir_withholding_brackets
        SET compensation_range_from = min_compensation,
            compensation_range_to = max_compensation,
            excess_over = over_amount
        """
    )
    op.execute(
        """
        UPDATE policy_min_wage_orders
        SET daily_rate = daily_wage_amount
        """
    )
    op.execute(
        """
        UPDATE payroll_policy_sources
        SET document_type = source_type,
            title = reference_code
        """
    )

    op.alter_column("policy_sss_brackets", "compensation_range_from", nullable=False)
    op.alter_column("policy_sss_brackets", "compensation_range_to", nullable=False)
    op.alter_column("policy_sss_brackets", "monthly_salary_credit", nullable=False)
    op.alter_column("policy_philhealth_rules", "compensation_range_from", nullable=False)
    op.alter_column("policy_philhealth_rules", "compensation_range_to", nullable=False)
    op.alter_column("policy_philhealth_rules", "premium_rate", nullable=False)
    op.alter_column("policy_pagibig_rules", "compensation_range_from", nullable=False)
    op.alter_column("policy_pagibig_rules", "compensation_cap", nullable=False)
    op.alter_column(
        "policy_bir_withholding_brackets",
        "compensation_range_from",
        nullable=False,
    )
    op.alter_column("policy_bir_withholding_brackets", "excess_over", nullable=False)
    op.alter_column("policy_min_wage_orders", "daily_rate", nullable=False)
    op.alter_column("payroll_policy_sources", "document_type", nullable=False)
    op.alter_column("payroll_policy_sources", "title", nullable=False)


def downgrade() -> None:
    op.drop_column("payroll_policy_sources", "published_at")
    op.drop_column("payroll_policy_sources", "title")
    op.drop_column("payroll_policy_sources", "document_type")
    op.drop_column("policy_min_wage_orders", "daily_rate")
    op.drop_column("policy_bir_withholding_brackets", "source_reference")
    op.drop_column("policy_bir_withholding_brackets", "excess_over")
    op.drop_column("policy_bir_withholding_brackets", "compensation_range_to")
    op.drop_column("policy_bir_withholding_brackets", "compensation_range_from")
    op.drop_column("policy_pagibig_rules", "source_reference")
    op.drop_column("policy_pagibig_rules", "employer_share_cap")
    op.drop_column("policy_pagibig_rules", "employee_share_cap")
    op.drop_column("policy_pagibig_rules", "compensation_cap")
    op.drop_column("policy_pagibig_rules", "compensation_range_to")
    op.drop_column("policy_pagibig_rules", "compensation_range_from")
    op.drop_column("policy_philhealth_rules", "source_reference")
    op.drop_column("policy_philhealth_rules", "employer_share_ratio")
    op.drop_column("policy_philhealth_rules", "premium_rate")
    op.drop_column("policy_philhealth_rules", "compensation_range_to")
    op.drop_column("policy_philhealth_rules", "compensation_range_from")
    op.drop_column("policy_sss_brackets", "source_reference")
    op.drop_column("policy_sss_brackets", "mpf_employer_contribution")
    op.drop_column("policy_sss_brackets", "mpf_employee_contribution")
    op.drop_column("policy_sss_brackets", "ec_contribution")
    op.drop_column("policy_sss_brackets", "employer_contribution")
    op.drop_column("policy_sss_brackets", "employee_contribution")
    op.drop_column("policy_sss_brackets", "monthly_salary_credit")
    op.drop_column("policy_sss_brackets", "compensation_range_to")
    op.drop_column("policy_sss_brackets", "compensation_range_from")
