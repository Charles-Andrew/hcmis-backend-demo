"""add official business and certificate attendance requests

Revision ID: 0045_special_requests_core
Revises: 0044_user_emp_class_fields
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0045_special_requests_core"
down_revision: Union[str, None] = "0044_user_emp_class_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "official_business_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("info", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("escalated_to_backup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_to_backup_by_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["escalated_to_backup_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_official_business_requests_id"),
        "official_business_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_requests_user_id"),
        "official_business_requests",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_requests_approver_id"),
        "official_business_requests",
        ["approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_requests_date"),
        "official_business_requests",
        ["date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_requests_status"),
        "official_business_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_requests_escalated_to_backup_by_id"),
        "official_business_requests",
        ["escalated_to_backup_by_id"],
        unique=False,
    )

    op.create_table(
        "official_business_request_approvers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("official_business_request_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["official_business_request_id"], ["official_business_requests.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "official_business_request_id",
            "approver_id",
            name="uq_ob_req_approvers_req_id_approver_id",
        ),
    )
    op.create_index(
        op.f("ix_official_business_request_approvers_id"),
        "official_business_request_approvers",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_ob_req_approvers_req_id",
        "official_business_request_approvers",
        ["official_business_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_request_approvers_approver_id"),
        "official_business_request_approvers",
        ["approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_official_business_request_approvers_status"),
        "official_business_request_approvers",
        ["status"],
        unique=False,
    )

    op.create_table(
        "certificate_attendance_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("info", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("escalated_to_backup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_to_backup_by_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["escalated_to_backup_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificate_attendance_requests_id"),
        "certificate_attendance_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_requests_user_id"),
        "certificate_attendance_requests",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_requests_approver_id"),
        "certificate_attendance_requests",
        ["approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_requests_date"),
        "certificate_attendance_requests",
        ["date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_requests_status"),
        "certificate_attendance_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_requests_escalated_to_backup_by_id"),
        "certificate_attendance_requests",
        ["escalated_to_backup_by_id"],
        unique=False,
    )

    op.create_table(
        "certificate_attendance_request_approvers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certificate_attendance_request_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["certificate_attendance_request_id"], ["certificate_attendance_requests.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "certificate_attendance_request_id",
            "approver_id",
            name="uq_ca_req_approvers_req_id_approver_id",
        ),
    )
    op.create_index(
        op.f("ix_certificate_attendance_request_approvers_id"),
        "certificate_attendance_request_approvers",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_ca_req_approvers_req_id",
        "certificate_attendance_request_approvers",
        ["certificate_attendance_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_request_approvers_approver_id"),
        "certificate_attendance_request_approvers",
        ["approver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificate_attendance_request_approvers_status"),
        "certificate_attendance_request_approvers",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_certificate_attendance_request_approvers_status"),
        table_name="certificate_attendance_request_approvers",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_request_approvers_approver_id"),
        table_name="certificate_attendance_request_approvers",
    )
    op.drop_index(
        "ix_ca_req_approvers_req_id",
        table_name="certificate_attendance_request_approvers",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_request_approvers_id"),
        table_name="certificate_attendance_request_approvers",
    )
    op.drop_table("certificate_attendance_request_approvers")

    op.drop_index(
        op.f("ix_certificate_attendance_requests_escalated_to_backup_by_id"),
        table_name="certificate_attendance_requests",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_requests_status"),
        table_name="certificate_attendance_requests",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_requests_date"),
        table_name="certificate_attendance_requests",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_requests_approver_id"),
        table_name="certificate_attendance_requests",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_requests_user_id"),
        table_name="certificate_attendance_requests",
    )
    op.drop_index(
        op.f("ix_certificate_attendance_requests_id"),
        table_name="certificate_attendance_requests",
    )
    op.drop_table("certificate_attendance_requests")

    op.drop_index(
        op.f("ix_official_business_request_approvers_status"),
        table_name="official_business_request_approvers",
    )
    op.drop_index(
        op.f("ix_official_business_request_approvers_approver_id"),
        table_name="official_business_request_approvers",
    )
    op.drop_index(
        "ix_ob_req_approvers_req_id",
        table_name="official_business_request_approvers",
    )
    op.drop_index(
        op.f("ix_official_business_request_approvers_id"),
        table_name="official_business_request_approvers",
    )
    op.drop_table("official_business_request_approvers")

    op.drop_index(
        op.f("ix_official_business_requests_escalated_to_backup_by_id"),
        table_name="official_business_requests",
    )
    op.drop_index(
        op.f("ix_official_business_requests_status"),
        table_name="official_business_requests",
    )
    op.drop_index(
        op.f("ix_official_business_requests_date"),
        table_name="official_business_requests",
    )
    op.drop_index(
        op.f("ix_official_business_requests_approver_id"),
        table_name="official_business_requests",
    )
    op.drop_index(
        op.f("ix_official_business_requests_user_id"),
        table_name="official_business_requests",
    )
    op.drop_index(
        op.f("ix_official_business_requests_id"),
        table_name="official_business_requests",
    )
    op.drop_table("official_business_requests")
