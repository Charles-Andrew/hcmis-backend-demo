from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.user import UserWithCapabilitiesRead


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1)
    password: str = Field(min_length=8)
    first_name: str = ""
    last_name: str = ""
    employee_number: str | None = None
    role: str | None = None
    department_name: str | None = None
    department_code: str | None = None

    @model_validator(mode="after")
    def validate_username_required(self) -> "AuthRegisterRequest":
        if self.username.strip() == "":
            raise ValueError("Username is required.")
        return self


class AuthLoginRequest(BaseModel):
    identifier: str | None = None
    email: EmailStr | None = None
    password: str

    @model_validator(mode="after")
    def validate_identifier(self) -> "AuthLoginRequest":
        normalized_identifier = (self.identifier or "").strip()
        normalized_email = (str(self.email) if self.email is not None else "").strip()
        if normalized_identifier == "" and normalized_email == "":
            raise ValueError("Email/username and password are required.")
        return self


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserWithCapabilitiesRead


class AuthChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=8)


class UserPasswordResetResponse(BaseModel):
    temporary_password: str
