from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MerchantApplicationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: str = Field(min_length=4, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    bay_count: int = Field(default=1, ge=1, le=50)
    operating_hours_start: str = Field(default="08:00", max_length=16)
    operating_hours_end: str = Field(default="20:00", max_length=16)


class MerchantPhotoConfirmRequest(BaseModel):
    storefront_object_key: str = Field(min_length=1, max_length=500)
    bay_object_key: str = Field(min_length=1, max_length=500)


class MerchantPaymentSetupRequest(BaseModel):
    bank_name: str = Field(min_length=2, max_length=120)
    account_number: str = Field(min_length=4, max_length=80)
    account_holder_name: str = Field(min_length=2, max_length=200)
    qr_object_key: str | None = Field(default=None, max_length=500)


class MerchantEkycSubmitRequest(BaseModel):
    object_key: str = Field(min_length=1, max_length=500)


class OpsMerchantDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class MerchantAdmissionDto(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str
    address: str
    phone: str | None = None
    latitude: float
    longitude: float
    bay_count: int
    status: str
    pipeline_status: str
    application_status: str
    photo_status: str
    payment_recipient_status: str
    ekyc_status: str
    go_live_blockers: list[str] = Field(default_factory=list)
    storefront_photo_url: str | None = None
    bay_photo_url: str | None = None
    ops_rejection_reason: str | None = None
    ops_reviewed_by: UUID | None = None
    ops_reviewed_at: datetime | None = None
    created_at: datetime


class MerchantEkycSubmissionDto(BaseModel):
    id: UUID
    kind: str
    object_key: str
    status: str
    submitted_at: datetime


class MerchantEkycStatusResponse(BaseModel):
    merchant_id: UUID
    ekyc_status: str
    submissions: list[MerchantEkycSubmissionDto]


class PendingMerchantsResponse(BaseModel):
    merchants: list[MerchantAdmissionDto]
