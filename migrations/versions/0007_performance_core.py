"""performance core

Revision ID: 0007_performance_core
Revises: 0006_payroll_core
Create Date: 2026-03-24 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_performance_core"
down_revision = "0006_payroll_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "questionnaires",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_questionnaires_id"), "questionnaires", ["id"], unique=False)
    op.create_index(op.f("ix_questionnaires_code"), "questionnaires", ["code"], unique=False)

    op.create_table(
        "user_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evaluatee_id", sa.Integer(), nullable=False),
        sa.Column("questionnaire_id", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.String(length=2), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evaluatee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["questionnaires.id"]),
        sa.UniqueConstraint(
            "evaluatee_id",
            "questionnaire_id",
            "quarter",
            "year",
            name="uq_user_evaluations_identity",
        ),
    )
    op.create_index(op.f("ix_user_evaluations_id"), "user_evaluations", ["id"], unique=False)
    op.create_index(
        op.f("ix_user_evaluations_evaluatee_id"),
        "user_evaluations",
        ["evaluatee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_evaluations_questionnaire_id"),
        "user_evaluations",
        ["questionnaire_id"],
        unique=False,
    )
    op.create_index(op.f("ix_user_evaluations_year"), "user_evaluations", ["year"], unique=False)

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evaluator_id", sa.Integer(), nullable=False),
        sa.Column("user_evaluation_id", sa.Integer(), nullable=False),
        sa.Column("questionnaire_id", sa.Integer(), nullable=False),
        sa.Column("positive_feedback", sa.Text(), nullable=True),
        sa.Column("improvement_suggestion", sa.Text(), nullable=True),
        sa.Column("content_data", sa.JSON(), nullable=False),
        sa.Column("date_submitted", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evaluator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_evaluation_id"], ["user_evaluations.id"]),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["questionnaires.id"]),
        sa.UniqueConstraint(
            "user_evaluation_id",
            "evaluator_id",
            name="uq_evaluations_identity",
        ),
    )
    op.create_index(op.f("ix_evaluations_id"), "evaluations", ["id"], unique=False)
    op.create_index(op.f("ix_evaluations_evaluator_id"), "evaluations", ["evaluator_id"], unique=False)
    op.create_index(
        op.f("ix_evaluations_user_evaluation_id"),
        "evaluations",
        ["user_evaluation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluations_questionnaire_id"),
        "evaluations",
        ["questionnaire_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evaluations_questionnaire_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_user_evaluation_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_evaluator_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_id"), table_name="evaluations")
    op.drop_table("evaluations")

    op.drop_index(op.f("ix_user_evaluations_year"), table_name="user_evaluations")
    op.drop_index(op.f("ix_user_evaluations_questionnaire_id"), table_name="user_evaluations")
    op.drop_index(op.f("ix_user_evaluations_evaluatee_id"), table_name="user_evaluations")
    op.drop_index(op.f("ix_user_evaluations_id"), table_name="user_evaluations")
    op.drop_table("user_evaluations")

    op.drop_index(op.f("ix_questionnaires_code"), table_name="questionnaires")
    op.drop_index(op.f("ix_questionnaires_id"), table_name="questionnaires")
    op.drop_table("questionnaires")
