from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy import text

from app.core.errors import ApiError, ErrorCode
from app.db.models import (
    Booking,
    Complaint,
    DomainEvent,
    Evidence,
    Merchant,
    MerchantService,
    Payment,
    Profile,
    PromoCode,
    RewardStamp,
    RlsProbeRecord,
    ServiceTemplate,
    SlotCapacity,
    Tenant,
    User,
)
from app.db.session import get_engine, get_sessionmaker, set_local_context
from app.services.domain_events import DomainEventRepository
from app.services.idempotency_service import IdempotencyService, IdempotencyStatus


pytestmark = pytest.mark.integration
APP_ROLE_URL = "postgresql+asyncpg://truecare_app:truecare_app@127.0.0.1:55432/truecare"


async def _ensure_app_role(grant_sql: str) -> None:
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
            await session.execute(text(grant_sql))


@pytest.mark.anyio
async def test_rls_probe_isolates_rows_by_tenant() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    await _ensure_app_role("grant select, insert, update, delete on rls_probe_records to truecare_app")

    async with get_sessionmaker(APP_ROLE_URL)() as session:
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
    await get_engine(APP_ROLE_URL).dispose()


@pytest.mark.anyio
async def test_core_rls_tables_hide_cross_tenant_rows() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    await _ensure_app_role(
        "grant select on users, profiles, bookings, payments, evidence, promo_codes, reward_stamps, complaints to truecare_app"
    )

    async with get_sessionmaker()() as session:
        async with session.begin():
            template = await session.scalar(select(ServiceTemplate).order_by(ServiceTemplate.name).limit(1))
            assert template is not None
            now = datetime.now(UTC)
            for tenant_id, label in ((tenant_a, "a"), (tenant_b, "b")):
                user_id = uuid4()
                merchant_id = uuid4()
                service_id = uuid4()
                slot_id = uuid4()
                booking_id = uuid4()
                session.add(Tenant(id=tenant_id, name=f"RLS tenant {label}"))
                await session.flush()
                session.add(
                    User(
                        id=user_id,
                        tenant_id=tenant_id,
                        email=f"rls-{label}-{uuid4().hex}@example.com",
                        password_hash="argon2-placeholder",
                        name=f"RLS {label}",
                        role="consumer",
                    )
                )
                await session.flush()
                session.add(Profile(user_id=user_id, tenant_id=tenant_id, display_name=f"RLS {label}"))
                await session.flush()
                session.add(
                    Merchant(
                        id=merchant_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        name=f"RLS Merchant {label}",
                        address="1 Isolation St",
                        latitude=21.0285,
                        longitude=105.8542,
                        bay_count=1,
                        operating_hours_start="08:00",
                        operating_hours_end="20:00",
                        status="live",
                        pipeline_status="live_full",
                        tags=[],
                    )
                )
                await session.flush()
                session.add(
                    MerchantService(
                        id=service_id,
                        tenant_id=tenant_id,
                        merchant_id=merchant_id,
                        template_id=template.id,
                        name=template.name,
                        price=template.floor_price,
                        duration_min=template.duration_min,
                        duration_max=template.duration_max,
                        status="active",
                        is_custom=False,
                    )
                )
                await session.flush()
                session.add(
                    SlotCapacity(
                        id=slot_id,
                        tenant_id=tenant_id,
                        merchant_id=merchant_id,
                        bay_number=1,
                        time_slot=now + timedelta(days=1),
                        status="held",
                        held_by_user_id=user_id,
                        held_at=now,
                        expires_at=now + timedelta(minutes=30),
                    )
                )
                await session.flush()
                session.add(
                    Booking(
                        id=booking_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        merchant_id=merchant_id,
                        merchant_service_id=service_id,
                        slot_capacity_id=slot_id,
                        bay_number=1,
                        status="completed",
                        held_at=now,
                        expires_at=now + timedelta(minutes=30),
                        total_amount=template.floor_price,
                        discount_amount=0,
                        idempotency_key=f"rls-{label}-{uuid4().hex}",
                        check_in_token=uuid4().hex,
                        completed_at=now,
                    )
                )
                await session.flush()
                session.add_all(
                    [
                        Payment(
                            id=uuid4(),
                            tenant_id=tenant_id,
                            booking_id=booking_id,
                            amount=template.floor_price,
                            method="cash",
                            status="verified",
                            commission_amount=0,
                            commission_status="not_applicable",
                            idempotency_key=f"pay-{label}-{uuid4().hex}",
                        ),
                        Evidence(
                            id=uuid4(),
                            tenant_id=tenant_id,
                            booking_id=booking_id,
                            type="before",
                            object_key=f"rls/{label}.jpg",
                            photo_url=f"local://rls/{label}.jpg",
                            content_type="image/jpeg",
                            status="processed",
                            quality="valid",
                        ),
                        PromoCode(
                            id=uuid4(),
                            tenant_id=tenant_id,
                            code=f"RLS{label.upper()}{uuid4().hex[:6]}",
                            discount_type="fixed",
                            discount_value=10_000,
                            usage_limit_total=10,
                            usage_limit_per_user=1,
                        ),
                        RewardStamp(booking_id=booking_id, tenant_id=tenant_id, user_id=user_id, status="finalized", finalized_at=now),
                        Complaint(
                            id=uuid4(),
                            tenant_id=tenant_id,
                            booking_id=booking_id,
                            user_id=user_id,
                            merchant_id=merchant_id,
                            category="rls",
                            description=f"RLS complaint {label}",
                            evidence_refs=[],
                            status="created",
                        ),
                    ]
                )

    protected_models = (User, Profile, Booking, Payment, Evidence, PromoCode, RewardStamp, Complaint)
    async with get_sessionmaker(APP_ROLE_URL)() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_a)
            for model in protected_models:
                visible_tenants = set((await session.scalars(select(model.tenant_id))).all())
                assert tenant_a in visible_tenants
                assert tenant_b not in visible_tenants

        async with session.begin():
            await set_local_context(session, tenant_id=tenant_b)
            for model in protected_models:
                visible_tenants = set((await session.scalars(select(model.tenant_id))).all())
                assert tenant_b in visible_tenants
                assert tenant_a not in visible_tenants

    await get_engine(APP_ROLE_URL).dispose()


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
