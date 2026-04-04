"""attendance raw event id

Revision ID: 0014_attendance_raw_event_id
Revises: 0013_bridge_user_snapshots
Create Date: 2026-04-04 00:00:08.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_attendance_raw_event_id"
down_revision = "0013_bridge_user_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendance_records",
        sa.Column("raw_event_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_attendance_records_raw_event_id",
        "attendance_records",
        ["raw_event_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_attendance_records_raw_event_id",
        "attendance_records",
        ["raw_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_attendance_records_raw_event_id",
        "attendance_records",
        type_="unique",
    )
    op.drop_index("ix_attendance_records_raw_event_id", table_name="attendance_records")
    op.drop_column("attendance_records", "raw_event_id")
