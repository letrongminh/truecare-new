from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.db.models import (
    AuditLog,
    Booking,
    Complaint,
    DataExportJob,
    Evidence,
    Merchant,
    MerchantGoldenHour,
    MerchantService,
    Payment,
    PromoCode,
    PromoCodeUsage,
    Rating,
    RewardStamp,
    RewardVoucher,
    ServiceTemplate,
    SlotCapacity,
    TenantMembership,
    User,
)
from app.db.session import get_sessionmaker, set_local_context
from app.main import create_app
from app.services.marketplace_service import round_to_current_slot

pytestmark = pytest.mark.integration


async def _signup(client: TestClient, prefix: str) -> tuple[dict[str, str], UUID, UUID, str]:
    identifier = f"{prefix}-{uuid4().hex}@example.com"
    response = client.post(
        "/v1/auth/signup",
        json={
            "identifier": identifier,
            "password": "correct-horse-battery",
            "display_name": prefix.title(),
            "invite_code": "PILOT-HA01",
        },
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    return headers, UUID(me.json()["tenant_id"]), UUID(me.json()["user_id"]), identifier


async def _promote_admin(user_id: UUID, tenant_id: UUID) -> None:
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=user_id, role="admin")
            await session.execute(update(TenantMembership).where(TenantMembership.user_id == user_id).values(role="admin"))
            await session.execute(update(User).where(User.id == user_id).values(role="admin"))


async def _seed_marketplace(tenant_id: UUID, owner_id: UUID) -> tuple[UUID, UUID, str]:
    merchant_id = uuid4()
    service_id = uuid4()
    slot_time = round_to_current_slot() + timedelta(minutes=30)
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=owner_id, role="admin")
            await session.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            await session.execute(delete(Complaint).where(Complaint.tenant_id == tenant_id))
            await session.execute(delete(Evidence).where(Evidence.tenant_id == tenant_id))
            await session.execute(delete(Payment).where(Payment.tenant_id == tenant_id))
            await session.execute(delete(Rating).where(Rating.tenant_id == tenant_id))
            await session.execute(delete(PromoCodeUsage).where(PromoCodeUsage.tenant_id == tenant_id))
            await session.execute(delete(PromoCode).where(PromoCode.tenant_id == tenant_id))
            await session.execute(delete(RewardVoucher).where(RewardVoucher.tenant_id == tenant_id))
            await session.execute(delete(RewardStamp).where(RewardStamp.tenant_id == tenant_id))
            await session.execute(delete(DataExportJob).where(DataExportJob.tenant_id == tenant_id))
            await session.execute(delete(Booking).where(Booking.tenant_id == tenant_id))
            await session.execute(delete(SlotCapacity).where(SlotCapacity.tenant_id == tenant_id))
            await session.execute(delete(MerchantGoldenHour).where(MerchantGoldenHour.tenant_id == tenant_id))
            await session.execute(delete(MerchantService).where(MerchantService.tenant_id == tenant_id))
            await session.execute(delete(Merchant).where(Merchant.tenant_id == tenant_id))
            template = await session.scalar(select(ServiceTemplate).order_by(ServiceTemplate.name).limit(1))
            assert template is not None
            session.add(
                Merchant(
                    id=merchant_id,
                    tenant_id=tenant_id,
                    user_id=owner_id,
                    name="TrueCare Route Closure Wash",
                    address="5 Ly Thuong Kiet, Hoan Kiem, Ha Noi",
                    phone="+84901234567",
                    latitude=21.0285,
                    longitude=105.8542,
                    bay_count=2,
                    operating_hours_start="08:00",
                    operating_hours_end="20:00",
                    status="live",
                    pipeline_status="live_full",
                    tags=["fast_lane"],
                    rating_average=4.8,
                    rating_count=12,
                )
            )
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
            for index in range(2):
                session.add(
                    SlotCapacity(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        merchant_id=merchant_id,
                        bay_number=1,
                        time_slot=slot_time + timedelta(minutes=index * 30),
                        status="available",
                    )
                )
    return merchant_id, service_id, slot_time.isoformat()


@pytest.mark.anyio
async def test_remaining_contract_routes_have_local_backing_and_audit() -> None:
    client = TestClient(create_app())
    admin_headers, tenant_id, admin_id, admin_identifier = await _signup(client, "route-admin")
    consumer_headers, tenant_id_again, consumer_id, _consumer_identifier = await _signup(client, "route-consumer")
    assert tenant_id == tenant_id_again
    await _promote_admin(admin_id, tenant_id)
    admin_login = client.post("/v1/auth/login", json={"identifier": admin_identifier, "password": "correct-horse-battery"})
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    merchant_id, service_id, maintenance_slot = await _seed_marketplace(tenant_id, admin_id)

    calendar = client.get(f"/v1/merchants/{merchant_id}/calendar", headers=admin_headers)
    assert calendar.status_code == 200, calendar.text
    assert len(calendar.json()["bays"]) == 2

    maintenance = client.post(
        f"/v1/merchants/{merchant_id}/calendar/maintenance",
        json={"bay_number": 1, "time_slot": maintenance_slot, "status": "maintenance"},
        headers=admin_headers,
    )
    assert maintenance.status_code == 200, maintenance.text
    assert maintenance.json() == {"updated": 1, "status": "closed"}

    golden = client.put(
        f"/v1/merchants/{merchant_id}/golden-hour",
        json={"rules": [{"day_of_week": 1, "start_time": "14:00", "end_time": "16:00", "discount_percent": 20}]},
        headers=admin_headers,
    )
    assert golden.status_code == 200, golden.text
    assert golden.json()["rules"][0]["discount_percent"] == 20
    assert client.get(f"/v1/merchants/{merchant_id}/golden-hour", headers=admin_headers).json()["rules"][0]["day_of_week"] == 1

    fallback = client.post(
        "/v1/ops/bookings",
        json={
            "user_id": str(consumer_id),
            "merchant_id": str(merchant_id),
            "merchant_service_id": str(service_id),
            "bay_number": 1,
            "reason": "consumer called ops desk",
        },
        headers=admin_headers,
    )
    assert fallback.status_code == 201, fallback.text
    booking_id = fallback.json()["id"]
    assert fallback.json()["audit_log_id"]

    mine = client.get("/v1/me/bookings", headers=consumer_headers)
    assert mine.status_code == 200, mine.text
    assert booking_id in {row["id"] for row in mine.json()["bookings"]}

    arrived = client.post(f"/v1/bookings/{booking_id}/arrived", headers=consumer_headers)
    assert arrived.status_code == 200, arrived.text
    assert arrived.json()["id"] == booking_id

    checked_in = client.post(f"/v1/ops/bookings/{booking_id}/check-in", json={"reason": "manual QR fallback"}, headers=admin_headers)
    assert checked_in.status_code == 200, checked_in.text
    assert checked_in.json()["id"] == booking_id

    evidence = client.post(
        "/v1/ops/evidence/upload",
        json={"booking_id": booking_id, "type": "before", "photo_key": f"ops/{booking_id}/before.jpg", "reason": "merchant phone offline"},
        headers=admin_headers,
    )
    assert evidence.status_code == 201, evidence.text

    assert client.post(f"/v1/bookings/{booking_id}/start-service", headers=admin_headers).status_code == 200
    completed = client.post(f"/v1/bookings/{booking_id}/complete-service", headers=admin_headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "awaiting_payment"

    payment = client.post(
        "/v1/payments/initiate",
        json={"booking_id": booking_id, "method": "cash", "idempotency_key": f"cash-{uuid4().hex}"},
        headers=consumer_headers,
    )
    assert payment.status_code == 200, payment.text
    confirmed = client.post(f"/v1/ops/payments/{payment.json()['id']}/confirm", json={"reason": "cash counted at counter"}, headers=admin_headers)
    assert confirmed.status_code == 200, confirmed.text

    voucher = client.post("/v1/ops/reward/voucher", json={"user_id": str(consumer_id), "reason": "service recovery"}, headers=admin_headers)
    assert voucher.status_code == 201, voucher.text
    assert voucher.json()["voucher_id"]

    data_room = client.get("/v1/ops/data-room/bookings", headers=admin_headers)
    assert data_room.status_code == 200, data_room.text
    assert data_room.json()["metrics"]["total_bookings"] >= 1
    export = client.post("/v1/ops/exports", json={"section": "bookings", "format": "csv"}, headers=admin_headers)
    assert export.status_code == 202, export.text
    export_status = client.get(f"/v1/ops/exports/{export.json()['job_id']}", headers=admin_headers)
    assert export_status.status_code == 200, export_status.text
    assert export_status.json()["status"] == "completed"

    audit = client.get("/v1/ops/audit-log", headers=admin_headers)
    assert audit.status_code == 200, audit.text
    actions = {row["action"] for row in audit.json()["audit_log"]}
    assert {
        "merchant.calendar.maintenance",
        "merchant.golden_hour.update",
        "ops_booking.create",
        "ops_booking.check_in",
        "ops_evidence.upload",
        "ops_payment.confirm",
        "ops_reward.voucher",
        "ops_export.create",
    }.issubset(actions)
