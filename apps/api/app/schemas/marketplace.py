from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceTemplateDto(BaseModel):
    id: UUID
    name: str
    floor_price: int
    ceiling_price: int
    duration_min: int
    duration_max: int
    evidence_required: str
    sop_checklist_url: str | None = None


class ServiceTemplatesResponse(BaseModel):
    templates: list[ServiceTemplateDto]


class MerchantNearbyDto(BaseModel):
    id: UUID
    name: str
    address: str
    phone: str | None = None
    latitude: float
    longitude: float
    distance_meters: int
    available_bays: int
    bay_count: int
    rating_average: float
    rating_count: int
    service_tags: list[str]
    storefront_photo_url: str | None = None
    operating_hours_start: str
    operating_hours_end: str


class MerchantsNearbyResponse(BaseModel):
    merchants: list[MerchantNearbyDto]
    total: int
    gps_fallback: bool = False


class MerchantServiceDto(BaseModel):
    id: UUID
    merchant_id: UUID
    template_id: UUID | None = None
    name: str
    price: int
    duration_min: int
    duration_max: int
    status: str
    is_custom: bool
    description: str | None = None
    photo_url: str | None = None


class MerchantServicesResponse(BaseModel):
    services: list[MerchantServiceDto]


class MerchantBayDto(BaseModel):
    bay_number: int
    time_slot: datetime
    status: str
    capacity: int = 1


class MerchantBaysResponse(BaseModel):
    bays: list[MerchantBayDto]


class CreateHoldRequest(BaseModel):
    merchant_id: UUID
    merchant_service_id: UUID
    bay_number: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)
    promo_code: str | None = Field(default=None, max_length=64)


class CancelBookingRequest(BaseModel):
    reason: str = Field(default="user_cancelled", max_length=200)


class CheckInRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class BookingDto(BaseModel):
    id: UUID
    merchant_id: UUID
    merchant_service_id: UUID
    bay_number: int
    status: str
    total_amount: int
    discount_amount: int
    deposit_amount: int | None = None
    held_at: datetime
    expires_at: datetime
    checked_in_at: datetime | None = None
    service_completed_at: datetime | None = None
    completed_at: datetime | None = None
    payment_method: str | None = None
    payment_status: str | None = None
    created_at: datetime
    check_in_token: str | None = None


class BookingListResponse(BaseModel):
    bookings: list[BookingDto]


class MerchantQueueResponse(BaseModel):
    queue: list[BookingDto]
