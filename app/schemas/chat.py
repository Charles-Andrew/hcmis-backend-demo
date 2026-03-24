from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.schemas.user import UserRead


class MessageRead(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    message: str | None = None
    seen: bool
    sender: UserRead | None = None
    receiver: UserRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreateRequest(BaseModel):
    receiver_id: int
    message: str = Field(min_length=1)


class ChatContactRead(BaseModel):
    user: UserRead
    unseen_count: int = 0


class ConversationRead(BaseModel):
    participants: list[UserRead] = Field(default_factory=list)
    messages: list[MessageRead] = Field(default_factory=list)
