#!/usr/bin/env bash
set -euo pipefail

: "${EC2_HOST:?EC2_HOST is required}"
: "${EC2_SSH_USER:=ec2-user}"
: "${EC2_SSH_PORT:=22}"
: "${EC2_APP_DIR:=/opt/truecare-new}"
: "${PUBLIC_API_BASE_URL:=https://truecare-new.noboil.dev}"

command -v ssh >/dev/null 2>&1 || {
  echo 'ssh is required' >&2
  exit 1
}

ssh_args=(-p "$EC2_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
if [[ -n "${EC2_SSH_KEY_PATH:-}" ]]; then
  ssh_args+=(-i "$EC2_SSH_KEY_PATH")
fi

remote="${EC2_SSH_USER}@${EC2_HOST}"

ssh "${ssh_args[@]}" "$remote" "set -euo pipefail
command -v docker >/dev/null
docker info >/dev/null
docker compose version >/dev/null
test -d '$EC2_APP_DIR/.git'
test -f '$EC2_APP_DIR/.env'
cd '$EC2_APP_DIR'
docker compose --env-file .env -f infra/compose/compose.staging.yml config >/dev/null
"

if [[ -n "${CLOUDFLARE_TUNNEL_ID:-}" ]] && command -v cloudflared >/dev/null 2>&1; then
  cloudflared tunnel info "$CLOUDFLARE_TUNNEL_ID" >/dev/null
fi

if [[ "${SKIP_PUBLIC_HEALTHCHECK:-0}" != "1" ]]; then
  curl -fsS "$PUBLIC_API_BASE_URL/healthz" >/dev/null
  curl -fsS "$PUBLIC_API_BASE_URL/readyz" >/dev/null
fi

echo ok
