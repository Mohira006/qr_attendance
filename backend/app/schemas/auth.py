from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Language, UserRole
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeBrief, lower_email, validate_password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    _lower_email = field_validator("email", mode="before")(lower_email)
    _validate_password = field_validator("password")(validate_password)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    _validate_current = field_validator("current_password")(validate_password)
    _validate_new = field_validator("new_password")(validate_password)


class UserResponse(ORMModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    preferred_language: Language
    employee: EmployeeBrief | None


class LoginResponse(TokenPair):
    user: UserResponse


class UpdateLanguageRequest(BaseModel):
    preferred_language: Language
