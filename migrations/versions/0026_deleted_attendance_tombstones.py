"""add deleted attendance tombstones

Revision ID: 0026_deleted_attendance_tombs
Revises: 0025_payroll_run_inputs_items
Create Date: 2026-04-08 16:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0026_deleted_attendance_tombs"
down_revision = "0025_payroll_run_inputs_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deleted_attendance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_event_id", sa.String(length=64), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_event_id", name="uq_deleted_attendance_records_raw_event_id"),
    )
    op.create_index(
        op.f("ix_deleted_attendance_records_id"),
        "deleted_attendance_records",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deleted_attendance_records_raw_event_id"),
        "deleted_attendance_records",
        ["raw_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_deleted_attendance_records_raw_event_id"),
        table_name="deleted_attendance_records",
    )
    op.drop_index(
        op.f("ix_deleted_attendance_records_id"),
        table_name="deleted_attendance_records",
    )
    op.drop_table("deleted_attendance_records")
