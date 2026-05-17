import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonLogFormatter
from app.main import create_app


def test_json_log_formatter_emits_structured_fields() -> None:
    record = logging.LogRecord(
        name="truecare.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "log-test"  # type: ignore[attr-defined]
    record.method = "GET"  # type: ignore[attr-defined]
    record.path = "/healthz"  # type: ignore[attr-defined]
    record.status_code = 200  # type: ignore[attr-defined]

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "info"
    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "log-test"
    assert payload["path"] == "/healthz"


def test_access_log_records_request_metadata(caplog) -> None:
    client = TestClient(create_app())

    with caplog.at_level(logging.INFO, logger="truecare.access"):
        response = client.get("/healthz", headers={"x-request-id": "access-log-test"})

    assert response.status_code == 200
    record = next(item for item in caplog.records if item.name == "truecare.access")
    assert record.message == "request_completed"
    assert record.request_id == "access-log-test"
    assert record.path == "/healthz"
    assert record.status_code == 200
