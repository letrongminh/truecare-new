#!/usr/bin/env bash
set -euo pipefail

: "${EC2_HOST:?EC2_HOST is required}"
: "${EC2_SSH_USER:=ec2-user}"
: "${EC2_SSH_PORT:=22}"
: "${EC2_APP_DIR:=/opt/truecare-new}"
: "${PUBLIC_API_BASE_URL:=https://truecare-new.noboil.dev}"

for bin in ssh curl git; do
  command -v "$bin" >/dev/null 2>&1 || {
    printf '%s is required\n' "$bin" >&2
    exit 1
  }
done

ssh_args=(-p "$EC2_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
if [[ -n "${EC2_SSH_KEY_PATH:-}" ]]; then
  ssh_args+=(-i "$EC2_SSH_KEY_PATH")
fi

remote="${EC2_SSH_USER}@${EC2_HOST}"
target_ref="${DEPLOY_REF:-origin/main}"

ssh "${ssh_args[@]}" "$remote" "set -euo pipefail
cd '$EC2_APP_DIR'
git fetch origin main
git checkout -q '$target_ref'
git reset --hard '$target_ref'
docker compose --env-file .env -f infra/compose/compose.staging.yml up -d --build
docker compose -f infra/compose/compose.staging.yml ps
"

curl -fsS "$PUBLIC_API_BASE_URL/healthz" >/dev/null
curl -fsS "$PUBLIC_API_BASE_URL/readyz" >/dev/null

echo ok
