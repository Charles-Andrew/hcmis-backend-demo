from datetime import date, datetime

from pydantic import BaseModel
from pydantic import ConfigDict

from app.schemas.department import DepartmentRead


class UserRead(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    gender: str | None = None
    education: str | None = None
    civil_status: str | None = None
    religion: str | None = None
    rank: str | None = None
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
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    gender: str | None = None
    education: str | None = None
    civil_status: str | None = None
    religion: str | None = None
    rank: str | None = None
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
    rank: str | None = None
    phone_number: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    date_of_hiring: date | None = None
    profile_picture_url: str | None = None
