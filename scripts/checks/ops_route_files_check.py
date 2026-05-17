from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ROUTES = {
    "apps/ops-web/src/routes/admissions/index.tsx": "ops-admissions",
    "apps/ops-web/src/routes/commission/index.tsx": "ops-commission",
    "apps/ops-web/src/routes/complaints/index.tsx": "ops-complaints",
    "apps/ops-web/src/routes/network-health/index.tsx": "ops-network-health",
    "apps/ops-web/src/routes/growth-ekyc/index.tsx": "ops-growth-ekyc",
    "apps/ops-web/src/routes/audit-log/index.tsx": "ops-audit-log",
}
REQUIRED_STATES = {"loading", "empty", "error", "offline", "forbidden"}


def main() -> None:
    errors: list[str] = []
    for route, test_id_prefix in ROUTES.items():
        path = ROOT / route
        if not path.exists():
            errors.append(f"missing ops route file: {route}")
            continue
        text = path.read_text()
        if "OpsStateSurface" not in text:
            errors.append(f"{route} does not use OpsStateSurface")
        if f'testIDPrefix="{test_id_prefix}"' not in text:
            errors.append(f"{route} does not expose testIDPrefix={test_id_prefix}")

    state_surface = (ROOT / "apps/ops-web/src/components/OpsStateSurface.tsx").read_text()
    for state in REQUIRED_STATES:
        if state not in state_surface:
            errors.append(f"OpsStateSurface missing {state} state surface")

    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"ok: {len(ROUTES)} ops route files present with test IDs and state surfaces")


if __name__ == "__main__":
    main()
