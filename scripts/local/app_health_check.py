from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _read_text(url: str, *, token: str | None = None, timeout: float = 5.0) -> tuple[int, str]:
    headers = {"accept": "application/json, text/html;q=0.9, */*;q=0.1"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {body[:400]}") from exc
    except URLError as exc:
        raise RuntimeError(f"{url} is not reachable: {exc.reason}") from exc


def _read_json(url: str, *, token: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    status, text = _read_text(url, token=token, timeout=timeout)
    if status < 200 or status >= 300:
        raise RuntimeError(f"{url} returned HTTP {status}: {text[:400]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{url} did not return JSON: {text[:400]}") from exc


def _load_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"{path} is missing; run `make local.qa.fixtures` first")
    return json.loads(path.read_text())


def _assert_role(name: str, me: dict[str, Any], expected_role: str) -> None:
    roles = set(me.get("roles") or [])
    if expected_role not in roles:
        raise RuntimeError(f"{name} token is missing role {expected_role}; got {sorted(roles)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local API/Ops app endpoints with deterministic local QA tokens.")
    parser.add_argument("--artifact", default=".local-e2e.json")
    parser.add_argument("--api-base-url", default=os.environ.get("LOCAL_API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--ops-url", default=os.environ.get("LOCAL_OPS_URL", "http://127.0.0.1:5173"))
    parser.add_argument("--mobile-status-url", default=os.environ.get("LOCAL_MOBILE_STATUS_URL", ""))
    parser.add_argument("--require-mobile", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    artifact = _load_artifact(Path(args.artifact))
    personas = artifact["personas"]
    ids = artifact["ids"]
    api_base = args.api_base_url.rstrip("/")

    health = _read_json(f"{api_base}/healthz", timeout=args.timeout)
    ready = _read_json(f"{api_base}/readyz", timeout=args.timeout)
    if health.get("status") != "ok":
        raise RuntimeError(f"healthz is not ok: {health}")
    if ready.get("status") != "ok":
        raise RuntimeError(f"readyz is not ok: {ready}")

    consumer_me = _read_json(f"{api_base}/v1/auth/me", token=personas["consumer"]["access_token"], timeout=args.timeout)
    merchant_me = _read_json(f"{api_base}/v1/auth/me", token=personas["merchant_owner"]["access_token"], timeout=args.timeout)
    ops_me = _read_json(f"{api_base}/v1/auth/me", token=personas["ops"]["access_token"], timeout=args.timeout)
    _assert_role("consumer", consumer_me, "consumer")
    _assert_role("merchant owner", merchant_me, "merchant")
    _assert_role("ops", ops_me, "ops")
    if merchant_me.get("merchant_id") != ids["merchant_id"]:
        raise RuntimeError(f"merchant token returned merchant_id={merchant_me.get('merchant_id')}, expected {ids['merchant_id']}")

    _, ops_html = _read_text(args.ops_url.rstrip("/"), timeout=args.timeout)
    if "TrueCare Ops" not in ops_html or 'id="root"' not in ops_html:
        raise RuntimeError(f"{args.ops_url} is reachable but does not look like the Ops web app")

    if args.mobile_status_url:
        _, mobile_text = _read_text(args.mobile_status_url, timeout=args.timeout)
        if "running" not in mobile_text.lower() and "packager-status" not in mobile_text.lower():
            raise RuntimeError(f"{args.mobile_status_url} is reachable but does not look like an Expo/Metro status endpoint")
        print(f"ok: mobile status endpoint reachable at {args.mobile_status_url}")
    elif args.require_mobile:
        raise RuntimeError("mobile status URL is required; set LOCAL_MOBILE_STATUS_URL or omit --require-mobile")
    else:
        print("warning: mobile runtime check skipped; set LOCAL_MOBILE_STATUS_URL to verify Expo/Metro status", file=sys.stderr)

    print("ok: local API health/readiness/auth and Ops web are reachable")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
