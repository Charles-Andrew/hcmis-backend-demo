from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    receiver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    seen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship(
        "User", foreign_keys=[receiver_id], back_populates="messages_received"
    )
