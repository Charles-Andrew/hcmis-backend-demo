"""bridge user snapshots

Revision ID: 0013_bridge_user_snapshots
Revises: 0012_bridge_cmd_id_seq
Create Date: 2026-04-03 00:00:07.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_bridge_user_snapshots"
down_revision = "0012_bridge_cmd_id_seq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bridge_user_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_code", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("biometric_uid", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        op.f("ix_bridge_user_snapshots_id"),
        "bridge_user_snapshots",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bridge_user_snapshots_site_code"),
        "bridge_user_snapshots",
        ["site_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bridge_user_snapshots_device_id"),
        "bridge_user_snapshots",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bridge_user_snapshots_biometric_uid"),
        "bridge_user_snapshots",
        ["biometric_uid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_bridge_user_snapshots_biometric_uid"),
        table_name="bridge_user_snapshots",
    )
    op.drop_index(
        op.f("ix_bridge_user_snapshots_device_id"),
        table_name="bridge_user_snapshots",
    )
    op.drop_index(
        op.f("ix_bridge_user_snapshots_site_code"),
        table_name="bridge_user_snapshots",
    )
    op.drop_index(
        op.f("ix_bridge_user_snapshots_id"),
        table_name="bridge_user_snapshots",
    )
    op.drop_table("bridge_user_snapshots")
