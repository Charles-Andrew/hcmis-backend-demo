"""bridge commands

Revision ID: 0011_bridge_commands
Revises: 0010_announcements_and_polls
Create Date: 2026-04-03 00:00:05.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_bridge_commands"
down_revision = "0010_announcements_and_polls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bridge_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_code", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_bridge_commands_id"), "bridge_commands", ["id"], unique=False)
    op.create_index(op.f("ix_bridge_commands_site_code"), "bridge_commands", ["site_code"], unique=False)
    op.create_index(op.f("ix_bridge_commands_device_id"), "bridge_commands", ["device_id"], unique=False)
    op.create_index(op.f("ix_bridge_commands_command_type"), "bridge_commands", ["command_type"], unique=False)
    op.create_index(op.f("ix_bridge_commands_status"), "bridge_commands", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bridge_commands_status"), table_name="bridge_commands")
    op.drop_index(op.f("ix_bridge_commands_command_type"), table_name="bridge_commands")
    op.drop_index(op.f("ix_bridge_commands_device_id"), table_name="bridge_commands")
    op.drop_index(op.f("ix_bridge_commands_site_code"), table_name="bridge_commands")
    op.drop_index(op.f("ix_bridge_commands_id"), table_name="bridge_commands")
    op.drop_table("bridge_commands")
