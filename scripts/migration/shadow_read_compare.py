from __future__ import annotations

import argparse
from pathlib import Path

from migration_dry_run import build_plan


ROOT = Path(__file__).resolve().parents[2]


def build_shadow_queries() -> list[dict[str, str]]:
    plan = build_plan()
    rows = []
    for table in plan["tables"]:  # type: ignore[index]
        if table["stance"] != "keep":
            continue
        rows.append(
            {
                "old_table": table["old_table"],
                "new_table": table["new_table"],
                "row_count_query": f"select count(*) from {table['old_table']};",
                "verification_query": table["verification_query"],
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the TrueCare shadow-read comparison query contract.")
    parser.add_argument("--list", action="store_true", help="Print each comparison query.")
    args = parser.parse_args()
    rows = build_shadow_queries()
    if len(rows) < 25:
        raise SystemExit(f"expected at least 25 kept-table shadow checks, found {len(rows)}")
    if args.list:
        for row in rows:
            print(f"{row['old_table']} -> {row['new_table']}: {row['verification_query']}")
    else:
        print(f"ok: shadow-read dry-run covers {len(rows)} kept-table verification queries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
