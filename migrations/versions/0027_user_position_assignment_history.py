"""add user position assignment history

Revision ID: 0027_user_position_assignments
Revises: 0026_deleted_attendance_tombs
Create Date: 2026-04-08 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_user_position_assignments"
down_revision = "0026_deleted_attendance_tombs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("position_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("rank_level", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("step_number", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_position_id_positions",
        "users",
        "positions",
        ["position_id"],
        ["id"],
    )
    op.create_index(op.f("ix_users_position_id"), "users", ["position_id"], unique=False)
    op.create_check_constraint(
        "ck_users_rank_level_positive",
        "users",
        "rank_level IS NULL OR rank_level >= 1",
    )
    op.create_check_constraint(
        "ck_users_step_number_positive",
        "users",
        "step_number IS NULL OR step_number >= 1",
    )

    op.create_table(
        "user_position_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("rank_level", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("change_reason", sa.String(length=500), nullable=True),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rank_level >= 1",
            name="ck_user_position_assignments_rank_level_positive",
        ),
        sa.CheckConstraint(
            "step_number IS NULL OR step_number >= 1",
            name="ck_user_position_assignments_step_number_positive",
        ),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_position_assignments_effective_from"),
        "user_position_assignments",
        ["effective_from"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_position_assignments_effective_to"),
        "user_position_assignments",
        ["effective_to"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_position_assignments_id"),
        "user_position_assignments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_position_assignments_position_id"),
        "user_position_assignments",
        ["position_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_position_assignments_user_id"),
        "user_position_assignments",
        ["user_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE users
        SET
            rank_level = CASE
                WHEN rank ~ '^[A-Z0-9]+-[0-9]+(\\s*-\\s*STEP\\s*[0-9]+)?$'
                    THEN CAST((regexp_match(rank, '^[A-Z0-9]+-([0-9]+)'))[1] AS INTEGER)
                ELSE NULL
            END,
            step_number = CASE
                WHEN rank ~ 'STEP\\s*[0-9]+$'
                    THEN CAST((regexp_match(rank, 'STEP\\s*([0-9]+)$'))[1] AS INTEGER)
                ELSE NULL
            END
        """
    )
    op.execute(
        """
        UPDATE users AS u
        SET position_id = p.id
        FROM positions AS p
        WHERE split_part(u.rank, '-', 1) = p.code
        """
    )
    op.execute(
        """
        INSERT INTO user_position_assignments (
            user_id,
            position_id,
            rank_level,
            step_number,
            effective_from,
            effective_to,
            change_reason,
            changed_by,
            created_at,
            updated_at
        )
        SELECT
            id,
            position_id,
            rank_level,
            step_number,
            COALESCE(date_of_hiring, CURRENT_DATE),
            NULL,
            'Initial migration from legacy rank field',
            NULL,
            NOW(),
            NOW()
        FROM users
        WHERE position_id IS NOT NULL
          AND rank_level IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_position_assignments_user_id"),
        table_name="user_position_assignments",
    )
    op.drop_index(
        op.f("ix_user_position_assignments_position_id"),
        table_name="user_position_assignments",
    )
    op.drop_index(
        op.f("ix_user_position_assignments_id"),
        table_name="user_position_assignments",
    )
    op.drop_index(
        op.f("ix_user_position_assignments_effective_to"),
        table_name="user_position_assignments",
    )
    op.drop_index(
        op.f("ix_user_position_assignments_effective_from"),
        table_name="user_position_assignments",
    )
    op.drop_table("user_position_assignments")

    op.drop_constraint("ck_users_step_number_positive", "users", type_="check")
    op.drop_constraint("ck_users_rank_level_positive", "users", type_="check")
    op.drop_index(op.f("ix_users_position_id"), table_name="users")
    op.drop_constraint("fk_users_position_id_positions", "users", type_="foreignkey")
    op.drop_column("users", "step_number")
    op.drop_column("users", "rank_level")
    op.drop_column("users", "position_id")
