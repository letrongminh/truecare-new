from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy import text

from app.core.errors import ApiError, ErrorCode
from app.db.models import DomainEvent, RlsProbeRecord
from app.db.session import get_engine, get_sessionmaker, set_local_context
from app.services.domain_events import DomainEventRepository
from app.services.idempotency_service import IdempotencyService, IdempotencyStatus


pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_rls_probe_isolates_rows_by_tenant() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    app_role_url = "postgresql+asyncpg://truecare_app:truecare_app@127.0.0.1:55432/truecare"

    async with get_sessionmaker()() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    do $$
                    begin
                      create role truecare_app login password 'truecare_app';
                    exception when duplicate_object then null;
                    end $$;
                    """
                )
            )
            await session.execute(text("grant usage on schema public to truecare_app"))
            await session.execute(text("grant select, insert, update, delete on rls_probe_records to truecare_app"))

    async with get_sessionmaker(app_role_url)() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_a)
            await session.execute(insert(RlsProbeRecord).values(id=uuid4(), tenant_id=tenant_a, value="tenant-a-only"))

        async with session.begin():
            await set_local_context(session, tenant_id=tenant_b)
            hidden = (await session.scalars(select(RlsProbeRecord).where(RlsProbeRecord.value == "tenant-a-only"))).all()

        async with session.begin():
            await set_local_context(session, tenant_id=tenant_a)
            visible = (await session.scalars(select(RlsProbeRecord).where(RlsProbeRecord.value == "tenant-a-only"))).all()

    assert hidden == []
    assert len(visible) == 1
    await get_engine(app_role_url).dispose()


@pytest.mark.anyio
async def test_idempotency_replay_and_mismatch() -> None:
    tenant_id = uuid4()
    async with get_sessionmaker()() as session:
        async with session.begin():
            service = IdempotencyService(session)
            await service.store(
                tenant_id=tenant_id,
                subject="user:test",
                key="hold-1",
                body={"amount": 1},
                response={"ok": True},
            )
            replay = await service.check(tenant_id=tenant_id, subject="user:test", key="hold-1", body={"amount": 1})
            assert replay.status == IdempotencyStatus.replay
            assert replay.response == {"ok": True}

            with pytest.raises(ApiError) as exc:
                await service.check(tenant_id=tenant_id, subject="user:test", key="hold-1", body={"amount": 2})
            assert exc.value.code == ErrorCode.idempotency_mismatch


@pytest.mark.anyio
async def test_domain_event_emit_and_claim() -> None:
    tenant_id = uuid4()
    aggregate_id = uuid4()
    async with get_sessionmaker()() as session:
        async with session.begin():
            await session.execute(delete(DomainEvent))

        async with session.begin():
            repo = DomainEventRepository(session)
            event = await repo.emit(
                tenant_id=tenant_id,
                aggregate_type="booking",
                aggregate_id=aggregate_id,
                event_type="booking.held",
                payload={"booking_id": str(aggregate_id)},
            )

        async with session.begin():
            claimed = await DomainEventRepository(session).claim_batch(consumer_name="test-worker", limit=10)

    assert [event.event_id for event in claimed] == [event.event_id]
    assert claimed[0].locked_by == "test-worker"
