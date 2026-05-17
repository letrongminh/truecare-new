from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEED_PLAN = ROOT / "docs/seed-plan-v1.json"
REQUIRED_GROUPS = {"tenant", "service_templates", "worker_jobs"}


def load_seed_plan() -> dict:
    return json.loads(SEED_PLAN.read_text())


def validate_seed_plan(plan: dict) -> list[str]:
    errors: list[str] = []
    groups = plan.get("groups") or []
    names = {group.get("name") for group in groups}
    missing = REQUIRED_GROUPS - names
    for group in sorted(missing):
        errors.append(f"missing required seed group: {group}")

    for group in groups:
        name = group.get("name", "<unnamed>")
        if group.get("required") and not group.get("rows"):
            errors.append(f"required seed group has no rows: {name}")
        if not group.get("table"):
            errors.append(f"seed group missing table: {name}")
        if not group.get("naturalKey"):
            errors.append(f"seed group missing naturalKey: {name}")
        for index, row in enumerate(group.get("rows") or []):
            for key in group.get("naturalKey") or []:
                if key not in row:
                    errors.append(f"seed group {name} row {index} missing natural key {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and render the deterministic TrueCare baseline seed manifest.")
    parser.add_argument("--json", action="store_true", help="Emit the seed plan as JSON.")
    args = parser.parse_args()
    plan = load_seed_plan()
    errors = validate_seed_plan(plan)
    if errors:
        for error in errors:
            print(error)
        return 1

    groups = plan["groups"]
    row_count = sum(len(group.get("rows") or []) for group in groups)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"ok: seed plan covers {len(groups)} groups and {row_count} deterministic rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
