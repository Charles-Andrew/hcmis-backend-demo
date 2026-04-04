from datetime import date, datetime
from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base


class LeaveType(str, PyEnum):
    PAID = "PA"
    UNPAID = "UN"
    WORK_RELATED_TRIP = "WR"


class LeaveRequestStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LeaveApprover(Base):
    __tablename__ = "leave_approvers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), unique=True, index=True, nullable=False
    )
    department_approver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    director_approver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    president_approver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    hr_approver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    department = relationship("Department", back_populates="leave_approver")
    department_approver = relationship("User", foreign_keys=[department_approver_id])
    director_approver = relationship("User", foreign_keys=[director_approver_id])
    president_approver = relationship("User", foreign_keys=[president_approver_id])
    hr_approver = relationship("User", foreign_keys=[hr_approver_id])


class LeaveCredit(Base):
    __tablename__ = "leave_credits"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True, index=True
    )
    credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="leave_credit")

    @property
    def remaining_credits(self) -> int:
        return self.credits - self.used_credits


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    leave_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    leave_type: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    info: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_approver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    first_approver_status: Mapped[str] = mapped_column(
        String(20), default=LeaveRequestStatus.PENDING.value, nullable=False, index=True
    )
    first_approver_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    second_approver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    second_approver_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    second_approver_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=LeaveRequestStatus.PENDING.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship("User", back_populates="leave_requests", foreign_keys=[user_id])
    first_approver = relationship("User", foreign_keys=[first_approver_id])
    second_approver = relationship("User", foreign_keys=[second_approver_id])

    @property
    def is_ready_for_second_approver(self) -> bool:
        return (
            self.second_approver_id is not None
            and self.first_approver_status == LeaveRequestStatus.APPROVED.value
            and self.second_approver_status == LeaveRequestStatus.PENDING.value
        )
