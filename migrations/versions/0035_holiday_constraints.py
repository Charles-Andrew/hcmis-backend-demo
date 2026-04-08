"""tighten holiday constraints

Revision ID: 0035_holiday_constraints
Revises: 0034_overtime_request_approver_pool
Create Date: 2026-04-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0035_holiday_constraints"
down_revision: str | None = "0034_overtime_request_pool"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    invalid_holiday = op.get_bind().execute(
        sa.text(
            """
            SELECT id, name, day, month, year
            FROM holidays
            WHERE day < 1
               OR day > 31
               OR month < 1
               OR month > 12
               OR (year IS NOT NULL AND year < 1900)
            ORDER BY id
            LIMIT 1
            """
        )
    ).mappings().first()
    if invalid_holiday is not None:
        raise RuntimeError(
            "Cannot apply holiday constraints because invalid holiday rows exist. "
            f"Example row id={invalid_holiday['id']} "
            f"({invalid_holiday['name']}: {invalid_holiday['month']}/{invalid_holiday['day']}/{invalid_holiday['year']})."
        )

    op.execute(
        sa.text(
            """
            DELETE FROM holidays AS specific
            USING holidays AS recurring
            WHERE recurring.year IS NULL
              AND specific.year IS NOT NULL
              AND recurring.month = specific.month
              AND recurring.day = specific.day
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM holidays
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY month, day
                            ORDER BY id
                        ) AS row_number
                    FROM holidays
                    WHERE year IS NULL
                ) ranked
                WHERE ranked.row_number > 1
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM holidays
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY year, month, day
                            ORDER BY id
                        ) AS row_number
                    FROM holidays
                    WHERE year IS NOT NULL
                ) ranked
                WHERE ranked.row_number > 1
            )
            """
        )
    )

    op.create_check_constraint("ck_holidays_day_range", "holidays", "day >= 1 AND day <= 31")
    op.create_check_constraint(
        "ck_holidays_month_range",
        "holidays",
        "month >= 1 AND month <= 12",
    )
    op.create_check_constraint(
        "ck_holidays_year_range",
        "holidays",
        "year IS NULL OR year >= 1900",
    )
    op.create_index(
        "uq_holidays_recurring_effective_date",
        "holidays",
        ["month", "day"],
        unique=True,
        postgresql_where=sa.text("year IS NULL"),
    )
    op.create_index(
        "uq_holidays_specific_effective_date",
        "holidays",
        ["year", "month", "day"],
        unique=True,
        postgresql_where=sa.text("year IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_holidays_specific_effective_date", table_name="holidays")
    op.drop_index("uq_holidays_recurring_effective_date", table_name="holidays")
    op.drop_constraint("ck_holidays_year_range", "holidays", type_="check")
    op.drop_constraint("ck_holidays_month_range", "holidays", type_="check")
    op.drop_constraint("ck_holidays_day_range", "holidays", type_="check")
