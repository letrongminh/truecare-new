from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ArrivedResponse(BaseModel):
    booking_id: UUID
    arrived: bool = True
    recorded_at: datetime


class SlotMaintenanceRequest(BaseModel):
    bay_number: int = Field(ge=1)
    time_slot: datetime
    status: str = Field(default="maintenance", pattern="^(available|maintenance|closed)$")


class SlotMaintenanceResponse(BaseModel):
    updated: int
    status: str


class GoldenHourRuleDto(BaseModel):
    id: UUID
    merchant_id: UUID
    day_of_week: int
    start_time: str
    end_time: str
    discount_percent: int
    updated_at: datetime | None = None


class GoldenHourRuleWrite(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")
    end_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")
    discount_percent: int = Field(ge=0, le=30)


class GoldenHourUpdateRequest(BaseModel):
    rules: list[GoldenHourRuleWrite] = Field(default_factory=list, max_length=7)


class GoldenHourResponse(BaseModel):
    rules: list[GoldenHourRuleDto]


class OpsDataRoomResponse(BaseModel):
    section: str
    generated_at: datetime
    metrics: dict[str, int | float | str | bool | None] = Field(default_factory=dict)
    rows: list[dict[str, int | float | str | bool | None]] = Field(default_factory=list)


class OpsExportRequest(BaseModel):
    section: str = Field(min_length=1, max_length=80)
    format: str = Field(default="csv", pattern="^(csv|json)$")


class OpsExportResponse(BaseModel):
    job_id: UUID
    status: str
    bundle_url: str | None = None
    expires_at: datetime | None = None


class OpsCreateBookingRequest(BaseModel):
    user_id: UUID
    merchant_id: UUID
    merchant_service_id: UUID
    bay_number: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class OpsCheckInRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class OpsEvidenceUploadRequest(BaseModel):
    booking_id: UUID
    type: str = Field(pattern="^(before|after)$")
    photo_key: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=500)


class OpsConfirmPaymentRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class OpsConciergeResultResponse(BaseModel):
    id: UUID
    audit_log_id: UUID


class OpsMintVoucherRequest(BaseModel):
    user_id: UUID
    voucher_type_code: str | None = Field(default=None, max_length=80)
    reason: str = Field(min_length=1, max_length=500)


class OpsMintVoucherResponse(BaseModel):
    voucher_id: UUID
    expires_at: datetime
    audit_log_id: UUID
