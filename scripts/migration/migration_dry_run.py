from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_MAP = ROOT / "docs/migration-map-v1.md"


def markdown_cells(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def parse_table_map() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_table = False
    for line in MIGRATION_MAP.read_text().splitlines():
        if line.startswith("| Old table |"):
            in_table = True
            continue
        if in_table and line.startswith("## New Tables"):
            break
        if not in_table or not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 9 or cells[0] == "---":
            continue
        old_table, _old_cols, new_table, _new_cols, transformation, rls, seed, rollback, query = cells
        stance = "keep"
        normalized_new = new_table.lower()
        normalized_transform = transformation.lower()
        if "archive" in normalized_new or "archive" in normalized_transform:
            stance = "archive"
        elif "replace" in normalized_transform or normalized_new in {"domain_events", "processed_domain_events", "app i18n bundles", "deferred"}:
            stance = "replace"
        rows.append(
            {
                "old_table": old_table,
                "new_table": new_table,
                "stance": stance,
                "transformation": transformation,
                "rls_policy_mapping": rls,
                "seed_dependency": seed,
                "rollback_note": rollback,
                "verification_query": re.sub(r"<br\\s*/?>", " ", query),
            }
        )
    return rows


def build_plan() -> dict[str, object]:
    rows = parse_table_map()
    summary = {
        "keep": sum(1 for row in rows if row["stance"] == "keep"),
        "replace": sum(1 for row in rows if row["stance"] == "replace"),
        "archive": sum(1 for row in rows if row["stance"] == "archive"),
    }
    return {
        "source": str(MIGRATION_MAP.relative_to(ROOT)),
        "table_count": len(rows),
        "summary": summary,
        "steps": [
            "validate source snapshot is read-only",
            "run legacy verification queries",
            "apply Alembic head on target",
            "load seed manifest",
            "copy kept tables in dependency order",
            "write archive manifests for archived/deferred tables",
            "run shadow-read comparison",
            "emit checksum report before cutover",
        ],
        "tables": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the TrueCare migration dry-run plan from migration-map-v1.")
    parser.add_argument("--json", action="store_true", help="Emit the full dry-run plan as JSON.")
    args = parser.parse_args()
    plan = build_plan()

    if plan["table_count"] != 37:
        raise SystemExit(f"expected 37 legacy tables, found {plan['table_count']}")

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        summary = plan["summary"]
        print(
            "ok: migration dry-run plan covers "
            f"{plan['table_count']} legacy tables "
            f"(keep={summary['keep']}, replace={summary['replace']}, archive={summary['archive']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
