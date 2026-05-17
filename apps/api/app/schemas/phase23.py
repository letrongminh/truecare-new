from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidencePresignRequest(BaseModel):
    type: str = Field(pattern="^(before|after)$")
    content_type: str = Field(default="image/jpeg", pattern="^image/(jpeg|png)$")


class EvidencePresignResponse(BaseModel):
    evidence_id: UUID
    object_key: str
    upload_url: str


class EvidenceConfirmRequest(BaseModel):
    object_key: str
    perceptual_hash: str | None = Field(default=None, max_length=128)
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy_meters: float | None = None


class EvidenceDto(BaseModel):
    id: UUID
    booking_id: UUID
    type: str
    photo_url: str
    status: str
    quality: str
    latitude: float | None = None
    longitude: float | None = None
    perceptual_hash: str | None = None
    watermarked_at: datetime | None = None
    exif_stripped: bool = False
    retry_attempts: int = 0
    retry_exhausted_at: datetime | None = None
    ops_review_required: bool = False


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceDto]


class InitiatePaymentRequest(BaseModel):
    booking_id: UUID
    method: str = Field(pattern="^(qr_transfer|cash|vetc_wallet)$")
    idempotency_key: str = Field(min_length=8, max_length=200)


class MerchantDeniedPaymentRequest(BaseModel):
    reason: str | None = Field(default=None, pattern="^(not_received|wrong_amount|other)$")


class SwitchPaymentMethodRequest(BaseModel):
    method: str = Field(pattern="^(qr_transfer|cash)$")


class PaymentDto(BaseModel):
    id: UUID
    booking_id: UUID
    amount: int
    method: str
    status: str
    merchant_confirmed_at: datetime | None = None
    created_at: datetime
    commission_amount: int = 0
    commission_status: str = "not_applicable"
    merchant_payment_qr_url: str | None = None


class CreateRatingRequest(BaseModel):
    rating: str = Field(pattern="^(positive|negative)$")
    comment: str | None = Field(default=None, max_length=500)
    tip: int | None = Field(default=None, ge=0)
    reasons: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)


class RatingDto(BaseModel):
    id: UUID
    booking_id: UUID
    rating: str
    comment: str | None = None
    created_at: datetime


class PromoValidateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    order_amount: int = Field(gt=0)
    merchant_id: UUID | None = None
    service_template_id: UUID | None = None


class PromoValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_amount: int = 0
    reason: str | None = None


class PromoCodeDto(BaseModel):
    id: UUID
    code: str
    discount_type: str
    discount_value: int
    max_discount_amount: int | None = None
    min_order_amount: int | None = None
    usage_limit_total: int
    used_count: int
    is_active: bool


class PromoListResponse(BaseModel):
    promo_codes: list[PromoCodeDto]


class CreatePromoCodeRequest(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    discount_type: str = Field(pattern="^(percent|fixed)$")
    discount_value: int = Field(gt=0)
    max_discount_amount: int | None = Field(default=None, ge=0)
    min_order_amount: int | None = Field(default=None, ge=0)
    merchant_id: UUID | None = None
    service_template_id: UUID | None = None
    usage_limit_total: int = Field(default=100, ge=1)
    usage_limit_per_user: int = Field(default=1, ge=1)


class RewardProgressResponse(BaseModel):
    finalized_stamps: int
    pending_stamps: int
    threshold: int = 5
    next_reward_at: int


class RewardVoucherDto(BaseModel):
    id: UUID
    status: str
    issued_at: datetime
    expires_at: datetime
    reserved_booking_id: UUID | None = None
    redeemed_booking_id: UUID | None = None


class RewardVoucherListResponse(BaseModel):
    vouchers: list[RewardVoucherDto]


class VoucherBookingRequest(BaseModel):
    booking_id: UUID | None = None


class ReferralDto(BaseModel):
    id: UUID
    type: str
    code: str
    status: str
    reward_status: str
    created_at: datetime


class ReferralMeResponse(BaseModel):
    referral_code: str | None
    referrals: list[ReferralDto]


class ReferralShareEventRequest(BaseModel):
    channel: str = Field(default="copy_link", max_length=80)


class ReferralShareEventResponse(BaseModel):
    recorded: bool


class CreateComplaintRequest(BaseModel):
    booking_id: UUID
    category: str = Field(max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list)


class ComplaintDto(BaseModel):
    id: UUID
    booking_id: UUID
    category: str
    description: str
    evidence_refs: list[str]
    status: str
    resolution: str | None = None
    refund_approved: bool = False
    voucher_action: str | None = None
    created_at: datetime


class OpsComplaintUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    resolution: str | None = Field(default=None, max_length=2000)
    refund_approved: bool | None = None
    voucher_action: str | None = Field(default=None, max_length=40)


class ComplaintListResponse(BaseModel):
    complaints: list[ComplaintDto]


class MerchantServiceWriteRequest(BaseModel):
    merchant_id: UUID
    template_id: UUID | None = None
    name: str | None = Field(default=None, max_length=200)
    price: int = Field(gt=0)
    duration_min: int = Field(gt=0)
    duration_max: int = Field(gt=0)
    status: str = Field(default="active")
    description: str | None = Field(default=None, max_length=1000)


class MerchantServiceUpdateRequest(BaseModel):
    price: int | None = Field(default=None, gt=0)
    duration_min: int | None = Field(default=None, gt=0)
    duration_max: int | None = Field(default=None, gt=0)
    status: str | None = None


class PriceChangeDto(BaseModel):
    old_price: int
    new_price: int
    changed_at: datetime


class PriceHistoryResponse(BaseModel):
    price_changes: list[PriceChangeDto]


class OpsMerchantServiceDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class DailySummaryBookingRow(BaseModel):
    time: datetime
    service_name: str
    amount: int
    method: str | None
    promo_code: str | None = None
    status: str


class DailySummaryResponse(BaseModel):
    services_completed: int
    total_revenue: int
    qr_revenue: int
    cash_revenue: int
    promo_discount_total: int
    average_rating: float
    complaint_count: int
    payout_status: str
    bookings: list[DailySummaryBookingRow]


class CommissionReceivableDto(BaseModel):
    merchant_id: UUID
    merchant_name: str
    total_bookings: int
    total_revenue: int
    commission_receivable: int
    commission_status: str


class CommissionReceivablesResponse(BaseModel):
    receivables: list[CommissionReceivableDto]


class AuditLogDto(BaseModel):
    id: UUID
    actor_user_id: UUID | None = None
    action: str
    target_kind: str
    target_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    recorded_at: datetime


class AuditLogResponse(BaseModel):
    audit_log: list[AuditLogDto]


class RealtimeTokenResponse(BaseModel):
    token: str
    expires_in: int = 300
