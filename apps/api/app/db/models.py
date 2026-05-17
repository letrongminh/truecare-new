from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from sqlalchemy import Uuid

from app.db.base import Base


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def utc_now_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


JSONType = JSON().with_variant(JSONB, "postgresql")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = utc_now_column()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("users_tenant_email_active", "tenant_id", "email", unique=True, postgresql_where=text("deleted_at is null and email is not null")),
        Index("users_tenant_phone_active", "tenant_id", "phone", unique=True, postgresql_where=text("deleted_at is null and phone is not null")),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="consumer")
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    referral_code: Mapped[str | None] = mapped_column(String(32), unique=True)
    referred_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = utc_now_column()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = utc_now_column()


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="vi")
    no_show_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = utc_now_column()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("refresh_tokens_user", "user_id"),
        Index("refresh_tokens_family", "family_id"),
    )

    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    family_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    parent_hash: Mapped[str | None] = mapped_column(String(128))
    superseded_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = utc_now_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InviteCode(Base):
    __tablename__ = "invite_codes"
    __table_args__ = (
        UniqueConstraint("code", name="invite_codes_code_uidx"),
        Index("invite_codes_tenant", "tenant_id", "expires_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="direct_ops")
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    referred_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = utc_now_column()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceRegistration(Base):
    __tablename__ = "device_registrations"
    __table_args__ = (
        UniqueConstraint("device_id", "user_id", name="device_registrations_device_user_uidx"),
        Index("device_registrations_device", "device_id"),
        Index("device_registrations_user", "user_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = utc_now_column()


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        Index("vehicles_user_active", "user_id", postgresql_where=text("deleted_at is null")),
        Index("vehicles_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="sedan")
    license_plate: Mapped[str | None] = mapped_column(String(40))
    make: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(80))
    year: Mapped[int | None] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(80))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = utc_now_column()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        Index("device_tokens_user", "user_id", "registered_at"),
        Index("device_tokens_device", "device_id"),
    )

    token: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(200))
    registered_at: Mapped[datetime] = utc_now_column()
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    booking_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    golden_hour: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    referral_reward: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    wash_reminder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(16))
    quiet_hours_end: Mapped[str | None] = mapped_column(String(16))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = utc_now_column()


class SupportRequest(Base):
    __tablename__ = "support_requests"
    __table_args__ = (
        Index("support_requests_tenant_status", "tenant_id", "status", "created_at"),
        Index("support_requests_subject", "subject_user_id", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subject_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    created_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    owner_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    identifier: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = utc_now_column()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataExportJob(Base):
    __tablename__ = "data_export_jobs"
    __table_args__ = (Index("data_export_jobs_user", "user_id", "created_at"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    bundle_url: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = utc_now_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccountDeletionRequest(Base):
    __tablename__ = "account_deletion_requests"
    __table_args__ = (Index("account_deletion_requests_user", "user_id", "requested_at"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="waiting")
    requested_at: Mapped[datetime] = utc_now_column()
    cancel_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject: Mapped[str] = mapped_column(String(200), primary_key=True)
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = utc_now_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DomainEvent(Base):
    __tablename__ = "domain_events"
    __table_args__ = (
        Index("domain_events_available", "available_at", "processed_at"),
        Index("domain_events_aggregate", "tenant_id", "aggregate_type", "aggregate_id", "aggregate_version"),
    )

    event_id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trace_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(120))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dead_letter_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = utc_now_column()


class ProcessedDomainEvent(Base):
    __tablename__ = "processed_domain_events"

    consumer_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"))
    processed_at: Mapped[datetime] = utc_now_column()
    result_hash: Mapped[str | None] = mapped_column(String(128))
    error_context: Mapped[dict[str, Any] | None] = mapped_column(JSONType)


class ServiceTemplate(Base):
    __tablename__ = "service_templates"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    floor_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ceiling_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_max: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_required: Mapped[str] = mapped_column(Text, nullable=False)
    sop_checklist_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = utc_now_column()


class Merchant(Base):
    __tablename__ = "merchants"
    __table_args__ = (Index("merchants_tenant_status", "tenant_id", "status"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    bay_count: Mapped[int] = mapped_column(Integer, nullable=False)
    operating_hours_start: Mapped[str] = mapped_column(String(16), nullable=False)
    operating_hours_end: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    pipeline_status: Mapped[str] = mapped_column(String(40), nullable=False, default="longlist")
    tags: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    rating_average: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.10)
    max_bookings_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    storefront_photo_url: Mapped[str | None] = mapped_column(Text)
    bay_photo_url: Mapped[str | None] = mapped_column(Text)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = utc_now_column()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MerchantService(Base):
    __tablename__ = "merchant_services"
    __table_args__ = (Index("merchant_services_merchant", "merchant_id"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    template_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("service_templates.id"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_max: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    ops_reviewed_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    ops_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ops_rejection_reason: Mapped[str | None] = mapped_column(Text)
    resubmit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = utc_now_column()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SlotCapacity(Base):
    __tablename__ = "slot_capacity"
    __table_args__ = (
        UniqueConstraint("merchant_id", "bay_number", "time_slot", name="slot_capacity_merchant_bay_time"),
        Index("slot_capacity_merchant_status", "merchant_id", "status"),
        Index("slot_capacity_held_by_user", "held_by_user_id", postgresql_where=text("status = 'held'")),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    bay_number: Mapped[int] = mapped_column(Integer, nullable=False)
    time_slot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    held_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("bookings_user_status", "user_id", "status", "expires_at"),
        Index("bookings_merchant_status", "merchant_id", "status", "held_at"),
        UniqueConstraint("user_id", "idempotency_key", name="bookings_user_idempotency_uidx"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    merchant_service_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchant_services.id"), nullable=False)
    slot_capacity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("slot_capacity.id"), nullable=False)
    bay_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    held_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    deposit_amount: Mapped[int | None] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    check_in_token: Mapped[str] = mapped_column(String(64), nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_method: Mapped[str | None] = mapped_column(String(40))
    payment_status: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = utc_now_column()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PriceChangeLog(Base):
    __tablename__ = "price_change_log"
    __table_args__ = (Index("price_change_log_service", "merchant_service_id", "changed_at"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    merchant_service_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchant_services.id"), nullable=False)
    old_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    new_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    changed_at: Mapped[datetime] = utc_now_column()


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("evidence_booking", "booking_id", "type"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    gps_accuracy_meters: Mapped[float | None] = mapped_column(Float)
    perceptual_hash: Mapped[str | None] = mapped_column(String(128))
    watermarked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exif_stripped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_exhausted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ops_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_retry_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = utc_now_column()
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("payments_booking", "booking_id"),
        UniqueConstraint("tenant_id", "booking_id", "idempotency_key", name="payments_tenant_booking_idempotency_uidx"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    merchant_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merchant_denied_reason: Mapped[str | None] = mapped_column(String(80))
    commission_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    commission_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_applicable")
    invoice_id: Mapped[str | None] = mapped_column(Text)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waived_reason: Mapped[str | None] = mapped_column(Text)
    dispute_status: Mapped[str] = mapped_column(String(40), nullable=False, default="none")
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    ops_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = utc_now_column()


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("booking_id", name="ratings_booking_unique"),
        Index("ratings_merchant", "merchant_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    rating: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    tip: Mapped[int | None] = mapped_column(BigInteger)
    reasons: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    evidence_urls: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    created_at: Mapped[datetime] = utc_now_column()
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="promo_codes_tenant_code_uidx"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_discount_amount: Mapped[int | None] = mapped_column(BigInteger)
    min_order_amount: Mapped[int | None] = mapped_column(BigInteger)
    merchant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id"))
    service_template_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("service_templates.id"))
    usage_limit_total: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_limit_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    platform_funded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_ops: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = utc_now_column()


class PromoCodeUsage(Base):
    __tablename__ = "promo_code_usages"
    __table_args__ = (
        Index("promo_code_usages_promo", "promo_code_id"),
        UniqueConstraint("user_id", "promo_code_id", name="promo_code_usages_user_promo"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    promo_code_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("promo_codes.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = utc_now_column()


class RewardStamp(Base):
    __tablename__ = "reward_stamps"
    __table_args__ = (Index("reward_stamps_user", "user_id", "status"),)

    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    earned_at: Mapped[datetime] = utc_now_column()
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RewardVoucher(Base):
    __tablename__ = "reward_vouchers"
    __table_args__ = (Index("reward_vouchers_user_status", "user_id", "status"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    service_template_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("service_templates.id"))
    stamp_threshold_reached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_at: Mapped[datetime] = utc_now_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reserved_booking_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"))
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    redeemed_booking_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="issued")
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (Index("referrals_referrer", "referrer_id"),)

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    referrer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    referee_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    reward_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reward_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = utc_now_column()


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        Index("complaints_user", "user_id", "status"),
        Index("complaints_merchant", "merchant_id", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="created")
    resolution: Mapped[str | None] = mapped_column(Text)
    refund_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    voucher_action: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = utc_now_column()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkerJob(Base):
    __tablename__ = "worker_jobs"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"))
    schedule_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_lag_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    catch_up_from: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = utc_now_column()


class WorkerRun(Base):
    __tablename__ = "worker_runs"

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"))
    job_name: Mapped[str] = mapped_column(String(120), ForeignKey("worker_jobs.name"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(120), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = utc_now_column()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    high_watermark: Mapped[str | None] = mapped_column(String(200))
    rows_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_context: Mapped[dict[str, Any] | None] = mapped_column(JSONType)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("audit_log_tenant_recorded", "tenant_id", "recorded_at"),
        Index("audit_log_actor", "actor_user_id", "recorded_at"),
        Index("audit_log_target", "target_kind", "target_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = utc_now_column()
    request_id: Mapped[str | None] = mapped_column(String(80))


class RlsProbeRecord(Base):
    __tablename__ = "rls_probe_records"

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = utc_now_column()

    __table_args__ = (
        UniqueConstraint("tenant_id", "value", name="rls_probe_records_tenant_value_uidx"),
    )
