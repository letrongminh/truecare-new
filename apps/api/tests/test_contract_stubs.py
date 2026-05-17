from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ApiError, api_error_handler
from app.core.request_id import request_id_middleware
from app.main import create_app
from app.routers.contract_stubs import build_contract_router


def test_openapi_contains_contract_stub_paths() -> None:
    schema = create_app().openapi()

    assert "/v1/bookings/holds" in schema["paths"]
    assert "/v1/payments/{id}/merchant-denied" in schema["paths"]
    assert "/v1/realtime/token" in schema["paths"]


def test_contract_stub_returns_typed_problem_details() -> None:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(build_contract_router())
    client = TestClient(app)

    response = client.post("/v1/ops/exports", headers={"x-request-id": "stub-request"})

    assert response.status_code == 501
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "NOT_IMPLEMENTED"
    assert body["requestId"] == "stub-request"
    assert body["extra"]["path"] == "/v1/ops/exports"


def test_application_mounts_no_p0_contract_stubs() -> None:
    schema = create_app().openapi()

    stubbed = [
        (method, path)
        for path, methods in schema["paths"].items()
        for method, spec in methods.items()
        if spec.get("responses", {}).get("501", {}).get("description") == "Contract stub not implemented yet"
    ]
    assert stubbed == []
