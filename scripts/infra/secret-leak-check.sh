#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

find . -type f \
  -not -path './.git/*' \
  -not -path './.venv/*' \
  -not -path './node_modules/*' \
  -not -path './.pytest_cache/*' \
  -not -path '*/.pytest_cache/*' \
  -not -path '*/__pycache__/*' \
  -not -name '*.swp' \
  -not -name '*.swo' \
  -print0 \
  | xargs -0 rg -n --hidden --no-ignore-vcs \
    -e 'AKIA[0-9A-Z]{16}' \
    -e 'ASIA[0-9A-Z]{16}' \
    -e 'sb_secret_[A-Za-z0-9_-]{20,}' \
    -e '-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----' \
    -e 'xox[baprs]-[A-Za-z0-9-]{20,}' \
    -e 'gh[pousr]_[A-Za-z0-9_]{30,}' \
    >"$tmp" || true

if [[ -s "$tmp" ]]; then
  echo 'possible committed secret material found:' >&2
  cat "$tmp" >&2
  exit 1
fi

echo ok
