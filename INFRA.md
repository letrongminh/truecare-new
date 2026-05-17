# TrueCare New Infrastructure Plan

This is the single infrastructure source of truth for the TrueCare porting project.

## Summary

The P0 infrastructure is intentionally minimal:

- AWS is used only for one EC2 runtime host.
- Supabase Singapore is used for Postgres, Realtime, and Storage.
- Cloudflare Tunnel is used for public ingress to EC2.
- Docker Compose is the runtime orchestrator.
- Deploy is SSH-based and builds directly on EC2 from this repo.

Do not pull the legacy EKS/k3s/Argo/Helm topology into P0.

## Decisions

| Area | Decision |
| --- | --- |
| AWS services | EC2 only for P0 runtime |
| App runtime | Single EC2 instance running Docker Compose |
| AWS region | `ap-southeast-1` |
| EC2 size | Amazon Linux 2023 ARM64, `t4g.medium`, 30 GB encrypted root volume |
| Public ingress | Cloudflare Tunnel to Caddy on EC2 |
| Admin/deploy access | SSH to EC2, preferably through Cloudflare Access SSH or a fixed operator IP allowlist |
| Database | Supabase Postgres in Singapore |
| Realtime | Supabase Realtime private Broadcast |
| Object storage | Supabase Storage private buckets |
| CI/CD | GitHub Actions static checks; deploy is SSH-based and builds directly on EC2 |
| Repo | `letrongminh/truecare-new` |

Explicitly out of P0:

- ECR
- SSM Session Manager / SSM SendCommand
- SSM Parameter Store
- CloudWatch Logs
- ALB / ACM
- RDS
- S3
- EKS / ECS
- IAM OIDC deploy role for GitHub Actions

EC2 security groups, key pairs, Elastic IP, and the EC2 root volume are considered part of the EC2 baseline, not separate application services.

## Required Accounts And Tools

Required operator accounts:

- AWS account with permission to create and manage one EC2 instance and its security group.
- Cloudflare account for `truecare-new.noboil.dev` or another approved hostname.
- Supabase project in Singapore.
- GitHub repository with Actions enabled.
- Expo account for later EAS Build and EAS Update setup.
- Sentry or compatible DSN for API, worker, mobile, and Ops web.

Required local CLIs:

- `docker`
- `node`
- `pnpm`
- `uv`
- `psql`
- `supabase`
- `jq`
- `curl`
- `git`
- `ssh`

Optional but expected soon:

- `aws` for EC2 provisioning and security group audit.
- `gh` for GitHub repo/admin work.
- `eas` for mobile release setup.

Run:

```bash
make infra-prereqs.check
```

## Environment Contract

All production-like secrets are server-side and stored only in the EC2-local `/opt/truecare-new/.env` file for P0. Do not introduce AWS SSM Parameter Store in P0.

Public client variables that may be embedded in Expo/mobile or browser bundles:

| Name | Required | Purpose |
| --- | --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | Yes | Public API origin, default `https://truecare-new.noboil.dev`. |
| `EXPO_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL for Realtime client setup. |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key; safe only with correct RLS policies. |

No other Supabase key may be public.

Server runtime variables:

| Name | Required | Scope | Purpose |
| --- | --- | --- | --- |
| `PUBLIC_API_BASE_URL` | Yes | API | Public origin used in health/readiness and generated links. |
| `DATABASE_URL_DIRECT` | Yes | API, worker, migration | Direct Supabase Postgres connection for migrations and admin operations. |
| `DATABASE_URL_POOLER` | Yes | API, worker | Supabase pooler connection for request-time SQL. |
| `SUPABASE_URL` | Yes | API, worker | Supabase project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | API, worker only | Server-side Storage/admin calls; never exposed to clients. |
| `SUPABASE_JWT_SECRET` | Yes | API only | Signs short-lived Realtime JWTs compatible with Supabase. |
| `JWT_SIGNING_PRIVATE_JWK` | Yes | API only | Path to access-token signing private JWK on EC2. |
| `JWT_SIGNING_PUBLIC_JWKS` | Yes | API, worker | Path to public JWKS on EC2. |
| `JWT_ISSUER` | Yes | API | Access-token issuer. |
| `JWT_AUDIENCE` | Yes | API | Access-token audience. |
| `SENTRY_DSN` | No | API, worker, web | Error telemetry. |
| `SENTRY_ENVIRONMENT` | Yes | all | `staging` or `production`. |
| `LOG_LEVEL` | Yes | all | Default `info`. |

Operator-side deploy variables:

| Name | Required | Purpose |
| --- | --- | --- |
| `AWS_REGION` | Yes | EC2 region, default `ap-southeast-1`. |
| `EC2_HOST` | Yes | Public DNS/IP or Cloudflare Access SSH hostname. |
| `EC2_SSH_USER` | Yes | Default `ec2-user`. |
| `EC2_SSH_PORT` | Yes | Default `22`. |
| `EC2_SSH_KEY_PATH` | Yes for local SSH | Private SSH key path on operator machine. |
| `EC2_APP_DIR` | Yes | Default `/opt/truecare-new`. |
| `PUBLIC_HOSTNAME` | Yes | Default `truecare-new.noboil.dev`. |
| `CLOUDFLARE_TUNNEL_ID` | Optional | Used for tunnel audit if `cloudflared` CLI is installed. |
| `CLOUDFLARE_TUNNEL_TOKEN` | EC2 only | Runs cloudflared; never in client or logs. |

Secret handling rules:

- Do not commit `.env`, private keys, service role keys, Supabase JWT secret, AWS credentials, Cloudflare tunnel token, or SSH keys.
- Keep EC2 runtime secrets in `/opt/truecare-new/.env` with `0600` permissions.
- Mobile/web bundles may only receive `EXPO_PUBLIC_*` variables listed above.
- `make secret-leak.check` must run before every push.

## Supabase Readiness

Supabase Singapore is the P0 data platform for Postgres, Realtime, and object storage. Do not introduce AWS S3 in P0.

Project requirements:

- Region: Singapore / `ap-southeast-1`.
- Products enabled: Postgres, Realtime, Storage.
- Required database extensions: `postgis`, `pg_trgm`, `pgcrypto`.
- Avoid unless explicitly justified: `timescaledb`, `vector`, `h3`.

Database role assumptions:

- API request path uses a pooler connection.
- Migration/admin path uses direct Postgres connection.
- Server-side elevated tasks use Supabase `service_role` or an approved custom role that bypasses RLS.
- No bypass key or service role credential is exposed to mobile or web clients.

Realtime uses private Broadcast channels with app-issued Supabase-compatible JWTs.

Mandatory channel families:

- `booking:user:{user_id}`
- `booking:merchant:{merchant_id}`
- `merchant:queue:{merchant_id}`
- `reward:user:{user_id}`
- `ops:tenant:{tenant_id}`

Realtime JWT claims must include:

- `sub`
- `role`
- `tenant_id`
- `merchant_ids`
- `ops_scopes`
- `exp`
- `aud`

Realtime gate passes only when allowed joins succeed and wrong-tenant, wrong-merchant, missing-scope, and expired-token joins fail.

Supabase Storage is the only object storage layer in P0.

| Bucket | Privacy | Purpose |
| --- | --- | --- |
| `evidence` | Private | Before/after vehicle evidence and derived metadata. |
| `merchant-qr` | Private | Merchant payment QR assets. |
| `exports` | Private | Short-lived data export bundles. |

Storage gate passes only when server-issued signed upload/download URLs work and unauthorized clients cannot list private buckets.

Run:

```bash
make supabase-readiness.check
```

Required environment:

- `DATABASE_URL_DIRECT`
- `SUPABASE_PROJECT_REF`

Optional environment for deeper checks:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## EC2 Runtime And Deploy

Runtime topology:

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

EC2 provisioning requirements:

- EC2 has Docker Engine, Docker Compose plugin, git, curl, and cloudflared runtime container access.
- EC2 has the repo cloned at `/opt/truecare-new`.
- `/opt/truecare-new/.env` exists and has `0600` permissions.
- Public HTTP traffic enters through Cloudflare Tunnel; EC2 does not expose public `80` or `443`.
- Admin/deploy access is SSH, preferably through Cloudflare Access SSH or a fixed operator IP allowlist.

Bootstrap sequence:

```bash
sudo mkdir -p /opt
sudo git clone https://github.com/letrongminh/truecare-new.git /opt/truecare-new
sudo chown -R ec2-user:ec2-user /opt/truecare-new
cd /opt/truecare-new
docker compose --env-file .env -f infra/compose/compose.staging.yml up -d --build
```

Deploy sequence:

```text
Operator or GitHub Actions
  -> SSH to EC2
  -> git fetch/reset in /opt/truecare-new
  -> docker compose up -d --build
  -> public health checks
```

Run:

```bash
make ec2-readiness.check
make deploy-smoke
```

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

## Readiness Gates

Port implementation can start when these commands pass from an operator machine:

```bash
make infra-prereqs.check
make secret-leak.check
make supabase-readiness.check
make ec2-readiness.check
make deploy-smoke
```

GitHub pull requests run static checks and `make secret-leak.check`.
