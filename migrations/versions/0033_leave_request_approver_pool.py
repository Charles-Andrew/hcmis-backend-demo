"""add leave request approver pool

Revision ID: 0033_leave_request_pool
Revises: 0032_thirteenth_month_v1
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0033_leave_request_pool"
down_revision = "0032_thirteenth_month_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leave_request_approvers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("leave_request_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["leave_request_id"], ["leave_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "leave_request_id",
            "approver_id",
            name="uq_leave_request_approvers_leave_request_id_approver_id",
        ),
    )
    op.create_index(
        op.f("ix_leave_request_approvers_id"),
        "leave_request_approvers",
        ["id"],
    )
    op.create_index(
        op.f("ix_leave_request_approvers_leave_request_id"),
        "leave_request_approvers",
        ["leave_request_id"],
    )
    op.create_index(
        op.f("ix_leave_request_approvers_approver_id"),
        "leave_request_approvers",
        ["approver_id"],
    )
    op.create_index(
        op.f("ix_leave_request_approvers_status"),
        "leave_request_approvers",
        ["status"],
    )

    op.execute(
        """
        INSERT INTO leave_request_approvers (
            leave_request_id,
            approver_id,
            status,
            acted_at,
            created_at,
            updated_at
        )
        SELECT
            id AS leave_request_id,
            first_approver_id AS approver_id,
            COALESCE(first_approver_status, 'PENDING') AS status,
            first_approver_at AS acted_at,
            created_at,
            updated_at
        FROM leave_requests
        WHERE first_approver_id IS NOT NULL
        ON CONFLICT (leave_request_id, approver_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO leave_request_approvers (
            leave_request_id,
            approver_id,
            status,
            acted_at,
            created_at,
            updated_at
        )
        SELECT
            id AS leave_request_id,
            second_approver_id AS approver_id,
            COALESCE(second_approver_status, 'PENDING') AS status,
            second_approver_at AS acted_at,
            created_at,
            updated_at
        FROM leave_requests
        WHERE second_approver_id IS NOT NULL
        ON CONFLICT (leave_request_id, approver_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_leave_request_approvers_status"), table_name="leave_request_approvers")
    op.drop_index(
        op.f("ix_leave_request_approvers_approver_id"),
        table_name="leave_request_approvers",
    )
    op.drop_index(
        op.f("ix_leave_request_approvers_leave_request_id"),
        table_name="leave_request_approvers",
    )
    op.drop_index(op.f("ix_leave_request_approvers_id"), table_name="leave_request_approvers")
    op.drop_table("leave_request_approvers")
