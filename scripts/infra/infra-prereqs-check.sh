#!/usr/bin/env bash
set -euo pipefail

missing=()
for bin in node python3 corepack supabase curl git; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    missing+=("$bin")
  fi
done

if ((${#missing[@]} > 0)); then
  printf 'missing required tools: %s\n' "${missing[*]}" >&2
  exit 1
fi

node_major="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
if (( node_major < 22 )) || (( node_major % 2 != 0 )); then
  printf 'node major must be an active even-numbered release >=22; got %s\n' "$(node --version)" >&2
  exit 1
fi

remote="$(git remote get-url origin 2>/dev/null || true)"
case "$remote" in
  https://github.com/letrongminh/truecare-new.git|git@github.com:letrongminh/truecare-new.git) ;;
  *)
    printf 'unexpected origin remote: %s\n' "${remote:-<none>}" >&2
    exit 1
    ;;
esac

warnings=()
if ! command -v pnpm >/dev/null 2>&1; then
  warnings+=("pnpm shim not enabled; corepack is available")
fi

for optional in psql jq uv docker aws ssh gh eas; do
  if ! command -v "$optional" >/dev/null 2>&1; then
    warnings+=("$optional")
  fi
done

if ((${#warnings[@]} > 0)); then
  printf 'optional tools not installed yet: %s\n' "${warnings[*]}" >&2
fi

echo ok
