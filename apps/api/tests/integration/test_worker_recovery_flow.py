from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.db.models import Booking, DomainEvent, ProcessedDomainEvent, Profile, SlotCapacity, WorkerRun
from app.db.session import get_sessionmaker, set_local_context
from app.jobs.worker import drain_once
from app.main import create_app
from app.services.booking_service import REPEAT_NO_SHOW_DEPOSIT_AMOUNT

from test_marketplace_flow import _seed_marketplace, _signup

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_worker_expires_stale_hold_to_no_show_and_next_hold_gets_deposit() -> None:
    client = TestClient(create_app())
    access_token, tenant_id, user_id = await _signup(client)
    merchant_id, service_id = await _seed_marketplace(tenant_id, user_id, slot_count=2)
    headers = {"Authorization": f"Bearer {access_token}"}

    hold = client.post(
        "/v1/bookings/holds",
        json={
            "merchant_id": str(merchant_id),
            "merchant_service_id": str(service_id),
            "bay_number": 1,
            "idempotency_key": f"worker-hold-{uuid4().hex}",
        },
        headers=headers,
    )
    assert hold.status_code == 201, hold.text
    booking_id = UUID(hold.json()["id"])

    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=user_id, role="consumer")
            await session.execute(update(Profile).where(Profile.user_id == user_id).values(no_show_count=1))
            await session.execute(
                update(Booking)
                .where(Booking.id == booking_id)
                .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
            )

    claimed, processed, dead_letters, scheduled_rows = await drain_once("worker-test", 25)
    assert scheduled_rows >= 1
    assert claimed >= processed
    assert dead_letters == 0

    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=user_id, role="consumer")
            booking = await session.get(Booking, booking_id)
            assert booking is not None
            assert booking.status == "no_show"
            profile = await session.get(Profile, user_id)
            assert profile is not None
            assert profile.no_show_count >= 2
            slot = await session.get(SlotCapacity, booking.slot_capacity_id)
            assert slot is not None
            assert slot.status == "available"
            completed_runs = (
                await session.scalars(select(WorkerRun).where(WorkerRun.job_name == "expire_stale_holds", WorkerRun.status == "completed"))
            ).all()
            assert completed_runs

    next_hold = client.post(
        "/v1/bookings/holds",
        json={
            "merchant_id": str(merchant_id),
            "merchant_service_id": str(service_id),
            "bay_number": 1,
            "idempotency_key": f"worker-deposit-{uuid4().hex}",
        },
        headers=headers,
    )
    assert next_hold.status_code == 201, next_hold.text
    assert next_hold.json()["deposit_amount"] == REPEAT_NO_SHOW_DEPOSIT_AMOUNT


@pytest.mark.anyio
async def test_worker_records_processed_events_and_dead_letters_exhausted_failures() -> None:
    client = TestClient(create_app())
    _access_token, tenant_id, user_id = await _signup(client)
    event_id = uuid4()
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=user_id, role="consumer")
            session.add(
                DomainEvent(
                    event_id=event_id,
                    tenant_id=tenant_id,
                    aggregate_type="worker-test",
                    aggregate_id=uuid4(),
                    aggregate_version=1,
                    event_type="worker.force_error",
                    payload={"force_error": "boom"},
                    attempts=2,
                    available_at=datetime.now(UTC) - timedelta(seconds=1),
                )
            )

    claimed, processed, dead_letters, _scheduled_rows = await drain_once("worker-test-deadletter", 25)
    assert claimed >= 1
    assert processed >= 0
    assert dead_letters >= 1

    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=user_id, role="consumer")
            event = await session.get(DomainEvent, event_id)
            assert event is not None
            assert event.dead_letter_reason == "boom"
            processed_event = await session.get(
                ProcessedDomainEvent,
                {"consumer_name": "worker-test-deadletter", "event_id": event_id},
            )
            assert processed_event is not None
            assert processed_event.error_context == {"dead_letter_reason": "boom"}


@pytest.mark.anyio
async def test_worker_processes_orphaned_tenant_events_without_crashing() -> None:
    orphan_tenant_id = uuid4()
    event_id = uuid4()
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=orphan_tenant_id, role="worker")
            session.add(
                DomainEvent(
                    event_id=event_id,
                    tenant_id=orphan_tenant_id,
                    aggregate_type="worker-test",
                    aggregate_id=uuid4(),
                    aggregate_version=1,
                    event_type="worker.orphaned_tenant",
                    payload={},
                    available_at=datetime.now(UTC) - timedelta(seconds=1),
                )
            )

    claimed, processed, dead_letters, _scheduled_rows = await drain_once("worker-test-orphan", 25)
    assert claimed >= 1
    assert processed >= 1
    assert dead_letters >= 0

    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=orphan_tenant_id, role="worker")
            event = await session.get(DomainEvent, event_id)
            assert event is not None
            assert event.processed_at is not None
            processed_event = await session.get(
                ProcessedDomainEvent,
                {"consumer_name": "worker-test-orphan", "event_id": event_id},
            )
            assert processed_event is not None
            assert processed_event.tenant_id is None
