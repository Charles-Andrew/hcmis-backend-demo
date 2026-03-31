"""shared resources core

Revision ID: 0009_shared_resources_core
Revises: 0008_chat_core
Create Date: 2026-03-25 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_shared_resources_core"
down_revision = "0008_chat_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shared_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uploader_id", sa.Integer(), nullable=False),
        sa.Column("resource_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_shared_resources_id"), "shared_resources", ["id"], unique=False)
    op.create_index(
        op.f("ix_shared_resources_uploader_id"),
        "shared_resources",
        ["uploader_id"],
        unique=False,
    )

    op.create_table(
        "shared_resource_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["shared_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("resource_id", "user_id", name="uq_shared_resource_shares_identity"),
    )
    op.create_index(op.f("ix_shared_resource_shares_id"), "shared_resource_shares", ["id"], unique=False)
    op.create_index(
        op.f("ix_shared_resource_shares_resource_id"),
        "shared_resource_shares",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shared_resource_shares_user_id"),
        "shared_resource_shares",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "shared_resource_confidential_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["shared_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "resource_id",
            "user_id",
            name="uq_shared_resource_confidential_access_identity",
        ),
    )
    op.create_index(
        op.f("ix_shared_resource_confidential_access_id"),
        "shared_resource_confidential_access",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shared_resource_confidential_access_resource_id"),
        "shared_resource_confidential_access",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shared_resource_confidential_access_user_id"),
        "shared_resource_confidential_access",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_shared_resource_confidential_access_user_id"),
        table_name="shared_resource_confidential_access",
    )
    op.drop_index(
        op.f("ix_shared_resource_confidential_access_resource_id"),
        table_name="shared_resource_confidential_access",
    )
    op.drop_index(op.f("ix_shared_resource_confidential_access_id"), table_name="shared_resource_confidential_access")
    op.drop_table("shared_resource_confidential_access")

    op.drop_index(op.f("ix_shared_resource_shares_user_id"), table_name="shared_resource_shares")
    op.drop_index(op.f("ix_shared_resource_shares_resource_id"), table_name="shared_resource_shares")
    op.drop_index(op.f("ix_shared_resource_shares_id"), table_name="shared_resource_shares")
    op.drop_table("shared_resource_shares")

    op.drop_index(op.f("ix_shared_resources_uploader_id"), table_name="shared_resources")
    op.drop_index(op.f("ix_shared_resources_id"), table_name="shared_resources")
    op.drop_table("shared_resources")
