"""add overtime approver settings

Revision ID: 0030_overtime_approvers
Revises: 0029_payslip_ded_sched
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0030_overtime_approvers"
down_revision = "0029_payslip_ded_sched"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "overtime_approvers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("department_approver_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("director_approver_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("president_approver_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("hr_approver_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["department_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["director_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["president_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["hr_approver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id"),
    )
    op.create_index(
        op.f("ix_overtime_approvers_id"), "overtime_approvers", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_overtime_approvers_department_id"),
        "overtime_approvers",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_overtime_approvers_department_approver_id"),
        "overtime_approvers",
        ["department_approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_overtime_approvers_director_approver_id"),
        "overtime_approvers",
        ["director_approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_overtime_approvers_president_approver_id"),
        "overtime_approvers",
        ["president_approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_overtime_approvers_hr_approver_id"),
        "overtime_approvers",
        ["hr_approver_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_overtime_approvers_hr_approver_id"), table_name="overtime_approvers"
    )
    op.drop_index(
        op.f("ix_overtime_approvers_president_approver_id"),
        table_name="overtime_approvers",
    )
    op.drop_index(
        op.f("ix_overtime_approvers_director_approver_id"),
        table_name="overtime_approvers",
    )
    op.drop_index(
        op.f("ix_overtime_approvers_department_approver_id"),
        table_name="overtime_approvers",
    )
    op.drop_index(
        op.f("ix_overtime_approvers_department_id"), table_name="overtime_approvers"
    )
    op.drop_index(op.f("ix_overtime_approvers_id"), table_name="overtime_approvers")
    op.drop_table("overtime_approvers")
