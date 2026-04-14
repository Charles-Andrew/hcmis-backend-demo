"""enforce distinct user approvers

Revision ID: 0041_user_approver_distinct_ck
Revises: 0040_user_username_login
Create Date: 2026-04-13 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0041_user_approver_distinct_ck"
down_revision = "0040_user_username_login"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_approvers_distinct",
        "users",
        "level_1_approver_id IS NULL OR level_2_approver_id IS NULL OR level_1_approver_id <> level_2_approver_id",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_approvers_distinct", "users", type_="check")
