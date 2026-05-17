from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DomainEvent, ProcessedDomainEvent, Tenant


class DomainEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def emit(
        self,
        *,
        tenant_id: UUID,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, Any] | None = None,
        aggregate_version: int = 1,
        schema_version: int = 1,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DomainEvent:
        event = DomainEvent(
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
            event_type=event_type,
            payload=payload or {},
            schema_version=schema_version,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def claim_batch(self, *, consumer_name: str, limit: int = 25, lease_seconds: int = 60) -> list[DomainEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(DomainEvent)
            .where(DomainEvent.processed_at.is_(None))
            .where(DomainEvent.dead_letter_reason.is_(None))
            .where(DomainEvent.available_at <= now)
            .where((DomainEvent.locked_until.is_(None)) | (DomainEvent.locked_until < now))
            .order_by(DomainEvent.available_at, DomainEvent.event_id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = list((await self.session.scalars(stmt)).all())
        for event in events:
            event.locked_by = consumer_name
            event.locked_until = now + timedelta(seconds=lease_seconds)
            event.attempts += 1
        await self.session.flush()
        return events

    async def mark_processed(self, event_id: UUID) -> None:
        await self.session.execute(update(DomainEvent).where(DomainEvent.event_id == event_id).values(processed_at=datetime.now(UTC)))

    async def _ledger_tenant_id(self, event: DomainEvent) -> UUID | None:
        tenant = await self.session.get(Tenant, event.tenant_id)
        return tenant.id if tenant is not None else None

    async def record_processed(
        self,
        *,
        consumer_name: str,
        event: DomainEvent,
        result_hash: str | None = None,
        error_context: dict[str, Any] | None = None,
    ) -> None:
        existing = await self.session.get(ProcessedDomainEvent, {"consumer_name": consumer_name, "event_id": event.event_id})
        if existing is None:
            self.session.add(
                ProcessedDomainEvent(
                    consumer_name=consumer_name,
                    event_id=event.event_id,
                    tenant_id=await self._ledger_tenant_id(event),
                    result_hash=result_hash,
                    error_context=error_context,
                )
            )
        await self.mark_processed(event.event_id)

    async def release_for_retry(self, *, event: DomainEvent, retry_after_seconds: int) -> None:
        event.locked_by = None
        event.locked_until = None
        event.available_at = datetime.now(UTC) + timedelta(seconds=retry_after_seconds)
        await self.session.flush()

    async def mark_dead_letter(self, *, event: DomainEvent, reason: str, consumer_name: str) -> None:
        now = datetime.now(UTC)
        event.dead_letter_reason = reason
        event.locked_by = None
        event.locked_until = None
        event.processed_at = now
        existing = await self.session.get(ProcessedDomainEvent, {"consumer_name": consumer_name, "event_id": event.event_id})
        if existing is None:
            self.session.add(
                ProcessedDomainEvent(
                    consumer_name=consumer_name,
                    event_id=event.event_id,
                    tenant_id=await self._ledger_tenant_id(event),
                    result_hash=None,
                    error_context={"dead_letter_reason": reason},
                )
            )


def new_aggregate_id() -> UUID:
    return uuid4()
