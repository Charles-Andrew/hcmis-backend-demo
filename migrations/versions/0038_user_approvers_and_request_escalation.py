"""add user-level approvers and per-request escalation audit fields

Revision ID: 0038_user_approver_escalation
Revises: 0037_req_cancel_ot_status
Create Date: 2026-04-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0038_user_approver_escalation"
down_revision = "0037_req_cancel_ot_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("level_1_approver_id", sa.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("level_2_approver_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_index(
        op.f("ix_users_level_1_approver_id"),
        "users",
        ["level_1_approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_level_2_approver_id"),
        "users",
        ["level_2_approver_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_users_level_1_approver_id_users",
        "users",
        "users",
        ["level_1_approver_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_users_level_2_approver_id_users",
        "users",
        "users",
        ["level_2_approver_id"],
        ["id"],
    )

    op.add_column(
        "leave_requests",
        sa.Column("escalated_to_backup_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leave_requests",
        sa.Column("escalated_to_backup_by_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_leave_requests_escalated_to_backup_by_id"),
        "leave_requests",
        ["escalated_to_backup_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_leave_requests_escalated_to_backup_by_id_users",
        "leave_requests",
        "users",
        ["escalated_to_backup_by_id"],
        ["id"],
    )

    op.add_column(
        "overtime_requests",
        sa.Column("escalated_to_backup_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "overtime_requests",
        sa.Column("escalated_to_backup_by_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_overtime_requests_escalated_to_backup_by_id"),
        "overtime_requests",
        ["escalated_to_backup_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_overtime_requests_escalated_to_backup_by_id_users",
        "overtime_requests",
        "users",
        ["escalated_to_backup_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_overtime_requests_escalated_to_backup_by_id_users",
        "overtime_requests",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_overtime_requests_escalated_to_backup_by_id"),
        table_name="overtime_requests",
    )
    op.drop_column("overtime_requests", "escalated_to_backup_by_id")
    op.drop_column("overtime_requests", "escalated_to_backup_at")

    op.drop_constraint(
        "fk_leave_requests_escalated_to_backup_by_id_users",
        "leave_requests",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_leave_requests_escalated_to_backup_by_id"),
        table_name="leave_requests",
    )
    op.drop_column("leave_requests", "escalated_to_backup_by_id")
    op.drop_column("leave_requests", "escalated_to_backup_at")

    op.drop_constraint("fk_users_level_2_approver_id_users", "users", type_="foreignkey")
    op.drop_constraint("fk_users_level_1_approver_id_users", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_level_2_approver_id"), table_name="users")
    op.drop_index(op.f("ix_users_level_1_approver_id"), table_name="users")
    op.drop_column("users", "level_2_approver_id")
    op.drop_column("users", "level_1_approver_id")
