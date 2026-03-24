"""leave core

Revision ID: 0005_leave_core
Revises: 0004_attendance_core
Create Date: 2026-03-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_leave_core"
down_revision = "0004_attendance_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leave_approvers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("department_approver_id", sa.Integer(), nullable=True),
        sa.Column("director_approver_id", sa.Integer(), nullable=True),
        sa.Column("president_approver_id", sa.Integer(), nullable=True),
        sa.Column("hr_approver_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["department_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["director_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["president_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["hr_approver_id"], ["users.id"]),
        sa.UniqueConstraint("department_id"),
    )
    op.create_index(
        op.f("ix_leave_approvers_department_id"),
        "leave_approvers",
        ["department_id"],
        unique=False,
    )

    op.create_table(
        "leave_credits",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_leave_credits_user_id"), "leave_credits", ["user_id"], unique=False
    )

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("leave_date", sa.Date(), nullable=False),
        sa.Column("leave_type", sa.String(length=2), nullable=False),
        sa.Column("info", sa.Text(), nullable=True),
        sa.Column("first_approver_id", sa.Integer(), nullable=True),
        sa.Column(
            "first_approver_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("first_approver_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("second_approver_id", sa.Integer(), nullable=True),
        sa.Column("second_approver_status", sa.String(length=20), nullable=True),
        sa.Column("second_approver_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["first_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["second_approver_id"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_leave_requests_user_id"), "leave_requests", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_leave_requests_leave_date"),
        "leave_requests",
        ["leave_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leave_requests_leave_type"),
        "leave_requests",
        ["leave_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leave_requests_first_approver_id"),
        "leave_requests",
        ["first_approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leave_requests_second_approver_id"),
        "leave_requests",
        ["second_approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leave_requests_status"), "leave_requests", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_leave_requests_first_approver_status"),
        "leave_requests",
        ["first_approver_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leave_requests_second_approver_status"),
        "leave_requests",
        ["second_approver_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_leave_requests_second_approver_status"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_first_approver_status"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_status"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_second_approver_id"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_first_approver_id"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_leave_type"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_leave_date"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_user_id"), table_name="leave_requests")
    op.drop_table("leave_requests")

    op.drop_index(op.f("ix_leave_credits_user_id"), table_name="leave_credits")
    op.drop_table("leave_credits")

    op.drop_index(op.f("ix_leave_approvers_department_id"), table_name="leave_approvers")
    op.drop_table("leave_approvers")
