"""add automatic deduction schedule to payroll settings

Revision ID: 0028_auto_deduction_schedule
Revises: 0027_user_position_assignments
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0028_auto_deduction_schedule"
down_revision = "0027_user_position_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payroll_settings",
        sa.Column(
            "automatic_deduction_schedule",
            sa.String(length=32),
            nullable=False,
            server_default="SECOND_CUTOFF_ONLY",
        ),
    )
    op.create_check_constraint(
        "ck_payroll_settings_automatic_deduction_schedule",
        "payroll_settings",
        "automatic_deduction_schedule IN ('SECOND_CUTOFF_ONLY', 'SPLIT_BOTH_CUTOFFS')",
    )
    op.alter_column(
        "payroll_settings",
        "automatic_deduction_schedule",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_payroll_settings_automatic_deduction_schedule",
        "payroll_settings",
        type_="check",
    )
    op.drop_column("payroll_settings", "automatic_deduction_schedule")
