from pydantic import BaseModel
from pydantic import Field
from pydantic import ConfigDict


class DepartmentRead(BaseModel):
    id: int
    name: str
    code: str
    workweek: list[str] = Field(default_factory=list)
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None
