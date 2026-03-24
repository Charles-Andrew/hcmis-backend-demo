from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base
from app.models.app_log import AppLog  # noqa: F401
from app.models.chat import Message  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.leave import LeaveCredit  # noqa: F401
from app.models.leave import LeaveRequest  # noqa: F401
from app.models.notification import Notification  # noqa: F401


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    education: Mapped[str | None] = mapped_column(String(10), nullable=True)
    civil_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
    religion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rank: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employee_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    biometric_uid: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_hiring: Mapped[date | None] = mapped_column(Date, nullable=True)
    resignation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    can_modify_shift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    department = relationship("Department", back_populates="users")
    notifications_received = relationship(
        "Notification",
        foreign_keys="Notification.recipient_id",
        back_populates="recipient",
    )
    notifications_sent = relationship(
        "Notification",
        foreign_keys="Notification.sender_id",
        back_populates="sender",
    )
    logs = relationship("AppLog", back_populates="user")
    leave_requests = relationship(
        "LeaveRequest",
        back_populates="user",
        foreign_keys="LeaveRequest.user_id",
    )
    leave_credit = relationship("LeaveCredit", back_populates="user", uselist=False)
    attendance_records = relationship("AttendanceRecord", back_populates="user")
    daily_shift_schedules = relationship("DailyShiftSchedule", back_populates="user")
    overtime_requests = relationship(
        "OvertimeRequest",
        foreign_keys="OvertimeRequest.user_id",
        back_populates="user",
    )
    overtime_approvals = relationship(
        "OvertimeRequest",
        foreign_keys="OvertimeRequest.approver_id",
        back_populates="approver",
    )
    shift_swap_requests = relationship(
        "ShiftSwapRequest",
        foreign_keys="ShiftSwapRequest.requested_by_id",
        back_populates="requested_by",
    )
    shift_swap_targets = relationship(
        "ShiftSwapRequest",
        foreign_keys="ShiftSwapRequest.requested_for_id",
        back_populates="requested_for",
    )
    shift_swap_approvals = relationship(
        "ShiftSwapRequest",
        foreign_keys="ShiftSwapRequest.approver_id",
        back_populates="approver",
    )
    payslips = relationship("Payslip", back_populates="user")
    thirteenth_month_pays = relationship("ThirteenthMonthPay", back_populates="user")
    messages_sent = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
    )
    messages_received = relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        back_populates="receiver",
    )
