from fastapi.testclient import TestClient

from app.main import create_app


def test_auth_me_requires_bearer_token() -> None:
    response = TestClient(create_app()).get("/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_auth_me_rejects_invalid_bearer_token() -> None:
    response = TestClient(create_app()).get("/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
