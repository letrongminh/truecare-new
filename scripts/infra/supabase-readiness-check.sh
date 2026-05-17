#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
venv_py="${repo_root}/.venv/bin/python"

if [[ ! -x "$venv_py" ]]; then
  printf '.venv is required; run `make venv` first\n' >&2
  exit 1
fi

exec "$venv_py" "$repo_root/scripts/infra/supabase_readiness_check.py"
