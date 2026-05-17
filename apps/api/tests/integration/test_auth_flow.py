from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


pytestmark = pytest.mark.integration


def test_signup_login_refresh_logout_flow() -> None:
    client = TestClient(create_app())
    identifier = f"driver-{uuid4().hex}@example.com"

    signup = client.post(
        "/v1/auth/signup",
        headers={"x-device-id": f"test-device-{uuid4().hex}"},
        json={"identifier": identifier, "password": "correct-horse-battery", "display_name": "Driver", "invite_code": "PILOT-HA01"},
    )
    assert signup.status_code == 200, signup.text
    first_pair = signup.json()
    assert first_pair["token_type"] == "bearer"

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {first_pair['access_token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["roles"] == ["consumer"]

    duplicate = client.post(
        "/v1/auth/signup",
        headers={"x-device-id": f"test-device-{uuid4().hex}"},
        json={"identifier": identifier, "password": "correct-horse-battery", "invite_code": "PILOT-HA01"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_IDENTITY"

    login = client.post("/v1/auth/login", json={"identifier": identifier, "password": "correct-horse-battery"})
    assert login.status_code == 200, login.text

    refresh = client.post("/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["refresh_token"] != login.json()["refresh_token"]

    reuse = client.post("/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert reuse.status_code == 401
    assert reuse.json()["code"] == "TOKEN_REUSED"

    logout = client.post("/v1/auth/logout", json={"refresh_token": first_pair["refresh_token"]})
    assert logout.status_code == 200
    assert logout.json()["revoked"] is True
