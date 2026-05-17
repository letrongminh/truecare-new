from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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
    processed_at: Mapped[datetime] = utc_now_column()
    result_hash: Mapped[str | None] = mapped_column(String(128))
    error_context: Mapped[dict[str, Any] | None] = mapped_column(JSONType)


class WorkerJob(Base):
    __tablename__ = "worker_jobs"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)
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


class RlsProbeRecord(Base):
    __tablename__ = "rls_probe_records"

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = utc_now_column()

    __table_args__ = (
        UniqueConstraint("tenant_id", "value", name="rls_probe_records_tenant_value_uidx"),
    )
