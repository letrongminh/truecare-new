from enum import StrEnum


class UserRole(StrEnum):
    consumer = "consumer"
    merchant_pending = "merchant_pending"
    merchant_live = "merchant_live"
    merchant_suspended = "merchant_suspended"
    ops = "ops"
    finance_ops = "finance_ops"
    quality_ops = "quality_ops"
    admin = "admin"


class BookingState(StrEnum):
    held = "held"
    checked_in = "checked_in"
    in_progress = "in_progress"
    awaiting_payment = "awaiting_payment"
    completed = "completed"
    rated = "rated"
    expired = "expired"
    no_show = "no_show"
    cancelled = "cancelled"
    cancelled_by_ops = "cancelled_by_ops"
    payment_disputed = "payment_disputed"


class PaymentState(StrEnum):
    pending = "pending"
    initiated_qr = "initiated_qr"
    user_claimed = "user_claimed"
    cash_offered = "cash_offered"
    verified = "verified"
    merchant_denied = "merchant_denied"
    disputed = "disputed"
    cancelled = "cancelled"


class EvidenceState(StrEnum):
    required = "required"
    presigned = "presigned"
    uploaded = "uploaded"
    processed = "processed"
    approved = "approved"
    weak_evidence = "weak_evidence"
    expired = "expired"
    missing_before = "missing_before"
    missing_after = "missing_after"
    evidence_pending = "evidence_pending"


class RewardVoucherState(StrEnum):
    issued = "issued"
    reserved = "reserved"
    redeemed = "redeemed"
    released = "released"
    expired = "expired"
    frozen = "frozen"
    restored = "restored"
    invalidated = "invalidated"


class MerchantAdmissionState(StrEnum):
    pending_info = "pending_info"
    shop_info = "shop_info"
    photos = "photos"
    payment_setup = "payment_setup"
    pending_review = "pending_review"
    ops_review = "ops_review"
    approved = "approved"
    payment_recipient_verified = "payment_recipient_verified"
    live = "live"
    rejected = "rejected"
    suspended = "suspended"


class CommissionState(StrEnum):
    accrued = "accrued"
    exported = "exported"
    invoiced = "invoiced"
    settled = "settled"
    waived = "waived"
    disputed = "disputed"
    resolved = "resolved"
