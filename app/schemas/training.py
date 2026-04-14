from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


TrainingStatus = Literal["pending", "completed"]


class TrainingParticipantCreateRequest(BaseModel):
    user_id: UUID


class TrainingCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    training_date: date
    participants: list[TrainingParticipantCreateRequest] = Field(default_factory=list)


class TrainingStatusUpdateRequest(BaseModel):
    status: TrainingStatus


class TrainingParticipantsReplaceRequest(BaseModel):
    participants: list[TrainingParticipantCreateRequest] = Field(default_factory=list)


class TrainingAttachmentRead(BaseModel):
    id: int
    file_name: str
    file_size: int
    content_type: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingParticipantRead(BaseModel):
    id: int
    user_id: UUID
    user_name: str
    attachments: list[TrainingAttachmentRead] = Field(default_factory=list)


class TrainingRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    training_date: date
    status: TrainingStatus
    created_by_id: UUID
    participants: list[TrainingParticipantRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
