from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_CLIS = ("git", "make", "curl", "python3", "node", "corepack", "pnpm", "docker")
OPTIONAL_CLIS = (
    ("maestro", "Maestro mobile runner"),
    ("supabase", "Supabase readiness and policy checks"),
    ("xcrun", "iOS Simulator control"),
    ("emulator", "Android Emulator"),
    ("adb", "Android device bridge"),
    ("eas", "Expo dev-client/build workflows"),
)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def _command_output(command: list[str]) -> str:
    result = _run(command)
    return (result.stdout or result.stderr).strip()


def _node_major() -> int | None:
    output = _command_output(["node", "--version"])
    if not output.startswith("v"):
        return None
    try:
        return int(output.split(".", 1)[0][1:])
    except ValueError:
        return None


def main() -> None:
    failures: list[str] = []
    warnings: list[str] = []

    missing_required = [binary for binary in REQUIRED_CLIS if shutil.which(binary) is None]
    if missing_required:
        failures.append(f"missing required CLIs: {', '.join(missing_required)}")

    if shutil.which("node") is not None:
        major = _node_major()
        if major is None or major < 22 or major % 2 != 0:
            failures.append(f"node must be an active even-numbered release >=22; got {_command_output(['node', '--version']) or '<unknown>'}")

    if shutil.which("git") is not None:
        branch = _command_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if branch != "main":
            failures.append(f"expected to verify from branch main; got {branch or '<unknown>'}")
        head = _command_output(["git", "log", "-1", "--oneline"])
        print(f"repo: {REPO_ROOT}")
        print(f"branch: {branch}")
        print(f"head: {head}")

    if shutil.which("docker") is not None:
        docker = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
        if docker.returncode != 0:
            failures.append("docker CLI is present but Docker daemon is not reachable")
        else:
            print(f"docker: {docker.stdout.strip()}")

    missing_optional = [label for binary, label in OPTIONAL_CLIS if shutil.which(binary) is None]
    if missing_optional:
        warnings.append(f"optional E2E tools not installed: {', '.join(missing_optional)}")

    if not (REPO_ROOT / "node_modules" / "@playwright" / "test").exists():
        warnings.append("project-local @playwright/test is not installed; Ops Playwright journey target will not run yet")

    if not (REPO_ROOT / ".env").exists():
        warnings.append(".env is absent; local-only verification is supported, Supabase readiness remains blocked")

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if failures:
        for failure in failures:
            print(f"error: {failure}", file=sys.stderr)
        raise SystemExit(1)

    print("ok: required local E2E prerequisites are present")


if __name__ == "__main__":
    main()
