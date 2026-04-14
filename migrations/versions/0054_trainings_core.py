"""add trainings core tables

Revision ID: 0054_trainings_core
Revises: 0053_leave_req_approval_type
Create Date: 2026-04-15 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0054_trainings_core"
down_revision = "0053_leave_req_approval_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trainings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name=op.f("fk_trainings_created_by_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trainings")),
    )
    op.create_index(op.f("ix_trainings_id"), "trainings", ["id"], unique=False)
    op.create_index(op.f("ix_trainings_status"), "trainings", ["status"], unique=False)
    op.create_index(op.f("ix_trainings_created_by_id"), "trainings", ["created_by_id"], unique=False)
    op.create_check_constraint(
        "ck_trainings_status",
        "trainings",
        "status IN ('pending', 'completed')",
    )

    op.create_table(
        "training_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["training_id"],
            ["trainings.id"],
            name=op.f("fk_training_participants_training_id_trainings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_training_participants_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_training_participants")),
        sa.UniqueConstraint("training_id", "user_id", name="uq_training_participants_identity"),
    )
    op.create_index(
        op.f("ix_training_participants_id"),
        "training_participants",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_participants_training_id"),
        "training_participants",
        ["training_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_participants_user_id"),
        "training_participants",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "training_participant_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["training_participants.id"],
            name=op.f("fk_training_participant_attachments_participant_id_training_participants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_training_participant_attachments")),
    )
    op.create_index(
        op.f("ix_training_participant_attachments_id"),
        "training_participant_attachments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_participant_attachments_participant_id"),
        "training_participant_attachments",
        ["participant_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_training_participant_attachments_file_size",
        "training_participant_attachments",
        "file_size >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_training_participant_attachments_file_size",
        "training_participant_attachments",
        type_="check",
    )
    op.drop_index(
        op.f("ix_training_participant_attachments_participant_id"),
        table_name="training_participant_attachments",
    )
    op.drop_index(
        op.f("ix_training_participant_attachments_id"),
        table_name="training_participant_attachments",
    )
    op.drop_table("training_participant_attachments")

    op.drop_index(op.f("ix_training_participants_user_id"), table_name="training_participants")
    op.drop_index(op.f("ix_training_participants_training_id"), table_name="training_participants")
    op.drop_index(op.f("ix_training_participants_id"), table_name="training_participants")
    op.drop_table("training_participants")

    op.drop_constraint("ck_trainings_status", "trainings", type_="check")
    op.drop_index(op.f("ix_trainings_created_by_id"), table_name="trainings")
    op.drop_index(op.f("ix_trainings_status"), table_name="trainings")
    op.drop_index(op.f("ix_trainings_id"), table_name="trainings")
    op.drop_table("trainings")
