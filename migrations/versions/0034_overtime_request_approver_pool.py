"""add overtime request approver pool

Revision ID: 0034_overtime_request_pool
Revises: 0033_leave_request_pool
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0034_overtime_request_pool"
down_revision = "0033_leave_request_pool"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "overtime_request_approvers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("overtime_request_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=4), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["overtime_request_id"], ["overtime_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "overtime_request_id",
            "approver_id",
            name="uq_overtime_request_approvers_overtime_request_id_approver_id",
        ),
    )
    op.create_index(
        op.f("ix_overtime_request_approvers_id"),
        "overtime_request_approvers",
        ["id"],
    )
    op.create_index(
        op.f("ix_overtime_request_approvers_overtime_request_id"),
        "overtime_request_approvers",
        ["overtime_request_id"],
    )
    op.create_index(
        op.f("ix_overtime_request_approvers_approver_id"),
        "overtime_request_approvers",
        ["approver_id"],
    )
    op.create_index(
        op.f("ix_overtime_request_approvers_status"),
        "overtime_request_approvers",
        ["status"],
    )

    op.execute(
        """
        INSERT INTO overtime_request_approvers (
            overtime_request_id,
            approver_id,
            status,
            acted_at,
            created_at,
            updated_at
        )
        SELECT
            id AS overtime_request_id,
            approver_id,
            COALESCE(status, 'PEND') AS status,
            CASE WHEN status = 'PEND' THEN NULL ELSE updated_at END AS acted_at,
            created_at,
            updated_at
        FROM overtime_requests
        WHERE approver_id IS NOT NULL
        ON CONFLICT (overtime_request_id, approver_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_overtime_request_approvers_status"),
        table_name="overtime_request_approvers",
    )
    op.drop_index(
        op.f("ix_overtime_request_approvers_approver_id"),
        table_name="overtime_request_approvers",
    )
    op.drop_index(
        op.f("ix_overtime_request_approvers_overtime_request_id"),
        table_name="overtime_request_approvers",
    )
    op.drop_index(
        op.f("ix_overtime_request_approvers_id"),
        table_name="overtime_request_approvers",
    )
    op.drop_table("overtime_request_approvers")
