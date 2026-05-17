# EC2 Runbook v1

This runbook describes the minimum P0 EC2 Docker Compose runtime. AWS is used only for EC2.

## Topology

```text
Cloudflare Edge
  |
Cloudflare Tunnel
  |
cloudflared container
  |
Caddy reverse proxy
  |-- /healthz, /readyz, /metrics -> api:8000
  |-- /v1/*                        -> api:8000
  |-- /ops/*                       -> ops-web:8080
  \-- default                      -> api:8000

EC2 Docker Compose
  |-- api      built locally from repo
  |-- worker   same local API image, worker command
  |-- ops-web  built locally from repo
  |-- caddy
  \-- cloudflared

Supabase Singapore
  |-- Postgres
  |-- Realtime
  \-- Storage
```

## Provisioning Requirements

- EC2 has Docker Engine, Docker Compose plugin, git, curl, and cloudflared runtime container access.
- EC2 has the repo cloned at `/opt/truecare-new`.
- `/opt/truecare-new/.env` exists and has `0600` permissions.
- Public HTTP traffic enters through Cloudflare Tunnel; EC2 does not expose public `80` or `443`.
- Admin/deploy access is SSH, preferably through Cloudflare Access SSH or a fixed operator IP allowlist.

## Bootstrap Sequence

1. Create EC2 in `ap-southeast-1`.
2. Install Docker, Docker Compose plugin, git, and curl.
3. Clone the repo:
   ```bash
   sudo mkdir -p /opt
   sudo git clone https://github.com/letrongminh/truecare-new.git /opt/truecare-new
   sudo chown -R ec2-user:ec2-user /opt/truecare-new
   ```
4. Create `/opt/truecare-new/.env` from `env-contract-v1.md`.
5. Start Compose:
   ```bash
   cd /opt/truecare-new
   docker compose --env-file .env -f infra/compose/compose.staging.yml up -d --build
   ```
6. Confirm:
   ```bash
   docker compose -f infra/compose/compose.staging.yml ps
   curl -fsS https://truecare-new.noboil.dev/healthz
   curl -fsS https://truecare-new.noboil.dev/readyz
   ```

## Deploy

P0 deployment is intentionally simple:

```text
Operator or GitHub Actions
  -> SSH to EC2
  -> git fetch/reset in /opt/truecare-new
  -> docker compose up -d --build
  -> public health checks
```

Run:

```bash
make deploy-smoke
```

for the placeholder deploy gate before real application services exist.

## Rollback

Rollback is git-SHA based:

```bash
cd /opt/truecare-new
git fetch origin main
git checkout <previous-good-sha>
docker compose --env-file .env -f infra/compose/compose.staging.yml up -d --build
curl -fsS https://truecare-new.noboil.dev/healthz
curl -fsS https://truecare-new.noboil.dev/readyz
```

Rollback does not roll back database migrations. Migration rollback is restore-or-forward-fix only and must be rehearsed separately.

## Readiness Check

Run:

```bash
make ec2-readiness.check
```

This validates:

- SSH access works.
- Docker and Compose are installed.
- `/opt/truecare-new` exists and is a git checkout.
- `.env` exists on EC2.
- Compose config parses.
- public app traffic health checks pass when `PUBLIC_API_BASE_URL` is set.
