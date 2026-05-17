from uuid import UUID

from pydantic import BaseModel, Field


class AuthExistsRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)


class AuthExistsResponse(BaseModel):
    exists: bool


class SignupRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=200)
    invite_code: str | None = Field(default=None, max_length=64)
    referral_code: str | None = Field(default=None, max_length=64)
    locale: str = Field(default="vi", max_length=16)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=24, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=24, max_length=512)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class AuthMeResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    roles: list[str]
    locale: str | None = None


class LogoutResponse(BaseModel):
    revoked: bool
