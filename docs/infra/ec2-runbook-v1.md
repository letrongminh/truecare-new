# EC2 Runbook v1

This runbook describes the P0 EC2 Docker Compose runtime.

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

api container
worker container
ops-web container

Supabase Singapore
  |-- Postgres
  |-- Realtime
  \-- Storage
```

## Provisioning Requirements

- EC2 has no inbound security group rules.
- EC2 has outbound internet access.
- EC2 instance profile includes SSM and ECR pull permissions.
- Docker Engine and Docker Compose plugin are installed.
- `/opt/truecare-new/compose.staging.yml` exists.
- `/opt/truecare-new/Caddyfile` exists.
- `/opt/truecare-new/.env` is generated from SSM parameters during bootstrap.

## Bootstrap Sequence

1. Create ECR repositories:
   - `truecare-new-api`
   - `truecare-new-ops-web`
2. Create EC2 in `ap-southeast-1`.
3. Install Docker and Compose plugin.
4. Copy `infra/compose/compose.staging.yml` and `infra/caddy/Caddyfile` to `/opt/truecare-new`.
5. Pull SSM parameters into `/opt/truecare-new/.env`.
6. Start Compose:
   ```bash
   docker compose --env-file .env -f compose.staging.yml up -d
   ```
7. Confirm:
   ```bash
   docker compose -f compose.staging.yml ps
   curl -fsS https://truecare-new.noboil.dev/healthz
   curl -fsS https://truecare-new.noboil.dev/readyz
   ```

## Deploy

The CI deploy path is:

```text
GitHub Actions OIDC
  -> AWS STS role
  -> ECR push immutable git SHA images
  -> SSM SendCommand
  -> EC2 docker compose pull
  -> EC2 docker compose up -d
```

Use:

```bash
make deploy-smoke
```

for the placeholder deploy gate before real application images exist.

## Rollback

Rollback is image-tag based:

1. Set `TRUECARE_API_IMAGE`, `TRUECARE_WORKER_IMAGE`, and `TRUECARE_OPS_WEB_IMAGE` to the previous known-good git SHA tags.
2. Run:
   ```bash
   docker compose --env-file .env -f compose.staging.yml pull
   docker compose --env-file .env -f compose.staging.yml up -d
   ```
3. Verify `/healthz` and `/readyz`.

Rollback does not roll back database migrations. Migration rollback is restore-or-forward-fix only and must be rehearsed separately.

## Readiness Check

Run:

```bash
make ec2-readiness.check
```

This validates:

- EC2 instance exists.
- SSM PingStatus is `Online`.
- EC2 security groups have no inbound rules.
- ECR repositories are reachable.
- Cloudflare tunnel information is available when `cloudflared` is installed.
