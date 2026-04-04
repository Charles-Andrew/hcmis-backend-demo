"""user password reset

Revision ID: 0015_user_password_reset
Revises: 0014_attendance_raw_event_id
Create Date: 2026-04-04 16:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_user_password_reset"
down_revision = "0014_attendance_raw_event_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("temporary_password_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("users", "must_change_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "temporary_password_expires_at")
    op.drop_column("users", "must_change_password")
