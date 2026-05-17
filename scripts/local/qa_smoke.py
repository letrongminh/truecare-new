from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LOCAL_SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from fastapi.testclient import TestClient

from app.main import create_app
from qa_fixtures import PASSWORD, SMOKE_SIGNUP_EMAIL, seed


def _load_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"{path} is missing; run `make local.qa.fixtures` first")
    return json.loads(path.read_text())


def _write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _restore_fixture_baseline(path: Path) -> None:
    _write_artifact(path, asyncio.run(seed()))


class SmokeClient:
    def __init__(self) -> None:
        self.client = TestClient(create_app())

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        expected: int = 200,
        **kwargs: Any,
    ) -> Any:
        headers = kwargs.pop("headers", {})
        if token:
            headers = {**headers, "Authorization": f"Bearer {token}"}
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code != expected:
            raise AssertionError(f"{method} {path} expected {expected}, got {response.status_code}: {response.text}")
        content_type = response.headers.get("content-type", "")
        return response.text if "text/" in content_type else response.json()


def run_smoke(artifact: dict[str, Any]) -> dict[str, Any]:
    smoke = SmokeClient()
    consumer = artifact["personas"]["consumer"]
    merchant = artifact["personas"]["merchant_owner"]
    ops = artifact["personas"]["ops"]
    ids = artifact["ids"]
    merchant_token = merchant["access_token"]
    ops_token = ops["access_token"]
    merchant_id = ids["merchant_id"]
    service_id = ids["merchant_service_id"]

    smoke.request("GET", "/healthz")
    ready = smoke.request("GET", "/readyz")
    if ready["status"] != "ok":
        raise AssertionError(f"readyz not ok: {ready}")

    exists = smoke.request("POST", "/v1/auth/exists", json={"identifier": consumer["identifier"]})
    if exists["exists"] is not True:
        raise AssertionError("seeded consumer identity was not found by auth exists")
    signup = smoke.request(
        "POST",
        "/v1/auth/signup",
        headers={"x-device-id": f"local-smoke-signup-{uuid4().hex}"},
        json={
            "identifier": SMOKE_SIGNUP_EMAIL,
            "password": PASSWORD,
            "display_name": "Local Smoke Signup",
            "invite_code": "PILOT-HA01",
        },
    )
    signup_me = smoke.request("GET", "/v1/auth/me", token=signup["access_token"])
    if signup_me["roles"] != ["consumer"]:
        raise AssertionError("signup user did not receive consumer role")
    login = smoke.request("POST", "/v1/auth/login", json={"identifier": consumer["identifier"], "password": consumer["password"]})
    consumer_token = login["access_token"]

    consumer_me = smoke.request("GET", "/v1/auth/me", token=consumer_token)
    merchant_me = smoke.request("GET", "/v1/auth/me", token=merchant_token)
    ops_me = smoke.request("GET", "/v1/auth/me", token=ops_token)
    if merchant_me["merchant_id"] != merchant_id:
        raise AssertionError("merchant principal is missing seeded merchant context")
    if "ops" not in ops_me["roles"]:
        raise AssertionError("ops principal does not have ops role")

    nearby = smoke.request("GET", "/v1/merchants/nearby", token=consumer_token, params={"lat": 21.0285, "lng": 105.8542})
    if merchant_id not in {row["id"] for row in nearby["merchants"]}:
        raise AssertionError("seeded merchant was not returned by nearby search")
    detail = smoke.request("GET", f"/v1/merchants/{merchant_id}", token=consumer_token)
    services = smoke.request("GET", f"/v1/merchants/{merchant_id}/services", token=consumer_token)
    if detail["id"] != merchant_id or service_id not in {row["id"] for row in services["services"]}:
        raise AssertionError("merchant detail/services did not include seeded records")

    promo = smoke.request("POST", "/v1/promo-codes/validate", token=consumer_token, json={"code": ids["promo_code"], "order_amount": 100_000})
    if not promo["valid"]:
        raise AssertionError(f"seeded promo was not valid: {promo}")

    hold = smoke.request(
        "POST",
        "/v1/bookings/holds",
        token=consumer_token,
        expected=201,
        json={
            "merchant_id": merchant_id,
            "merchant_service_id": service_id,
            "bay_number": 1,
            "idempotency_key": f"local-smoke-hold-{uuid4().hex}",
        },
    )
    booking_id = hold["id"]
    smoke.request("POST", f"/v1/bookings/{booking_id}/arrived", token=consumer_token)
    queue = smoke.request("GET", f"/v1/merchants/{merchant_id}/queue", token=merchant_token)
    if booking_id not in {row["id"] for row in queue["queue"]}:
        raise AssertionError("merchant queue did not include the active smoke booking")

    presign = smoke.request("POST", f"/v1/evidence/{booking_id}/presign", token=consumer_token, json={"type": "before", "content_type": "image/jpeg"})
    evidence = smoke.request(
        "POST",
        f"/v1/evidence/{presign['evidence_id']}/confirm",
        token=consumer_token,
        json={"object_key": presign["object_key"], "perceptual_hash": "local-smoke-before", "latitude": 21.0285, "longitude": 105.8542, "gps_accuracy_meters": 20},
    )
    if evidence["status"] != "processed":
        raise AssertionError("evidence did not process")

    check_in_code = hold["check_in_token"][:6].upper()
    smoke.request("POST", f"/v1/bookings/{booking_id}/check-in", token=merchant_token, json={"code": check_in_code})
    smoke.request("POST", f"/v1/bookings/{booking_id}/start-service", token=merchant_token)
    complete = smoke.request("POST", f"/v1/bookings/{booking_id}/complete-service", token=merchant_token)
    if complete["status"] != "awaiting_payment":
        raise AssertionError(f"booking did not reach awaiting_payment: {complete}")

    payment = smoke.request("POST", "/v1/payments/initiate", token=consumer_token, json={"booking_id": booking_id, "method": "qr_transfer", "idempotency_key": f"local-smoke-pay-{uuid4().hex}"})
    payment_id = payment["id"]
    smoke.request("POST", f"/v1/payments/{payment_id}/user-claimed", token=consumer_token)
    denied = smoke.request("POST", f"/v1/payments/{payment_id}/merchant-denied", token=merchant_token, json={"reason": "not_received"})
    if denied["status"] != "merchant_denied":
        raise AssertionError("payment was not denied by merchant")
    switched = smoke.request("POST", f"/v1/payments/{payment_id}/switch-method", token=consumer_token, json={"method": "cash"})
    if switched["status"] != "cash_offered":
        raise AssertionError("payment did not switch to cash")
    verified = smoke.request("POST", f"/v1/payments/{payment_id}/cash-record", token=merchant_token)
    if verified["status"] != "verified":
        raise AssertionError("cash payment was not verified")
    rating = smoke.request("POST", f"/v1/bookings/{booking_id}/rate", token=consumer_token, json={"rating": "positive", "comment": "Local smoke passed"})
    if rating["rating"] != "positive":
        raise AssertionError("rating did not persist")

    vouchers = smoke.request("GET", "/v1/rewards/vouchers", token=consumer_token)["vouchers"]
    issued = next((row for row in vouchers if row["status"] == "issued"), None)
    if issued is None:
        raise AssertionError("no issued voucher available for reserve/redeem smoke")
    smoke.request("POST", f"/v1/rewards/vouchers/{issued['id']}/reserve", token=consumer_token, json={"booking_id": booking_id})
    redeemed = smoke.request("POST", f"/v1/rewards/vouchers/{issued['id']}/redeem", token=consumer_token, json={"booking_id": booking_id})
    if redeemed["status"] != "redeemed":
        raise AssertionError("voucher was not redeemed")
    smoke.request("GET", "/v1/referrals/me", token=consumer_token)
    referral = smoke.request("POST", "/v1/referrals/share-event", token=consumer_token, json={"channel": "local_qa"})
    if referral["recorded"] is not True:
        raise AssertionError("referral share event was not recorded")

    complaint = smoke.request("POST", "/v1/complaints", token=consumer_token, expected=201, json={"booking_id": booking_id, "category": "service_quality", "description": "Local QA complaint", "evidence_refs": [presign["object_key"]]})
    ops_complaints = smoke.request("GET", "/v1/ops/complaints", token=ops_token)
    if complaint["id"] not in {row["id"] for row in ops_complaints["complaints"]}:
        raise AssertionError("ops complaints did not include smoke complaint")
    resolved = smoke.request("PATCH", f"/v1/ops/complaints/{complaint['id']}", token=ops_token, json={"status": "resolved", "resolution": "local qa resolved", "refund_approved": False, "voucher_action": "manual_review"})
    if resolved["status"] != "resolved":
        raise AssertionError("complaint was not resolved")

    data_export = smoke.request("POST", "/v1/me/data-export", token=consumer_token, expected=202)
    smoke.request("GET", f"/v1/me/data-export/{data_export['job_id']}", token=consumer_token)
    summary = smoke.request("GET", f"/v1/merchants/{merchant_id}/daily-summary", token=merchant_token)
    if summary["services_completed"] < 1:
        raise AssertionError("daily summary has no completed services")
    smoke.request("GET", f"/v1/merchants/{merchant_id}/daily-summary.csv", token=merchant_token)
    smoke.request("GET", "/v1/ops/commission-receivables", token=ops_token)

    fallback = smoke.request(
        "POST",
        "/v1/ops/bookings",
        token=ops_token,
        expected=201,
        json={
            "user_id": consumer["user_id"],
            "merchant_id": merchant_id,
            "merchant_service_id": service_id,
            "bay_number": 1,
            "reason": "local qa fallback booking",
        },
    )
    fallback_booking_id = fallback["id"]
    smoke.request("POST", f"/v1/ops/bookings/{fallback_booking_id}/check-in", token=ops_token, json={"reason": "local qa manual check-in"})
    smoke.request("POST", "/v1/ops/evidence/upload", token=ops_token, expected=201, json={"booking_id": fallback_booking_id, "type": "before", "photo_key": f"ops/{fallback_booking_id}/before.jpg", "reason": "local qa ops upload"})
    smoke.request("POST", f"/v1/bookings/{fallback_booking_id}/start-service", token=merchant_token)
    smoke.request("POST", f"/v1/bookings/{fallback_booking_id}/complete-service", token=merchant_token)
    fallback_payment = smoke.request("POST", "/v1/payments/initiate", token=consumer_token, json={"booking_id": fallback_booking_id, "method": "cash", "idempotency_key": f"local-smoke-fallback-pay-{uuid4().hex}"})
    smoke.request("POST", f"/v1/ops/payments/{fallback_payment['id']}/confirm", token=ops_token, json={"reason": "local qa cash count"})
    smoke.request("POST", "/v1/ops/reward/voucher", token=ops_token, expected=201, json={"user_id": consumer["user_id"], "reason": "local qa service recovery"})
    data_room = smoke.request("GET", "/v1/ops/data-room/bookings", token=ops_token)
    if data_room["metrics"]["total_bookings"] < 1:
        raise AssertionError("ops data-room has no bookings")
    export = smoke.request("POST", "/v1/ops/exports", token=ops_token, expected=202, json={"section": "bookings", "format": "csv"})
    smoke.request("GET", f"/v1/ops/exports/{export['job_id']}", token=ops_token)
    audit = smoke.request("GET", "/v1/ops/audit-log", token=ops_token)
    actions = {row["action"] for row in audit["audit_log"]}
    required_actions = {"complaint.update", "ops_booking.create", "ops_booking.check_in", "ops_evidence.upload", "ops_payment.confirm", "ops_export.create"}
    missing = required_actions - actions
    if missing:
        raise AssertionError(f"audit log is missing actions: {sorted(missing)}")

    return {
        "consumer_user_id": consumer_me["user_id"],
        "merchant_id": merchant_id,
        "booking_id": booking_id,
        "payment_id": payment_id,
        "fallback_booking_id": fallback_booking_id,
        "ops_user_id": ops_me["user_id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local in-process API smoke against deterministic QA fixtures.")
    parser.add_argument("--artifact", default=".local-e2e.json")
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    result: dict[str, Any] | None = None
    smoke_error: BaseException | None = None
    try:
        result = run_smoke(_load_artifact(artifact_path))
    except BaseException as exc:
        smoke_error = exc
        raise
    finally:
        try:
            _restore_fixture_baseline(artifact_path)
        except Exception as exc:
            if smoke_error is not None:
                print(f"warning: failed to restore local QA fixture baseline after smoke failure: {exc}", file=sys.stderr)
            else:
                raise

    print("ok: local QA smoke passed")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
