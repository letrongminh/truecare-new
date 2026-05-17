from fastapi.testclient import TestClient

from app.main import create_app


def test_openapi_contains_contract_stub_paths() -> None:
    schema = create_app().openapi()

    assert "/v1/bookings/holds" in schema["paths"]
    assert "/v1/payments/{id}/merchant-denied" in schema["paths"]
    assert "/v1/realtime/token" in schema["paths"]


def test_contract_stub_returns_typed_problem_details() -> None:
    client = TestClient(create_app())

    response = client.post("/v1/payments/initiate", headers={"x-request-id": "stub-request"})

    assert response.status_code == 501
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "NOT_IMPLEMENTED"
    assert body["requestId"] == "stub-request"
    assert body["extra"]["path"] == "/v1/payments/initiate"
