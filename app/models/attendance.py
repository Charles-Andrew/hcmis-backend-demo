from datetime import date, datetime, time
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base

department_shift_templates = Table(
    "department_shifts",
    Base.metadata,
    Column("department_id", ForeignKey("departments.id"), primary_key=True),
    Column("shift_id", ForeignKey("shifts.id"), primary_key=True),
)

department_roster_day_assignments = Table(
    "daily_shift_record_schedules",
    Base.metadata,
    Column("daily_shift_record_id", ForeignKey("daily_shift_records.id"), primary_key=True),
    Column("daily_shift_schedule_id", ForeignKey("daily_shift_schedules.id"), primary_key=True),
)


class ShiftTemplate(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    start_time_2: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time_2: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    departments = relationship(
        "Department",
        secondary=department_shift_templates,
        back_populates="shift_templates",
    )
    employee_shift_assignments = relationship(
        "EmployeeShiftAssignment", back_populates="shift_template"
    )


class EmployeeShiftAssignment(Base):
    __tablename__ = "daily_shift_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    shift_template_id: Mapped[int] = mapped_column("shift_id", ForeignKey("shifts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="employee_shift_assignments")
    shift_template = relationship("ShiftTemplate", back_populates="employee_shift_assignments")
    department_roster_days = relationship(
        "DepartmentRosterDay",
        secondary=department_roster_day_assignments,
        back_populates="employee_shift_assignments",
    )

    @property
    def shift_id(self) -> int:
        return self.shift_template_id

    @shift_id.setter
    def shift_id(self, value: int) -> None:
        self.shift_template_id = value

    @property
    def shift(self):
        return self.shift_template

    @shift.setter
    def shift(self, value) -> None:
        self.shift_template = value

    @property
    def records(self):
        return self.department_roster_days

    @records.setter
    def records(self, value) -> None:
        self.department_roster_days = value


class DepartmentRosterDay(Base):
    __tablename__ = "daily_shift_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    department = relationship("Department", back_populates="department_roster_days")
    employee_shift_assignments = relationship(
        "EmployeeShiftAssignment",
        secondary=department_roster_day_assignments,
        back_populates="department_roster_days",
    )

    @property
    def schedules(self):
        return self.employee_shift_assignments

    @schedules.setter
    def schedules(self, value) -> None:
        self.employee_shift_assignments = value


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_regular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    class Punch(str, PyEnum):
        TIME_IN = "IN"
        TIME_OUT = "OUT"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    device_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    punch: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="attendance_records")


class OvertimeRequest(Base):
    __tablename__ = "overtime_requests"

    class Status(str, PyEnum):
        PENDING = "PEND"
        APPROVED = "APP"
        REJECTED = "REJ"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    info: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(4), default=Status.PENDING.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="overtime_requests")
    approver = relationship(
        "User", foreign_keys=[approver_id], back_populates="overtime_approvals"
    )


class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"

    class Status(str, PyEnum):
        PENDING = "PEND"
        APPROVED = "APP"
        REJECTED = "REJ"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    requested_for_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    current_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("daily_shift_schedules.id"), index=True
    )
    requested_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("daily_shift_schedules.id"), index=True
    )
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    info: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(4), default=Status.PENDING.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    requested_by = relationship(
        "User", foreign_keys=[requested_by_id], back_populates="shift_swap_requests"
    )
    requested_for = relationship(
        "User", foreign_keys=[requested_for_id], back_populates="shift_swap_targets"
    )
    current_schedule = relationship(
        "EmployeeShiftAssignment", foreign_keys=[current_schedule_id]
    )
    requested_schedule = relationship(
        "EmployeeShiftAssignment", foreign_keys=[requested_schedule_id]
    )
    approver = relationship(
        "User", foreign_keys=[approver_id], back_populates="shift_swap_approvals"
    )


# Compatibility aliases while the database tables and older modules are phased out.
Shift = ShiftTemplate
DailyShiftSchedule = EmployeeShiftAssignment
DailyShiftRecord = DepartmentRosterDay
department_shifts = department_shift_templates
daily_shift_record_schedules = department_roster_day_assignments
