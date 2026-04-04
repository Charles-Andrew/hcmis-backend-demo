from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class AppLogRead(BaseModel):
    id: int
    user_id: UUID
    details: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
