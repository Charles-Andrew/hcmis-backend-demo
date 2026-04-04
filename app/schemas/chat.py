from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.user import UserRead


class MessageRead(BaseModel):
    id: int
    sender_id: UUID
    receiver_id: UUID
    message: str | None = None
    seen: bool
    sender: UserRead | None = None
    receiver: UserRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreateRequest(BaseModel):
    receiver_id: UUID
    message: str = Field(min_length=1)


class ChatContactRead(BaseModel):
    user: UserRead
    unseen_count: int = 0


class ConversationRead(BaseModel):
    participants: list[UserRead] = Field(default_factory=list)
    messages: list[MessageRead] = Field(default_factory=list)
