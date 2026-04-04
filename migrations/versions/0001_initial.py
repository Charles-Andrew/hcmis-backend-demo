"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("employee_number", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("phone_number", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("date_of_hiring", sa.Date(), nullable=True),
        sa.Column("resignation_date", sa.Date(), nullable=True),
        sa.Column("profile_picture_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("employee_number"),
    )
    op.create_index("ix_users_department_id", "users", ["department_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("recipient_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
    )
    op.create_index(
        "ix_notifications_recipient_id",
        "notifications",
        ["recipient_id"],
        unique=False,
    )
    op.create_index("ix_notifications_sender_id", "notifications", ["sender_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_sender_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_table("users")

    op.drop_table("departments")
