from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class AppLogRead(BaseModel):
    id: int
    user_id: int
    details: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

