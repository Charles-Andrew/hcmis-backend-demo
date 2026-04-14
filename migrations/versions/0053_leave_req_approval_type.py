"""add leave request approval type

Revision ID: 0053_leave_req_approval_type
Revises: 0052_clear_leave_types
Create Date: 2026-04-15 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0053_leave_req_approval_type"
down_revision = "0052_clear_leave_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leave_requests",
        sa.Column("approval_type", sa.String(length=20), nullable=True),
    )
    op.create_index(
        op.f("ix_leave_requests_approval_type"),
        "leave_requests",
        ["approval_type"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_leave_requests_approval_type",
        "leave_requests",
        "approval_type IN ('PAID', 'NON_PAID') OR approval_type IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_leave_requests_approval_type", "leave_requests", type_="check")
    op.drop_index(op.f("ix_leave_requests_approval_type"), table_name="leave_requests")
    op.drop_column("leave_requests", "approval_type")
