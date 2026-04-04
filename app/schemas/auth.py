from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserWithCapabilitiesRead


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = ""
    last_name: str = ""
    employee_number: str | None = None
    role: str | None = None
    department_name: str | None = None
    department_code: str | None = None


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserWithCapabilitiesRead


class AuthChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=8)


class UserPasswordResetResponse(BaseModel):
    temporary_password: str
