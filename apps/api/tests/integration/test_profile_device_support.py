from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import CurrentUser
from app.db.models import AuditLog, Profile, Tenant, TenantMembership, User
from app.db.session import get_sessionmaker, set_local_context
from app.main import create_app
from app.services.auth_service import AuthService, password_hasher


pytestmark = pytest.mark.integration


def _signup(client: TestClient, *, device_id: str | None = None) -> tuple[str, dict[str, object]]:
    identifier = f"profile-{uuid4().hex}@example.com"
    response = client.post(
        "/v1/auth/signup",
        headers={"x-device-id": device_id or f"profile-device-{uuid4().hex}"},
        json={"identifier": identifier, "password": "correct-horse-battery", "display_name": "Profile", "invite_code": "PILOT-HA01"},
    )
    assert response.status_code == 200, response.text
    return identifier, response.json()


async def _ops_token(tenant_id: UUID) -> str:
    async with get_sessionmaker()() as session:
        async with session.begin():
            tenant = await session.get(Tenant, tenant_id)
            assert tenant is not None
            await set_local_context(session, tenant_id=tenant.id)
            user = User(
                tenant_id=tenant.id,
                email=f"ops-{uuid4().hex}@example.com",
                password_hash=password_hasher.hash("correct-horse-battery"),
                name="Ops",
                role="ops",
            )
            session.add(user)
            await session.flush()
            session.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role="ops"))
            session.add(Profile(user_id=user.id, tenant_id=tenant.id, display_name="Ops", locale="vi"))
            await session.flush()
            pair = await AuthService(session).issue_token_pair(user, locale="vi")
            return str(pair["access_token"])


async def _audit_count(current: CurrentUser, action: str) -> int:
    async with get_sessionmaker()() as session:
        async with session.begin():
            await set_local_context(session, tenant_id=current.tenant_id, user_id=current.user_id, role="ops")
            rows = (await session.scalars(select(AuditLog).where(AuditLog.tenant_id == current.tenant_id, AuditLog.action == action))).all()
            return len(rows)


def test_profile_vehicle_sessions_notifications_and_support_flow() -> None:
    client = TestClient(create_app())
    identifier, pair = _signup(client)
    auth = {"Authorization": f"Bearer {pair['access_token']}"}

    forgot = client.post("/v1/auth/forgot-password", json={"identifier": identifier})
    assert forgot.status_code == 200, forgot.text
    assert forgot.json()["status"] == "open"

    profile = client.get("/v1/me/profile", headers=auth)
    assert profile.status_code == 200, profile.text
    assert profile.json()["display_name"] == "Profile"

    patched = client.patch("/v1/me/profile", headers=auth, json={"display_name": "Updated", "locale": "vi"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["display_name"] == "Updated"

    created_vehicle = client.post("/v1/me/vehicles", headers=auth, json={"kind": "sedan", "license_plate": "30A-12345", "is_default": True})
    assert created_vehicle.status_code == 201, created_vehicle.text
    vehicle_id = created_vehicle.json()["id"]
    patched_vehicle = client.patch(f"/v1/me/vehicles/{vehicle_id}", headers=auth, json={"color": "white"})
    assert patched_vehicle.status_code == 200, patched_vehicle.text
    assert patched_vehicle.json()["color"] == "white"
    vehicles = client.get("/v1/me/vehicles", headers=auth)
    assert vehicles.status_code == 200
    assert len(vehicles.json()["vehicles"]) == 1

    preferences = client.patch("/v1/me/notifications/preferences", headers=auth, json={"golden_hour": False})
    assert preferences.status_code == 200, preferences.text
    assert preferences.json()["golden_hour"] is False
    token = client.post("/v1/me/notifications/register", headers=auth, json={"token": f"ExpoPushToken[{uuid4().hex}]", "platform": "ios", "device_id": "ios-test"})
    assert token.status_code == 200, token.text

    sessions = client.get("/v1/me/sessions", headers=auth)
    assert sessions.status_code == 200, sessions.text
    assert sessions.json()["sessions"]
    revoke = client.delete(f"/v1/me/sessions/{sessions.json()['sessions'][0]['id']}", headers=auth)
    assert revoke.status_code == 204

    export = client.post("/v1/me/data-export", headers=auth)
    assert export.status_code == 202, export.text
    export_status = client.get(f"/v1/me/data-export/{export.json()['job_id']}", headers=auth)
    assert export_status.status_code == 200
    assert export_status.json()["status"] == "queued"

    deletion = client.delete("/v1/me/account", headers=auth)
    assert deletion.status_code == 202, deletion.text
    cancel = client.post("/v1/me/cancel-delete", headers=auth)
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.anyio
async def test_device_cap_and_ops_password_reset_audit() -> None:
    client = TestClient(create_app())
    shared_device = f"shared-device-{uuid4().hex}"
    for _ in range(3):
        _signup(client, device_id=shared_device)
    blocked = client.post(
        "/v1/auth/signup",
        headers={"x-device-id": shared_device},
        json={"identifier": f"blocked-{uuid4().hex}@example.com", "password": "correct-horse-battery", "invite_code": "PILOT-HA01"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "DEVICE_LIMIT_EXCEEDED"

    target_identifier, target_pair = _signup(client)
    target_me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {target_pair['access_token']}"})
    target_id = target_me.json()["user_id"]
    target_tenant_id = UUID(target_me.json()["tenant_id"])
    ops_access = await _ops_token(target_tenant_id)
    ops_auth = {"Authorization": f"Bearer {ops_access}"}

    reset = client.post(f"/v1/ops/users/{target_id}/reset-password", headers=ops_auth, json={"new_password": "new-correct-horse"})
    assert reset.status_code == 200, reset.text
    login = client.post("/v1/auth/login", json={"identifier": target_identifier, "password": "new-correct-horse"})
    assert login.status_code == 200, login.text

    ops_me = client.get("/v1/auth/me", headers=ops_auth).json()
    audit_count = await _audit_count(CurrentUser(user_id=UUID(ops_me["user_id"]), tenant_id=UUID(ops_me["tenant_id"]), roles=("ops",)), "user.password_reset")
    assert audit_count >= 1
