"""add attendance core schema

Revision ID: 0004_attendance_core
Revises: 0003_user_profile_fields
Create Date: 2026-03-24 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_attendance_core"
down_revision: str | None = "0003_user_profile_fields"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "departments",
        sa.Column(
            "workweek",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("biometric_uid", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint("uq_users_biometric_uid", "users", ["biometric_uid"])
    op.create_index("ix_users_biometric_uid", "users", ["biometric_uid"], unique=False)

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("start_time_2", sa.Time(), nullable=True),
        sa.Column("end_time_2", sa.Time(), nullable=True),
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
    )
    op.create_index("ix_shifts_id", "shifts", ["id"], unique=False)

    op.create_table(
        "department_shifts",
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.PrimaryKeyConstraint("department_id", "shift_id"),
    )

    op.create_table(
        "daily_shift_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    )
    op.create_index("ix_daily_shift_records_id", "daily_shift_records", ["id"], unique=False)
    op.create_index(
        "ix_daily_shift_records_department_id",
        "daily_shift_records",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_shift_records_date", "daily_shift_records", ["date"], unique=False
    )

    op.create_table(
        "daily_shift_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
    )
    op.create_index(
        "ix_daily_shift_schedules_id", "daily_shift_schedules", ["id"], unique=False
    )
    op.create_index(
        "ix_daily_shift_schedules_date", "daily_shift_schedules", ["date"], unique=False
    )
    op.create_index(
        "ix_daily_shift_schedules_user_id",
        "daily_shift_schedules",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_shift_schedules_shift_id",
        "daily_shift_schedules",
        ["shift_id"],
        unique=False,
    )

    op.create_table(
        "daily_shift_record_schedules",
        sa.Column("daily_shift_record_id", sa.Integer(), nullable=False),
        sa.Column("daily_shift_schedule_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["daily_shift_record_id"], ["daily_shift_records.id"]),
        sa.ForeignKeyConstraint(["daily_shift_schedule_id"], ["daily_shift_schedules.id"]),
        sa.PrimaryKeyConstraint("daily_shift_record_id", "daily_shift_schedule_id"),
    )

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_user_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("punch", sa.String(length=6), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_attendance_records_id", "attendance_records", ["id"], unique=False)
    op.create_index(
        "ix_attendance_records_user_id",
        "attendance_records",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_records_device_user_id",
        "attendance_records",
        ["device_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_records_timestamp",
        "attendance_records",
        ["timestamp"],
        unique=False,
    )

    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("is_regular", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    )
    op.create_index("ix_holidays_id", "holidays", ["id"], unique=False)

    op.create_table(
        "overtime_requests",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("info", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=4), nullable=False, server_default="PEND"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
    )
    op.create_index("ix_overtime_requests_id", "overtime_requests", ["id"], unique=False)
    op.create_index(
        "ix_overtime_requests_user_id", "overtime_requests", ["user_id"], unique=False
    )
    op.create_index(
        "ix_overtime_requests_approver_id",
        "overtime_requests",
        ["approver_id"],
        unique=False,
    )
    op.create_index("ix_overtime_requests_date", "overtime_requests", ["date"], unique=False)
    op.create_index(
        "ix_overtime_requests_status", "overtime_requests", ["status"], unique=False
    )

    op.create_table(
        "shift_swap_requests",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("requested_for_id", sa.Integer(), nullable=False),
        sa.Column("current_schedule_id", sa.Integer(), nullable=False),
        sa.Column("requested_schedule_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("info", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=4), nullable=False, server_default="PEND"),
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
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requested_for_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["current_schedule_id"], ["daily_shift_schedules.id"]),
        sa.ForeignKeyConstraint(["requested_schedule_id"], ["daily_shift_schedules.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
    )
    op.create_index("ix_shift_swap_requests_id", "shift_swap_requests", ["id"], unique=False)
    op.create_index(
        "ix_shift_swap_requests_requested_by_id",
        "shift_swap_requests",
        ["requested_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_shift_swap_requests_requested_for_id",
        "shift_swap_requests",
        ["requested_for_id"],
        unique=False,
    )
    op.create_index(
        "ix_shift_swap_requests_current_schedule_id",
        "shift_swap_requests",
        ["current_schedule_id"],
        unique=False,
    )
    op.create_index(
        "ix_shift_swap_requests_requested_schedule_id",
        "shift_swap_requests",
        ["requested_schedule_id"],
        unique=False,
    )
    op.create_index(
        "ix_shift_swap_requests_approver_id",
        "shift_swap_requests",
        ["approver_id"],
        unique=False,
    )
    op.create_index(
        "ix_shift_swap_requests_status",
        "shift_swap_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shift_swap_requests_status", table_name="shift_swap_requests")
    op.drop_index("ix_shift_swap_requests_approver_id", table_name="shift_swap_requests")
    op.drop_index(
        "ix_shift_swap_requests_requested_schedule_id", table_name="shift_swap_requests"
    )
    op.drop_index(
        "ix_shift_swap_requests_current_schedule_id", table_name="shift_swap_requests"
    )
    op.drop_index(
        "ix_shift_swap_requests_requested_for_id", table_name="shift_swap_requests"
    )
    op.drop_index(
        "ix_shift_swap_requests_requested_by_id", table_name="shift_swap_requests"
    )
    op.drop_index("ix_shift_swap_requests_id", table_name="shift_swap_requests")
    op.drop_table("shift_swap_requests")

    op.drop_index("ix_overtime_requests_status", table_name="overtime_requests")
    op.drop_index("ix_overtime_requests_date", table_name="overtime_requests")
    op.drop_index("ix_overtime_requests_approver_id", table_name="overtime_requests")
    op.drop_index("ix_overtime_requests_user_id", table_name="overtime_requests")
    op.drop_index("ix_overtime_requests_id", table_name="overtime_requests")
    op.drop_table("overtime_requests")

    op.drop_index("ix_holidays_id", table_name="holidays")
    op.drop_table("holidays")

    op.drop_index("ix_attendance_records_timestamp", table_name="attendance_records")
    op.drop_index("ix_attendance_records_device_user_id", table_name="attendance_records")
    op.drop_index("ix_attendance_records_user_id", table_name="attendance_records")
    op.drop_index("ix_attendance_records_id", table_name="attendance_records")
    op.drop_table("attendance_records")

    op.drop_table("daily_shift_record_schedules")
    op.drop_index("ix_daily_shift_schedules_shift_id", table_name="daily_shift_schedules")
    op.drop_index("ix_daily_shift_schedules_user_id", table_name="daily_shift_schedules")
    op.drop_index("ix_daily_shift_schedules_date", table_name="daily_shift_schedules")
    op.drop_index("ix_daily_shift_schedules_id", table_name="daily_shift_schedules")
    op.drop_table("daily_shift_schedules")

    op.drop_index("ix_daily_shift_records_date", table_name="daily_shift_records")
    op.drop_index(
        "ix_daily_shift_records_department_id", table_name="daily_shift_records"
    )
    op.drop_index("ix_daily_shift_records_id", table_name="daily_shift_records")
    op.drop_table("daily_shift_records")

    op.drop_table("department_shifts")
    op.drop_index("ix_shifts_id", table_name="shifts")
    op.drop_table("shifts")

    op.drop_index("ix_users_biometric_uid", table_name="users")
    op.drop_constraint("uq_users_biometric_uid", "users", type_="unique")
    op.drop_column("users", "biometric_uid")
    op.drop_column("departments", "workweek")

