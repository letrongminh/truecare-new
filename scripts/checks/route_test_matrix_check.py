#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PORT_PLAN = ROOT / "knowledge/00-porting/port-plan.md"
MATRIX = ROOT / "knowledge/00-porting/route-test-matrix-v1.md"
REQUIRED_STATES = {"loading", "empty", "error", "offline", "forbidden", "retry"}


@dataclass(frozen=True)
class ManifestRoute:
    prd_id: str
    persona: str
    route: str
    complexity: str


@dataclass(frozen=True)
class MatrixRow:
    prd_id: str
    persona: str
    route: str
    complexity: str
    test_id_prefix: str
    unit_tests: str
    e2e_tests: str
    states: set[str]
    owner: str
    status: str


def markdown_cells(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def parse_port_manifest() -> list[ManifestRoute]:
    lines = PORT_PLAN.read_text().splitlines()
    in_section = False
    rows: list[ManifestRoute] = []
    for line in lines:
        if line.startswith("## 14. Mobile Route Manifest"):
            in_section = True
            continue
        if in_section and line.startswith("## 15."):
            break
        if not in_section or not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 5 or cells[0] in {"PRD ID", "---"}:
            continue
        rows.append(ManifestRoute(cells[0], cells[1], cells[2], cells[3]))
    return rows


def parse_matrix() -> list[MatrixRow]:
    rows: list[MatrixRow] = []
    for line in MATRIX.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 10 or cells[0] in {"PRD ID", "---"}:
            continue
        rows.append(
            MatrixRow(
                prd_id=cells[0],
                persona=cells[1],
                route=cells[2],
                complexity=cells[3],
                test_id_prefix=cells[4],
                unit_tests=cells[5],
                e2e_tests=cells[6],
                states={state.strip() for state in cells[7].split(",") if state.strip()},
                owner=cells[8],
                status=cells[9],
            ),
        )
    return rows


def path_refs(value: str) -> list[Path]:
    if value.upper().startswith("TODO"):
        return []
    return [ROOT / item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    errors: list[str] = []
    manifest = parse_port_manifest()
    matrix = parse_matrix()
    manifest_keys = {(row.prd_id, row.route) for row in manifest}
    matrix_keys = {(row.prd_id, row.route) for row in matrix}

    for missing in sorted(manifest_keys - matrix_keys):
        errors.append(f"missing matrix row for {missing[0]} {missing[1]}")

    for extra in sorted(matrix_keys - manifest_keys):
        errors.append(f"matrix row not present in manifest: {extra[0]} {extra[1]}")

    for row in matrix:
        if not row.test_id_prefix or row.test_id_prefix.upper().startswith("TODO"):
            errors.append(f"{row.prd_id} {row.route} is missing testIDPrefix")
        if not row.owner or row.owner.upper().startswith("TODO"):
            errors.append(f"{row.prd_id} {row.route} is missing owner")
        missing_states = REQUIRED_STATES - row.states
        if missing_states:
            errors.append(f"{row.prd_id} {row.route} missing states: {', '.join(sorted(missing_states))}")

        if row.status.upper() != "TODO":
            for ref in path_refs(row.unit_tests) + path_refs(row.e2e_tests):
                if not ref.exists():
                    errors.append(f"{row.prd_id} references missing test file: {ref.relative_to(ROOT)}")
            if row.persona == "Ops" and "Playwright" not in row.e2e_tests:
                errors.append(f"{row.prd_id} ops route must reference Playwright coverage")
            if row.persona != "Ops" and row.complexity in {"H", "VH"} and "Maestro" not in row.e2e_tests:
                errors.append(f"{row.prd_id} H/VH mobile route must reference Maestro coverage")

    if errors:
        print("route-test-matrix check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"ok: {len(manifest)} manifest routes covered by {len(matrix)} matrix rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
