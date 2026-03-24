from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.time import utc_now
from app.models.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    workweek: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    users = relationship("User", back_populates="department")
    leave_approver = relationship(
        "LeaveApprover", back_populates="department", uselist=False
    )
    shifts = relationship(
        "Shift", secondary="department_shifts", back_populates="departments"
    )
    daily_shift_records = relationship("DailyShiftRecord", back_populates="department")
