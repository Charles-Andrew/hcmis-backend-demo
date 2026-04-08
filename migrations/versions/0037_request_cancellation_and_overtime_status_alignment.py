"""align overtime statuses and add cancellable request history

Revision ID: 0037_req_cancel_ot_status
Revises: 0036_drop_holiday_is_regular
Create Date: 2026-04-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0037_req_cancel_ot_status"
down_revision = "0036_drop_holiday_is_regular"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "overtime_requests",
        "status",
        existing_type=sa.String(length=4),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default="PEND",
        server_default="PENDING",
    )
    op.alter_column(
        "overtime_request_approvers",
        "status",
        existing_type=sa.String(length=4),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default="PEND",
        server_default="PENDING",
    )

    op.execute(
        """
        UPDATE overtime_requests
        SET status = CASE status
            WHEN 'PEND' THEN 'PENDING'
            WHEN 'APP' THEN 'APPROVED'
            WHEN 'REJ' THEN 'REJECTED'
            ELSE status
        END
        """
    )
    op.execute(
        """
        UPDATE overtime_request_approvers
        SET status = CASE status
            WHEN 'PEND' THEN 'PENDING'
            WHEN 'APP' THEN 'APPROVED'
            WHEN 'REJ' THEN 'REJECTED'
            ELSE status
        END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE overtime_request_approvers
        SET status = CASE status
            WHEN 'PENDING' THEN 'PEND'
            WHEN 'APPROVED' THEN 'APP'
            WHEN 'REJECTED' THEN 'REJ'
            WHEN 'CANCELLED' THEN 'PEND'
            ELSE status
        END
        """
    )
    op.execute(
        """
        UPDATE overtime_requests
        SET status = CASE status
            WHEN 'PENDING' THEN 'PEND'
            WHEN 'APPROVED' THEN 'APP'
            WHEN 'REJECTED' THEN 'REJ'
            WHEN 'CANCELLED' THEN 'PEND'
            ELSE status
        END
        """
    )

    op.alter_column(
        "overtime_request_approvers",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=4),
        existing_nullable=False,
        existing_server_default="PENDING",
        server_default="PEND",
    )
    op.alter_column(
        "overtime_requests",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=4),
        existing_nullable=False,
        existing_server_default="PENDING",
        server_default="PEND",
    )
