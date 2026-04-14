"""add punch and time to certificate attendance requests

Revision ID: 0046_cert_att_punch_time
Revises: 0045_special_requests_core
Create Date: 2026-04-14 00:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0046_cert_att_punch_time"
down_revision: Union[str, None] = "0045_special_requests_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "certificate_attendance_requests",
        sa.Column("time", sa.Time(), nullable=True),
    )
    op.add_column(
        "certificate_attendance_requests",
        sa.Column("punch", sa.String(length=6), nullable=True),
    )

    op.execute(
        """
        UPDATE certificate_attendance_requests
        SET time = COALESCE(time, TIME '00:00:00'),
            punch = COALESCE(punch, 'IN')
        """
    )

    op.alter_column("certificate_attendance_requests", "time", nullable=False)
    op.alter_column("certificate_attendance_requests", "punch", nullable=False)


def downgrade() -> None:
    op.drop_column("certificate_attendance_requests", "punch")
    op.drop_column("certificate_attendance_requests", "time")
