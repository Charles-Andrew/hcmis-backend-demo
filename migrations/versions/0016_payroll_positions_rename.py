"""rename payroll jobs domain to positions

Revision ID: 0016_payroll_positions_rename
Revises: 0015_user_password_reset
Create Date: 2026-04-05 12:35:00.000000
"""

from alembic import op


revision = "0016_payroll_positions_rename"
down_revision = "0015_user_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("jobs", "positions")
    op.rename_table("job_departments", "position_departments")
    op.alter_column("position_departments", "job_id", new_column_name="position_id")
    op.alter_column("payroll_settings", "max_job_rank", new_column_name="max_position_rank")
    op.execute("ALTER INDEX IF EXISTS ix_jobs_id RENAME TO ix_positions_id")
    op.execute("ALTER INDEX IF EXISTS ix_jobs_code RENAME TO ix_positions_code")


def downgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS ix_positions_id RENAME TO ix_jobs_id")
    op.execute("ALTER INDEX IF EXISTS ix_positions_code RENAME TO ix_jobs_code")
    op.alter_column("payroll_settings", "max_position_rank", new_column_name="max_job_rank")
    op.alter_column("position_departments", "position_id", new_column_name="job_id")
    op.rename_table("position_departments", "job_departments")
    op.rename_table("positions", "jobs")
