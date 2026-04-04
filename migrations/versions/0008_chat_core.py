"""chat core

Revision ID: 0008_chat_core
Revises: 0007_performance_core
Create Date: 2026-03-24 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_chat_core"
down_revision = "0007_performance_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("seen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)
    op.create_index(op.f("ix_messages_sender_id"), "messages", ["sender_id"], unique=False)
    op.create_index(op.f("ix_messages_receiver_id"), "messages", ["receiver_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_receiver_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_sender_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_id"), table_name="messages")
    op.drop_table("messages")
