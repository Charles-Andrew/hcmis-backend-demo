from datetime import date, datetime, time
from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base


class SpecialRequestStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OfficialBusinessRequest(Base):
    __tablename__ = "official_business_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    info: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    escalated_to_backup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalated_to_backup_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SpecialRequestStatus.PENDING.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="official_business_requests"
    )
    approver = relationship(
        "User", foreign_keys=[approver_id], back_populates="official_business_approvals"
    )
    escalated_to_backup_by = relationship("User", foreign_keys=[escalated_to_backup_by_id])
    approver_pool = relationship(
        "OfficialBusinessRequestApprover",
        back_populates="official_business_request",
        cascade="all, delete-orphan",
    )

    @staticmethod
    def _display_name(user) -> str | None:
        if user is None:
            return None
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return full_name or user.email

    @property
    def user_name(self) -> str | None:
        return self._display_name(self.user)

    @property
    def user_email(self) -> str | None:
        return self.user.email if self.user is not None else None

    @property
    def user_department_name(self) -> str | None:
        if self.user is None or self.user.department is None:
            return None
        return self.user.department.name

    @property
    def approver_name(self) -> str | None:
        return self._display_name(self.approver)


class OfficialBusinessRequestApprover(Base):
    __tablename__ = "official_business_request_approvers"
    __table_args__ = (
        UniqueConstraint(
            "official_business_request_id",
            "approver_id",
            name="uq_ob_req_approvers_req_id_approver_id",
        ),
        Index(
            "ix_ob_req_approvers_req_id",
            "official_business_request_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    official_business_request_id: Mapped[int] = mapped_column(
        ForeignKey("official_business_requests.id"), nullable=False
    )
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SpecialRequestStatus.PENDING.value, nullable=False, index=True
    )
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    official_business_request = relationship(
        "OfficialBusinessRequest", back_populates="approver_pool"
    )
    approver = relationship("User", foreign_keys=[approver_id])


class CertificateAttendanceRequest(Base):
    __tablename__ = "certificate_attendance_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    info: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    punch: Mapped[str] = mapped_column(String(6), nullable=False)
    escalated_to_backup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalated_to_backup_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SpecialRequestStatus.PENDING.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="certificate_attendance_requests"
    )
    approver = relationship(
        "User",
        foreign_keys=[approver_id],
        back_populates="certificate_attendance_approvals",
    )
    escalated_to_backup_by = relationship("User", foreign_keys=[escalated_to_backup_by_id])
    approver_pool = relationship(
        "CertificateAttendanceRequestApprover",
        back_populates="certificate_attendance_request",
        cascade="all, delete-orphan",
    )

    @staticmethod
    def _display_name(user) -> str | None:
        if user is None:
            return None
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return full_name or user.email

    @property
    def user_name(self) -> str | None:
        return self._display_name(self.user)

    @property
    def user_email(self) -> str | None:
        return self.user.email if self.user is not None else None

    @property
    def user_department_name(self) -> str | None:
        if self.user is None or self.user.department is None:
            return None
        return self.user.department.name

    @property
    def approver_name(self) -> str | None:
        return self._display_name(self.approver)


class CertificateAttendanceRequestApprover(Base):
    __tablename__ = "certificate_attendance_request_approvers"
    __table_args__ = (
        UniqueConstraint(
            "certificate_attendance_request_id",
            "approver_id",
            name="uq_ca_req_approvers_req_id_approver_id",
        ),
        Index(
            "ix_ca_req_approvers_req_id",
            "certificate_attendance_request_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certificate_attendance_request_id: Mapped[int] = mapped_column(
        ForeignKey("certificate_attendance_requests.id"), nullable=False
    )
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SpecialRequestStatus.PENDING.value, nullable=False, index=True
    )
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    certificate_attendance_request = relationship(
        "CertificateAttendanceRequest", back_populates="approver_pool"
    )
    approver = relationship("User", foreign_keys=[approver_id])
