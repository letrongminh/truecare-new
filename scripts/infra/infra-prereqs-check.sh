#!/usr/bin/env bash
set -euo pipefail

missing=()
for bin in docker node pnpm uv aws gh psql eas supabase jq curl git; do
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

docker info >/dev/null 2>&1 || {
  echo 'docker daemon is not reachable' >&2
  exit 1
}

remote="$(git remote get-url origin 2>/dev/null || true)"
case "$remote" in
  https://github.com/letrongminh/truecare-new.git|git@github.com:letrongminh/truecare-new.git) ;;
  *)
    printf 'unexpected origin remote: %s\n' "${remote:-<none>}" >&2
    exit 1
    ;;
esac

if [[ "${CHECK_MODE:-local}" != "ci" ]]; then
  aws sts get-caller-identity >/dev/null
  gh auth status >/dev/null
  supabase projects list >/dev/null
fi

echo ok
