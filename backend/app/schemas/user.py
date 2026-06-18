from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole
    full_name: str | None = Field(None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None


class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
    type: str | None = None
