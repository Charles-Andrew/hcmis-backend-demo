from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class NotificationRead(BaseModel):
    id: int
    recipient_id: UUID
    sender_id: UUID | None = None
    content: str
    url: str | None = None
    read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCountRead(BaseModel):
    unread_count: int


class NotificationMarkAllReadResult(BaseModel):
    updated_count: int
