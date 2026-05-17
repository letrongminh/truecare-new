from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.models import Booking, Merchant, MerchantService, ServiceTemplate, SlotCapacity
from app.db.session import get_sessionmaker
from app.main import create_app
from app.services.marketplace_service import round_to_current_slot


pytestmark = pytest.mark.integration


async def _signup(client: TestClient) -> tuple[str, UUID, UUID]:
    signup = client.post(
        "/v1/auth/signup",
        json={
            "identifier": f"marketplace-{uuid4().hex}@example.com",
            "password": "correct-horse-battery",
            "display_name": "Marketplace Tester",
        },
    )
    assert signup.status_code == 200, signup.text
    access_token = signup.json()["access_token"]
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200, me.text
    return access_token, UUID(me.json()["tenant_id"]), UUID(me.json()["user_id"])


async def _seed_marketplace(tenant_id: UUID, user_id: UUID) -> tuple[UUID, UUID]:
    merchant_id = uuid4()
    service_id = uuid4()
    now_slot = round_to_current_slot()
    async with get_sessionmaker()() as session:
        async with session.begin():
            await session.execute(delete(Booking).where(Booking.tenant_id == tenant_id))
            await session.execute(delete(SlotCapacity).where(SlotCapacity.tenant_id == tenant_id))
            await session.execute(delete(MerchantService).where(MerchantService.tenant_id == tenant_id))
            await session.execute(delete(Merchant).where(Merchant.tenant_id == tenant_id))
            template = await session.scalar(select(ServiceTemplate).order_by(ServiceTemplate.name).limit(1))
            assert template is not None
            session.add(
                Merchant(
                    id=merchant_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    name="TrueCare Hoan Kiem",
                    address="1 Trang Tien, Hoan Kiem, Ha Noi",
                    phone="+84901234567",
                    latitude=21.0285,
                    longitude=105.8542,
                    bay_count=2,
                    operating_hours_start="08:00",
                    operating_hours_end="20:00",
                    status="live",
                    pipeline_status="live_full",
                    tags=["fast_lane", "premium_care"],
                    rating_average=4.8,
                    rating_count=18,
                    storefront_photo_url="https://example.test/shop.jpg",
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
            session.add_all(
                [
                    SlotCapacity(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        merchant_id=merchant_id,
                        bay_number=1,
                        time_slot=now_slot,
                        status="available",
                    ),
                    SlotCapacity(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        merchant_id=merchant_id,
                        bay_number=1,
                        time_slot=now_slot + timedelta(minutes=30),
                        status="available",
                    ),
                ]
            )
    return merchant_id, service_id


@pytest.mark.anyio
async def test_marketplace_catalog_and_booking_hold_flow() -> None:
    client = TestClient(create_app())
    access_token, tenant_id, user_id = await _signup(client)
    merchant_id, service_id = await _seed_marketplace(tenant_id, user_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    templates = client.get("/v1/service-templates")
    assert templates.status_code == 200, templates.text
    assert len(templates.json()["templates"]) >= 6

    nearby = client.get("/v1/merchants/nearby?lat=21.0285&lng=105.8542", headers=headers)
    assert nearby.status_code == 200, nearby.text
    merchant = nearby.json()["merchants"][0]
    assert merchant["id"] == str(merchant_id)
    assert merchant["available_bays"] == 1

    detail = client.get(f"/v1/merchants/{merchant_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["phone"] == "+84901234567"

    services = client.get(f"/v1/merchants/{merchant_id}/services", headers=headers)
    assert services.status_code == 200, services.text
    assert services.json()["services"][0]["id"] == str(service_id)

    hold_body = {
        "merchant_id": str(merchant_id),
        "merchant_service_id": str(service_id),
        "bay_number": 1,
        "idempotency_key": f"hold-{uuid4().hex}",
    }
    hold = client.post("/v1/bookings/holds", json=hold_body, headers=headers)
    assert hold.status_code == 201, hold.text
    booking = hold.json()
    assert booking["status"] == "held"
    assert booking["check_in_token"]

    replay = client.post("/v1/bookings/holds", json=hold_body, headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == booking["id"]

    bookings = client.get("/v1/bookings", headers=headers)
    assert bookings.status_code == 200, bookings.text
    assert [item["id"] for item in bookings.json()["bookings"]] == [booking["id"]]

    cancel = client.post(f"/v1/bookings/{booking['id']}/cancel", json={"reason": "changed_plan"}, headers=headers)
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"

    next_hold = client.post(
        "/v1/bookings/holds",
        json={**hold_body, "idempotency_key": f"hold-{uuid4().hex}"},
        headers=headers,
    )
    assert next_hold.status_code == 201, next_hold.text
    assert next_hold.json()["id"] != booking["id"]
    active_booking = next_hold.json()

    queue = client.get(f"/v1/merchants/{merchant_id}/queue", headers=headers)
    assert queue.status_code == 200, queue.text
    assert [item["id"] for item in queue.json()["queue"]] == [active_booking["id"]]

    bad_check_in = client.post(f"/v1/bookings/{active_booking['id']}/check-in", json={"code": "WRONG"}, headers=headers)
    assert bad_check_in.status_code == 403
    assert bad_check_in.json()["code"] == "INVALID_CHECK_IN_CODE"

    short_code = active_booking["check_in_token"][:6].upper()
    check_in = client.post(f"/v1/bookings/{active_booking['id']}/check-in", json={"code": short_code}, headers=headers)
    assert check_in.status_code == 200, check_in.text
    assert check_in.json()["status"] == "checked_in"
    assert check_in.json()["checked_in_at"] is not None

    start = client.post(f"/v1/bookings/{active_booking['id']}/start-service", headers=headers)
    assert start.status_code == 200, start.text
    assert start.json()["status"] == "in_progress"

    complete = client.post(f"/v1/bookings/{active_booking['id']}/complete-service", headers=headers)
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "awaiting_payment"
    assert complete.json()["service_completed_at"] is not None


@pytest.mark.anyio
async def test_slot_full_is_reported_after_available_slots_are_claimed() -> None:
    client = TestClient(create_app())
    access_token, tenant_id, user_id = await _signup(client)
    merchant_id, service_id = await _seed_marketplace(tenant_id, user_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    base_body = {
        "merchant_id": str(merchant_id),
        "merchant_service_id": str(service_id),
        "bay_number": 1,
    }
    first = client.post("/v1/bookings/holds", json={**base_body, "idempotency_key": f"hold-{uuid4().hex}"}, headers=headers)
    assert first.status_code == 201, first.text
    full = client.post(
        "/v1/bookings/holds",
        json={**base_body, "bay_number": 2, "idempotency_key": f"hold-{uuid4().hex}"},
        headers=headers,
    )
    assert full.status_code == 409
    assert full.json()["code"] == "SLOT_FULL"
