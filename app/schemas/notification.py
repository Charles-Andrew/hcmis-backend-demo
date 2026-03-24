from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class NotificationRead(BaseModel):
    id: int
    recipient_id: int
    sender_id: int | None = None
    content: str
    url: str | None = None
    read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

