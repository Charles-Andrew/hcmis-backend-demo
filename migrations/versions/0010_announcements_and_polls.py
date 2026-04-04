"""announcements and polls

Revision ID: 0010_announcements_and_polls
Revises: 0009_shared_resources_core
Create Date: 2026-03-25 00:00:04.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_announcements_and_polls"
down_revision = "0009_shared_resources_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_announcements_id"), "announcements", ["id"], unique=False)
    op.create_index(op.f("ix_announcements_author_id"), "announcements", ["author_id"], unique=False)

    op.create_table(
        "polls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("allow_multiple_choices", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_polls_id"), "polls", ["id"], unique=False)
    op.create_index(op.f("ix_polls_author_id"), "polls", ["author_id"], unique=False)

    op.create_table(
        "poll_choices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("poll_id", "position", name="uq_poll_choices_position"),
    )
    op.create_index(op.f("ix_poll_choices_id"), "poll_choices", ["id"], unique=False)
    op.create_index(op.f("ix_poll_choices_poll_id"), "poll_choices", ["poll_id"], unique=False)

    op.create_table(
        "poll_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("choice_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["choice_id"], ["poll_choices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("poll_id", "user_id", "choice_id", name="uq_poll_votes_identity"),
    )
    op.create_index(op.f("ix_poll_votes_id"), "poll_votes", ["id"], unique=False)
    op.create_index(op.f("ix_poll_votes_poll_id"), "poll_votes", ["poll_id"], unique=False)
    op.create_index(op.f("ix_poll_votes_choice_id"), "poll_votes", ["choice_id"], unique=False)
    op.create_index(op.f("ix_poll_votes_user_id"), "poll_votes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_poll_votes_user_id"), table_name="poll_votes")
    op.drop_index(op.f("ix_poll_votes_choice_id"), table_name="poll_votes")
    op.drop_index(op.f("ix_poll_votes_poll_id"), table_name="poll_votes")
    op.drop_index(op.f("ix_poll_votes_id"), table_name="poll_votes")
    op.drop_table("poll_votes")

    op.drop_index(op.f("ix_poll_choices_poll_id"), table_name="poll_choices")
    op.drop_index(op.f("ix_poll_choices_id"), table_name="poll_choices")
    op.drop_table("poll_choices")

    op.drop_index(op.f("ix_polls_author_id"), table_name="polls")
    op.drop_index(op.f("ix_polls_id"), table_name="polls")
    op.drop_table("polls")

    op.drop_index(op.f("ix_announcements_author_id"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_id"), table_name="announcements")
    op.drop_table("announcements")
