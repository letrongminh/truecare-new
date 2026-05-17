from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)


class SupportRequestResponse(BaseModel):
    request_id: UUID
    status: str


class ProfileResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    display_name: str
    locale: str
    email: str | None = None
    phone: str | None = None
    referral_code: str | None = None
    no_show_count: int = 0
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    locale: str | None = Field(default=None, max_length=16)


class VehicleWriteRequest(BaseModel):
    kind: str = Field(default="sedan", pattern="^(sedan|suv|hatchback|other)$")
    license_plate: str | None = Field(default=None, max_length=40)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = Field(default=None, max_length=80)
    is_default: bool = False


class VehicleUpdateRequest(BaseModel):
    kind: str | None = Field(default=None, pattern="^(sedan|suv|hatchback|other)$")
    license_plate: str | None = Field(default=None, max_length=40)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = Field(default=None, max_length=80)
    is_default: bool | None = None


class VehicleDto(BaseModel):
    id: UUID
    kind: str
    license_plate: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime | None = None


class VehicleListResponse(BaseModel):
    vehicles: list[VehicleDto]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class MutationResponse(BaseModel):
    ok: bool = True


class SessionDto(BaseModel):
    id: str
    subject: UUID
    current: bool = False
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class SessionsResponse(BaseModel):
    sessions: list[SessionDto]


class NotificationRegisterRequest(BaseModel):
    token: str = Field(min_length=8, max_length=4096)
    platform: str = Field(pattern="^(ios|android|web)$")
    device_id: str | None = Field(default=None, max_length=200)


class NotificationPreferencesResponse(BaseModel):
    booking_updates: bool
    golden_hour: bool
    referral_reward: bool
    wash_reminder: bool
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None


class NotificationPreferencesUpdateRequest(BaseModel):
    booking_updates: bool | None = None
    golden_hour: bool | None = None
    referral_reward: bool | None = None
    wash_reminder: bool | None = None
    quiet_hours_start: str | None = Field(default=None, max_length=16)
    quiet_hours_end: str | None = Field(default=None, max_length=16)


class DataExportResponse(BaseModel):
    job_id: UUID
    status: str


class DataExportStatusResponse(BaseModel):
    job_id: UUID
    status: str
    bundle_url: str | None = None
    expires_at: datetime | None = None


class AccountDeletionResponse(BaseModel):
    request_id: UUID
    status: str
    cancel_until: datetime


class OpsUserDto(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str | None = None
    phone: str | None = None
    name: str | None = None
    role: str
    created_at: datetime


class OpsUserListResponse(BaseModel):
    users: list[OpsUserDto]


class OpsUserCreateRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=200)
    role: str = Field(default="ops", pattern="^(ops|merchant|consumer)$")


class OpsPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)


class OpsPasswordResetResponse(BaseModel):
    user_id: UUID
    reset: bool = True
