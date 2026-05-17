from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update

from app.core.security import CurrentUser
from app.db.models import (
    AuditLog,
    Booking,
    Complaint,
    DomainEvent,
    Evidence,
    Merchant,
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
from app.db.session import get_sessionmaker
from app.main import create_app
from app.services.marketplace_service import round_to_current_slot
from app.services.phase23_service import EVIDENCE_RETRY_EXHAUSTION_THRESHOLD, Phase23Service

pytestmark = pytest.mark.integration


async def _signup_admin(client: TestClient) -> tuple[str, UUID, UUID]:
    identifier = f"phase23-{uuid4().hex}@example.com"
    signup = client.post(
        "/v1/auth/signup",
        json={"identifier": identifier, "password": "correct-horse-battery", "display_name": "Phase 23"},
    )
    assert signup.status_code == 200, signup.text
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {signup.json()['access_token']}"})
    tenant_id = UUID(me.json()["tenant_id"])
    user_id = UUID(me.json()["user_id"])
    async with get_sessionmaker()() as session:
        async with session.begin():
            await session.execute(update(TenantMembership).where(TenantMembership.user_id == user_id).values(role="admin"))
            await session.execute(update(User).where(User.id == user_id).values(role="admin"))
    login = client.post("/v1/auth/login", json={"identifier": identifier, "password": "correct-horse-battery"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"], tenant_id, user_id


async def _seed_marketplace(tenant_id: UUID, user_id: UUID) -> tuple[UUID, UUID]:
    merchant_id = uuid4()
    service_id = uuid4()
    now_slot = round_to_current_slot()
    async with get_sessionmaker()() as session:
        async with session.begin():
            await session.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            await session.execute(delete(Complaint).where(Complaint.tenant_id == tenant_id))
            await session.execute(delete(Evidence).where(Evidence.tenant_id == tenant_id))
            await session.execute(delete(Payment).where(Payment.tenant_id == tenant_id))
            await session.execute(delete(Rating).where(Rating.tenant_id == tenant_id))
            await session.execute(delete(PromoCodeUsage).where(PromoCodeUsage.tenant_id == tenant_id))
            await session.execute(delete(PromoCode).where(PromoCode.tenant_id == tenant_id))
            await session.execute(delete(RewardVoucher).where(RewardVoucher.tenant_id == tenant_id))
            await session.execute(delete(RewardStamp).where(RewardStamp.tenant_id == tenant_id))
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
                    name="TrueCare Phase 23",
                    address="2 Trang Tien, Hoan Kiem, Ha Noi",
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
                    rating_count=18,
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
            session.add(
                SlotCapacity(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    bay_number=1,
                    time_slot=now_slot + timedelta(minutes=30),
                    status="available",
                )
            )
    return merchant_id, service_id


@pytest.mark.anyio
async def test_phase2_phase3_backend_flow() -> None:
    client = TestClient(create_app())
    access_token, tenant_id, user_id = await _signup_admin(client)
    merchant_id, service_id = await _seed_marketplace(tenant_id, user_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    promo = client.post(
        "/v1/ops/promo-codes",
        json={"code": "PILOT20", "discount_type": "fixed", "discount_value": 20_000, "usage_limit_total": 10},
        headers=headers,
    )
    assert promo.status_code == 200, promo.text
    promo_check = client.post("/v1/promo-codes/validate", json={"code": "PILOT20", "order_amount": 100_000}, headers=headers)
    assert promo_check.status_code == 200, promo_check.text
    assert promo_check.json()["discount_amount"] == 20_000

    hold = client.post(
        "/v1/bookings/holds",
        json={
            "merchant_id": str(merchant_id),
            "merchant_service_id": str(service_id),
            "bay_number": 1,
            "idempotency_key": f"hold-{uuid4().hex}",
        },
        headers=headers,
    )
    assert hold.status_code == 201, hold.text
    booking = hold.json()

    before = client.post(f"/v1/evidence/{booking['id']}/presign", json={"type": "before", "content_type": "image/jpeg"}, headers=headers)
    assert before.status_code == 200, before.text
    confirmed = client.post(
        f"/v1/evidence/{before.json()['evidence_id']}/confirm",
        json={"object_key": before.json()["object_key"], "perceptual_hash": "abc123"},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "processed"

    check_in = client.post(f"/v1/bookings/{booking['id']}/check-in", json={"code": booking["check_in_token"][:6].upper()}, headers=headers)
    assert check_in.status_code == 200, check_in.text
    assert client.post(f"/v1/bookings/{booking['id']}/start-service", headers=headers).status_code == 200
    complete = client.post(f"/v1/bookings/{booking['id']}/complete-service", headers=headers)
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "awaiting_payment"

    payment = client.post(
        "/v1/payments/initiate",
        json={"booking_id": booking["id"], "method": "qr_transfer", "idempotency_key": f"pay-{uuid4().hex}"},
        headers=headers,
    )
    assert payment.status_code == 200, payment.text
    payment_id = payment.json()["id"]
    claimed = client.post(f"/v1/payments/{payment_id}/user-claimed", headers=headers)
    assert claimed.status_code == 200, claimed.text
    verified = client.post(f"/v1/payments/{payment_id}/merchant-confirmed", headers=headers)
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"

    rating = client.post(f"/v1/bookings/{booking['id']}/rate", json={"rating": "positive", "comment": "Tot"}, headers=headers)
    assert rating.status_code == 200, rating.text
    progress = client.get("/v1/rewards/progress", headers=headers)
    assert progress.status_code == 200, progress.text
    assert progress.json()["finalized_stamps"] >= 1

    complaint = client.post(
        "/v1/complaints",
        json={"booking_id": booking["id"], "category": "service_quality", "description": "Needs review"},
        headers=headers,
    )
    assert complaint.status_code == 201, complaint.text
    ops_complaints = client.get("/v1/ops/complaints", headers=headers)
    assert ops_complaints.status_code == 200, ops_complaints.text
    assert ops_complaints.json()["complaints"][0]["id"] == complaint.json()["id"]
    complaint_update = client.patch(
        f"/v1/ops/complaints/{complaint.json()['id']}",
        json={"status": "resolved", "resolution": "voucher issued", "refund_approved": False, "voucher_action": "manual_review"},
        headers=headers,
    )
    assert complaint_update.status_code == 200, complaint_update.text
    assert complaint_update.json()["status"] == "resolved"

    custom = client.post(
        "/v1/merchant-services/custom",
        json={
            "merchant_id": str(merchant_id),
            "name": "Cham soc lop",
            "price": 50_000,
            "duration_min": 10,
            "duration_max": 15,
            "status": "pending_review",
        },
        headers=headers,
    )
    assert custom.status_code == 200, custom.text
    rejected = client.post(f"/v1/ops/merchant-services/{custom.json()['id']}/reject", json={"reason": "need_photo"}, headers=headers)
    assert rejected.status_code == 200, rejected.text
    resubmit = client.post(f"/v1/merchant-services/{custom.json()['id']}/resubmit", headers=headers)
    assert resubmit.status_code == 200, resubmit.text
    approved = client.post(f"/v1/ops/merchant-services/{custom.json()['id']}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    updated = client.patch(f"/v1/merchant-services/{custom.json()['id']}", json={"price": 60_000}, headers=headers)
    assert updated.status_code == 200, updated.text
    price_history = client.get(f"/v1/merchant-services/{custom.json()['id']}/price-history", headers=headers)
    assert price_history.status_code == 200, price_history.text
    assert price_history.json()["price_changes"][0]["new_price"] == 60_000

    summary = client.get(f"/v1/merchants/{merchant_id}/daily-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["services_completed"] >= 1
    csv_summary = client.get(f"/v1/merchants/{merchant_id}/daily-summary.csv", headers=headers)
    assert csv_summary.status_code == 200, csv_summary.text
    csv_rows = list(csv.DictReader(io.StringIO(csv_summary.text)))
    assert csv_rows
    assert csv_summary.text.splitlines()[0] == "time,service_name,amount,method,promo_code,status"
    csv_completed_total = sum(int(row["amount"]) for row in csv_rows if row["status"] in {"completed", "rated"})
    assert csv_completed_total == summary.json()["total_revenue"]
    commission = client.get("/v1/ops/commission-receivables", headers=headers)
    assert commission.status_code == 200, commission.text
    assert commission.json()["receivables"][0]["commission_receivable"] > 0
    audit = client.get("/v1/ops/audit-log", headers=headers)
    assert audit.status_code == 200, audit.text
    actions = {row["action"] for row in audit.json()["audit_log"]}
    assert {"promo_code.create", "complaint.update", "merchant_service.reject", "merchant_service.approve"}.issubset(actions)
    realtime = client.post("/v1/realtime/token", headers=headers)
    assert realtime.status_code == 200, realtime.text
    assert realtime.json()["token"]


@pytest.mark.anyio
async def test_promo_validation_matrix_and_discount_math() -> None:
    client = TestClient(create_app())
    access_token, tenant_id, user_id = await _signup_admin(client)
    merchant_id, service_id = await _seed_marketplace(tenant_id, user_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    now = datetime.now(UTC)
    booking_id = uuid4()
    per_user_promo_id = uuid4()
    async with get_sessionmaker()() as session:
        async with session.begin():
            service = await session.get(MerchantService, service_id)
            assert service is not None and service.template_id is not None
            slot_id = uuid4()
            session.add(
                SlotCapacity(
                    id=slot_id,
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    bay_number=1,
                    time_slot=now + timedelta(days=2),
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
                    total_amount=service.price,
                    discount_amount=0,
                    idempotency_key=f"promo-matrix-{uuid4().hex}",
                    check_in_token=uuid4().hex,
                    completed_at=now,
                )
            )
            await session.flush()
            session.add_all(
                [
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="INACTIVE",
                        discount_type="fixed",
                        discount_value=10_000,
                        usage_limit_total=10,
                        is_active=False,
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="FUTURE",
                        discount_type="fixed",
                        discount_value=10_000,
                        usage_limit_total=10,
                        starts_at=now + timedelta(days=1),
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="EXPIRED",
                        discount_type="fixed",
                        discount_value=10_000,
                        usage_limit_total=10,
                        expires_at=now - timedelta(days=1),
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="USEDUP",
                        discount_type="fixed",
                        discount_value=10_000,
                        usage_limit_total=1,
                        used_count=1,
                    ),
                    PromoCode(
                        id=per_user_promo_id,
                        tenant_id=tenant_id,
                        code="PERUSER",
                        discount_type="fixed",
                        discount_value=10_000,
                        usage_limit_total=10,
                        usage_limit_per_user=1,
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="WRONGMERCHANT",
                        discount_type="fixed",
                        discount_value=10_000,
                        merchant_id=merchant_id,
                        usage_limit_total=10,
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="WRONGSERVICE",
                        discount_type="fixed",
                        discount_value=10_000,
                        service_template_id=service.template_id,
                        usage_limit_total=10,
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="MINORDER",
                        discount_type="fixed",
                        discount_value=10_000,
                        min_order_amount=100_000,
                        usage_limit_total=10,
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="PERCENTCAP",
                        discount_type="percent",
                        discount_value=50,
                        max_discount_amount=20_000,
                        usage_limit_total=10,
                    ),
                    PromoCode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        code="FIXEDCAP",
                        discount_type="fixed",
                        discount_value=30_000,
                        usage_limit_total=10,
                    ),
                ]
            )
            await session.flush()
            session.add(
                PromoCodeUsage(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    promo_code_id=per_user_promo_id,
                    user_id=user_id,
                    booking_id=booking_id,
                    discount_amount=10_000,
                )
            )

    def validate(code: str, *, order_amount: int = 100_000, merchant: UUID | None = None, service_template: UUID | None = None) -> dict:
        payload = {"code": code, "order_amount": order_amount}
        if merchant is not None:
            payload["merchant_id"] = str(merchant)
        if service_template is not None:
            payload["service_template_id"] = str(service_template)
        response = client.post("/v1/promo-codes/validate", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        return response.json()

    assert validate("missing")["reason"] == "not_found"
    assert validate("inactive")["reason"] == "inactive"
    assert validate("future")["reason"] == "not_started"
    assert validate("expired")["reason"] == "expired"
    assert validate("usedup")["reason"] == "exhausted"
    assert validate("peruser")["reason"] == "per_user_limit"
    assert validate("wrongmerchant", merchant=uuid4())["reason"] == "merchant_mismatch"
    assert validate("wrongservice", service_template=uuid4())["reason"] == "service_template_mismatch"
    assert validate("minorder", order_amount=50_000)["reason"] == "min_order_not_met"
    assert validate("percentcap")["discount_amount"] == 20_000
    assert validate("fixedcap", order_amount=20_000)["discount_amount"] == 20_000


@pytest.mark.anyio
async def test_evidence_confirm_is_idempotent_and_retry_exhaustion_marks_ops_review() -> None:
    client = TestClient(create_app())
    access_token, tenant_id, user_id = await _signup_admin(client)
    merchant_id, service_id = await _seed_marketplace(tenant_id, user_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    hold = client.post(
        "/v1/bookings/holds",
        json={
            "merchant_id": str(merchant_id),
            "merchant_service_id": str(service_id),
            "bay_number": 1,
            "idempotency_key": f"evidence-{uuid4().hex}",
        },
        headers=headers,
    )
    assert hold.status_code == 201, hold.text
    booking_id = hold.json()["id"]

    before = client.post(f"/v1/evidence/{booking_id}/presign", json={"type": "before", "content_type": "image/jpeg"}, headers=headers)
    assert before.status_code == 200, before.text
    evidence_id = before.json()["evidence_id"]
    object_key = before.json()["object_key"]
    first = client.post(f"/v1/evidence/{evidence_id}/confirm", json={"object_key": object_key, "perceptual_hash": "abc123"}, headers=headers)
    assert first.status_code == 200, first.text
    second = client.post(f"/v1/evidence/{evidence_id}/confirm", json={"object_key": object_key, "perceptual_hash": "changed"}, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["perceptual_hash"] == "abc123"
    mismatch = client.post(f"/v1/evidence/{evidence_id}/confirm", json={"object_key": f"{object_key}.other"}, headers=headers)
    assert mismatch.status_code == 422
    assert mismatch.json()["code"] == "IDEMPOTENCY_MISMATCH"

    async with get_sessionmaker()() as session:
        processed_events = await session.scalar(
            select(func.count())
            .select_from(DomainEvent)
            .where(DomainEvent.tenant_id == tenant_id, DomainEvent.event_type == "evidence.processed", DomainEvent.aggregate_id == UUID(evidence_id))
        )
    assert processed_events == 1

    retry = client.post(f"/v1/evidence/{booking_id}/presign", json={"type": "after", "content_type": "image/jpeg"}, headers=headers)
    assert retry.status_code == 200, retry.text
    retry_evidence_id = UUID(retry.json()["evidence_id"])
    retry_object_key = retry.json()["object_key"]
    current = CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=("admin",))
    async with get_sessionmaker()() as session:
        async with session.begin():
            service = Phase23Service(session)
            dto = None
            for attempt in range(EVIDENCE_RETRY_EXHAUSTION_THRESHOLD):
                dto = await service.record_evidence_retry_failure(
                    current=current,
                    evidence_id=retry_evidence_id,
                    object_key=retry_object_key,
                    error_message=f"storage timeout {attempt}",
                )
            assert dto is not None
            assert dto.status == "weak_evidence"
            assert dto.quality == "weak_evidence"
            assert dto.retry_attempts == EVIDENCE_RETRY_EXHAUSTION_THRESHOLD
            assert dto.ops_review_required is True

        async with session.begin():
            exhausted_events = await session.scalar(
                select(func.count())
                .select_from(DomainEvent)
                .where(DomainEvent.tenant_id == tenant_id, DomainEvent.event_type == "evidence.retry_exhausted", DomainEvent.aggregate_id == retry_evidence_id)
            )
    assert exhausted_events == 1
