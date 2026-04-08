from datetime import date, datetime
import re
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_serializer
from pydantic import field_validator

from app.services.profile_photo_storage import get_profile_photo_read_url
from app.schemas.department import DepartmentRead

RANK_PATTERN = re.compile(
    r"^(?P<position_code>[A-Z0-9]+)-(?P<rank>\d+)(?:\s*-\s*STEP\s*(?P<step>\d+))?$"
)


def normalize_rank(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if normalized == "":
        return None
    match = RANK_PATTERN.match(normalized)
    if match is None:
        raise ValueError("Rank must follow CODE-RANK or CODE-RANK - STEP N format.")
    rank = int(match.group("rank"))
    if rank < 1:
        raise ValueError("Rank number must be at least 1.")
    step = match.group("step")
    if step is None:
        return f"{match.group('position_code')}-{rank}"
    step_number = int(step)
    if step_number < 1:
        raise ValueError("Step number must be at least 1.")
    return f"{match.group('position_code')}-{rank} - STEP {step_number}"


class UserRead(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    gender: str | None = None
    education: str | None = None
    civil_status: str | None = None
    religion: str | None = None
    rank: str | None = None
    position_id: int | None = None
    rank_level: int | None = None
    step_number: int | None = None
    employee_number: str | None = None
    biometric_uid: int | None = None
    role: str | None = None
    department_id: int | None = None
    department: DepartmentRead | None = None
    phone_number: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    date_of_hiring: date | None = None
    resignation_date: date | None = None
    profile_picture_url: str | None = None
    can_modify_shift: bool
    must_change_password: bool
    temporary_password_expires_at: datetime | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("must_change_password", mode="before")
    @classmethod
    def normalize_must_change_password(cls, value: object) -> bool:
        if value is None:
            return False
        return bool(value)

    @field_serializer("profile_picture_url")
    def serialize_profile_picture_url(self, value: str | None) -> str | None:
        return get_profile_photo_read_url(value)


class UserWithCapabilitiesRead(UserRead):
    capabilities: list[str] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = ""
    last_name: str = ""
    middle_name: str | None = None
    gender: str | None = None
    education: str | None = None
    civil_status: str | None = None
    religion: str | None = None
    rank: str | None = None
    position_id: int | None = None
    rank_level: int | None = None
    step_number: int | None = None
    assignment_effective_from: date | None = None
    assignment_change_reason: str | None = None
    employee_number: str | None = None
    biometric_uid: int | None = None
    role: str | None = None
    department_id: int | None = None
    phone_number: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    date_of_hiring: date | None = None
    resignation_date: date | None = None
    profile_picture_url: str | None = None
    can_modify_shift: bool = False
    is_active: bool = True
    is_superuser: bool = False

    @field_validator("rank", mode="before")
    @classmethod
    def normalize_rank_value(cls, value: str | None) -> str | None:
        return normalize_rank(value)

    @field_validator("rank_level")
    @classmethod
    def validate_rank_level(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Rank level must be at least 1.")
        return value

    @field_validator("step_number")
    @classmethod
    def validate_step_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Step number must be at least 1.")
        return value


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    gender: str | None = None
    education: str | None = None
    civil_status: str | None = None
    religion: str | None = None
    rank: str | None = None
    position_id: int | None = None
    rank_level: int | None = None
    step_number: int | None = None
    assignment_effective_from: date | None = None
    assignment_change_reason: str | None = None
    employee_number: str | None = None
    biometric_uid: int | None = None
    role: str | None = None
    department_id: int | None = None
    phone_number: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    date_of_hiring: date | None = None
    resignation_date: date | None = None
    profile_picture_url: str | None = None
    can_modify_shift: bool | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None

    @field_validator("rank", mode="before")
    @classmethod
    def normalize_rank_value(cls, value: str | None) -> str | None:
        return normalize_rank(value)

    @field_validator("rank_level")
    @classmethod
    def validate_rank_level(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Rank level must be at least 1.")
        return value

    @field_validator("step_number")
    @classmethod
    def validate_step_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Step number must be at least 1.")
        return value


class UserBiometricUpdateRequest(BaseModel):
    biometric_uid: int | None = None


class UserProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    gender: str | None = None
    education: str | None = None
    civil_status: str | None = None
    religion: str | None = None
    phone_number: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    date_of_hiring: date | None = None
    profile_picture_url: str | None = None
