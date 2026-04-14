"""drop leftover type column from certificate attendance requests

Revision ID: 0048_drop_cert_att_type
Revises: 0047_cert_att_type
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0048_drop_cert_att_type"
down_revision: str | None = "0047_cert_att_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column["name"] for column in inspector.get_columns("certificate_attendance_requests")
    }
    if "type" in column_names:
        op.drop_column("certificate_attendance_requests", "type")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column["name"] for column in inspector.get_columns("certificate_attendance_requests")
    }
    if "type" not in column_names:
        op.add_column(
            "certificate_attendance_requests",
            sa.Column("type", sa.String(length=50), nullable=True),
        )
