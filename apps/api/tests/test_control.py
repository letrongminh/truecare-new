from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_request_id() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz", headers={"x-request-id": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "test-request"


def test_control_routes_are_live() -> None:
    client = TestClient(create_app())

    assert client.get("/readyz").status_code == 200
    assert client.get("/metrics").headers["content-type"].startswith("text/plain")
    assert client.get("/v1/app/version-check").status_code == 200
    assert client.get("/v1/flags").json()["flags"]["search"] is True
