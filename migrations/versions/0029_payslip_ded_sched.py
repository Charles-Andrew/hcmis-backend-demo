"""snapshot deduction schedule on payslips

Revision ID: 0029_payslip_ded_sched
Revises: 0028_auto_deduction_schedule
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0029_payslip_ded_sched"
down_revision = "0028_auto_deduction_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payslips",
        sa.Column("automatic_deduction_schedule", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "ck_payslips_automatic_deduction_schedule",
        "payslips",
        "automatic_deduction_schedule IS NULL OR automatic_deduction_schedule IN "
        "('SECOND_CUTOFF_ONLY', 'SPLIT_BOTH_CUTOFFS')",
    )
    op.execute(
        """
        UPDATE payslips
        SET automatic_deduction_schedule = (
            SELECT payroll_settings.automatic_deduction_schedule
            FROM payroll_settings
            ORDER BY payroll_settings.id
            LIMIT 1
        )
        WHERE automatic_deduction_schedule IS NULL
        """
    )
    op.alter_column(
        "payslips",
        "automatic_deduction_schedule",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_payslips_automatic_deduction_schedule",
        "payslips",
        type_="check",
    )
    op.drop_column("payslips", "automatic_deduction_schedule")
