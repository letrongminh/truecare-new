from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.models import AuditLog, MerchantEkycSubmission, MerchantPaymentSetup, Profile, Tenant, TenantMembership, User
from app.db.session import get_sessionmaker, set_local_context
from app.main import create_app
from app.services.auth_service import AuthService, password_hasher

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


def _signup(client: TestClient) -> tuple[dict[str, str], UUID, UUID]:
    response = client.post(
        "/v1/auth/signup",
        json={"identifier": f"merchant-{uuid4().hex}@example.com", "password": "correct-horse-battery", "display_name": "Merchant Owner", "invite_code": "PILOT-HA01"},
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    return headers, UUID(me.json()["tenant_id"]), UUID(me.json()["user_id"])


async def _ops_token(tenant_id: UUID) -> str:
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id)
            user = User(
                tenant_id=tenant_id,
                email=f"merchant-ops-{uuid4().hex}@example.com",
                password_hash=password_hasher.hash("correct-horse-battery"),
                name="Merchant Ops",
                role="ops",
            )
            session.add(user)
            await session.flush()
            session.add(TenantMembership(user_id=user.id, tenant_id=tenant_id, role="ops"))
            session.add(Profile(user_id=user.id, tenant_id=tenant_id, display_name="Merchant Ops", locale="vi"))
            await session.flush()
            pair = await AuthService(session).issue_token_pair(user, locale="vi")
            return str(pair["access_token"])


async def _tenant_with_ops_token() -> tuple[UUID, str]:
    tenant_id = uuid4()
    async with get_sessionmaker()() as session:
        async with session.begin():
            session.add(Tenant(id=tenant_id, name=f"Isolated Tenant {tenant_id.hex[:8]}"))
    return tenant_id, await _ops_token(tenant_id)


async def _membership_role(user_id: UUID, tenant_id: UUID) -> str:
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, user_id=user_id, role="merchant")
            membership = await session.get(TenantMembership, (user_id, tenant_id))
            assert membership is not None
            return membership.role


async def _audit_actions(tenant_id: UUID) -> set[str]:
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_id, role="ops")
            rows = (await session.scalars(select(AuditLog.action).where(AuditLog.tenant_id == tenant_id))).all()
            return set(rows)


@pytest.mark.anyio
async def test_merchant_admission_go_live_flow_and_audit() -> None:
    client = TestClient(create_app())
    owner_headers, tenant_id, owner_id = _signup(client)
    ops_headers = {"Authorization": f"Bearer {await _ops_token(tenant_id)}"}

    application = client.post(
        "/v1/merchants/applications",
        headers=owner_headers,
        json={
            "name": "TrueCare Admission Wash",
            "address": "7 Nguyen Trai, Ha Dong, Ha Noi",
            "phone": "+84901234567",
            "latitude": 20.9804,
            "longitude": 105.7871,
            "bay_count": 2,
        },
    )
    assert application.status_code == 201, application.text
    merchant = application.json()
    merchant_id = merchant["id"]
    assert merchant["status"] == "pending_review"
    assert merchant["pipeline_status"] == "pending_setup"
    assert await _membership_role(owner_id, tenant_id) == "merchant"

    pending = client.get("/v1/ops/merchants/pending", headers=ops_headers)
    assert pending.status_code == 200, pending.text
    assert merchant_id in {row["id"] for row in pending.json()["merchants"]}

    blocked = client.post(f"/v1/ops/merchants/{merchant_id}/approve", headers=ops_headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "MERCHANT_GO_LIVE_BLOCKED"
    assert {"photo_required", "payment_recipient_required", "ekyc_required"}.issubset(set(blocked.json()["extra"]["blockers"]))

    photo = client.post(
        f"/v1/merchants/{merchant_id}/confirm-photo",
        headers=owner_headers,
        json={"storefront_object_key": f"merchant/{merchant_id}/storefront.jpg", "bay_object_key": f"merchant/{merchant_id}/bay.jpg"},
    )
    assert photo.status_code == 200, photo.text
    assert photo.json()["photo_status"] == "confirmed"

    payment = client.post(
        f"/v1/merchants/{merchant_id}/payment-setup",
        headers=owner_headers,
        json={"bank_name": "VCB", "account_number": "0123456789", "account_holder_name": "TRUECARE OWNER", "qr_object_key": f"merchant/{merchant_id}/qr.png"},
    )
    assert payment.status_code == 200, payment.text
    assert payment.json()["payment_recipient_status"] == "pending_review"

    for kind in ("cmnd", "selfie", "bank"):
        response = client.post(f"/v1/merchants/{merchant_id}/ekyc/{kind}", headers=owner_headers, json={"object_key": f"merchant/{merchant_id}/ekyc/{kind}.jpg"})
        assert response.status_code == 200, response.text
    status = client.get(f"/v1/merchants/{merchant_id}/ekyc/status", headers=owner_headers)
    assert status.status_code == 200, status.text
    assert status.json()["ekyc_status"] == "submitted"
    assert {row["kind"] for row in status.json()["submissions"]} == {"cmnd", "selfie", "bank"}

    verified = client.post(f"/v1/ops/merchants/{merchant_id}/verify-payment-recipient", headers=ops_headers)
    assert verified.status_code == 200, verified.text
    assert verified.json()["payment_recipient_status"] == "verified"

    approved = client.post(f"/v1/ops/merchants/{merchant_id}/approve", headers=ops_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "live"
    assert approved.json()["pipeline_status"] == "live_full"

    rejected_app = client.post(
        "/v1/merchants/applications",
        headers=owner_headers,
        json={"name": "Rejected Wash", "address": "1 Test Street", "latitude": 21.0, "longitude": 105.8, "bay_count": 1},
    )
    assert rejected_app.status_code == 201, rejected_app.text
    rejected = client.post(f"/v1/ops/merchants/{rejected_app.json()['id']}/reject", headers=ops_headers, json={"reason": "missing_legal_docs"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    suspended = client.post(f"/v1/ops/merchants/{merchant_id}/suspend", headers=ops_headers, json={"reason": "pilot_pause"})
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["status"] == "suspended"

    actions = await _audit_actions(tenant_id)
    assert {"merchant.payment_recipient.verify", "merchant.approve", "merchant.reject", "merchant.suspend"}.issubset(actions)


@pytest.mark.anyio
async def test_merchant_admission_cross_tenant_reads_are_blocked() -> None:
    client = TestClient(create_app())
    owner_headers, tenant_a, _owner_id = _signup(client)
    application = client.post(
        "/v1/merchants/applications",
        headers=owner_headers,
        json={"name": "Tenant A Wash", "address": "1 Tenant A", "latitude": 21.0, "longitude": 105.8, "bay_count": 1},
    )
    assert application.status_code == 201, application.text
    merchant_id = UUID(application.json()["id"])
    assert client.post(f"/v1/merchants/{merchant_id}/payment-setup", headers=owner_headers, json={"bank_name": "VCB", "account_number": "0001", "account_holder_name": "TENANT A"}).status_code == 200
    assert client.post(f"/v1/merchants/{merchant_id}/ekyc/cmnd", headers=owner_headers, json={"object_key": "tenant-a/cmnd.jpg"}).status_code == 200

    tenant_b, tenant_b_ops_token = await _tenant_with_ops_token()
    tenant_b_headers = {"Authorization": f"Bearer {tenant_b_ops_token}"}
    hidden = client.get("/v1/ops/merchants/pending", headers=tenant_b_headers)
    assert hidden.status_code == 200, hidden.text
    assert str(merchant_id) not in {row["id"] for row in hidden.json()["merchants"]}
    forbidden = client.get(f"/v1/merchants/{merchant_id}/ekyc/status", headers=tenant_b_headers)
    assert forbidden.status_code == 404, forbidden.text

    await _ensure_app_role("grant select on merchant_payment_setups, merchant_ekyc_submissions to truecare_app")
    async with get_sessionmaker(APP_ROLE_URL)() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=tenant_b, role="ops")
            payment_rows = (await session.scalars(select(MerchantPaymentSetup).where(MerchantPaymentSetup.merchant_id == merchant_id))).all()
            ekyc_rows = (await session.scalars(select(MerchantEkycSubmission).where(MerchantEkycSubmission.merchant_id == merchant_id))).all()
            assert payment_rows == []
            assert ekyc_rows == []
            assert tenant_a != tenant_b
