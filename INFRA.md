# TrueCare New Infrastructure Plan

This is the single infrastructure source of truth for the TrueCare porting project.

## Summary

The current phase optimizes for fast codebase porting, not deployment automation.

Minimum infrastructure to start building:

- Local developer machine.
- Supabase Singapore for Postgres, Realtime, and Storage.
- GitHub repo for source control.

No CI/CD flow is required yet. No AWS service is required to start porting. When a public demo is needed, use exactly one AWS service: EC2.

## Current Decisions

| Area | Current decision |
| --- | --- |
| Primary goal | Port backend/mobile/ops code quickly while preserving product correctness |
| AWS usage now | None required for local porting |
| AWS usage later | One EC2 host only, when public demo/deploy is needed |
| Database | Supabase Postgres in Singapore |
| Realtime | Supabase Realtime private Broadcast |
| Object storage | Supabase Storage private buckets |
| CI/CD | Deferred |
| Repo | `letrongminh/truecare-new` |

Explicitly out for now:

- ECR
- SSM Session Manager / SSM SendCommand
- SSM Parameter Store
- CloudWatch Logs
- ALB / ACM
- RDS
- S3
- EKS / ECS
- GitHub Actions deploy flow
- Cloudflare Tunnel setup, until there is an EC2 demo host

The legacy TrueCare repository remains a source reference only. Do not pull the old EKS/k3s/Argo/Helm topology into this port.

## Required Accounts And Tools

Required accounts:

- Supabase project in Singapore.
- GitHub repository.
- Expo account later, when mobile build/release setup begins.

Required local CLIs:

- `node`
- `corepack` for `pnpm`
- `python3` with local `.venv` package installs
- `supabase`
- `curl`
- `git`

Required for Supabase readiness checks:

- `psql`
- `jq`

Optional local tools for later:

- `docker` for local containers and testcontainers.
- `aws` for future EC2 provisioning.
- `ssh` for future EC2 deploy.
- `gh` for GitHub admin work.
- `eas` for mobile release setup.
- `uv` if the team later wants faster Python package installs than venv/pip.

Run:

```bash
make infra-prereqs.check
```

## Environment Contract

Use `.env.example` as the local contract. Real values live in local `.env` files only and must not be committed.

Public client variables that may be embedded in Expo/mobile or browser bundles:

| Name | Required | Purpose |
| --- | --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | Yes | Local API origin, default `http://127.0.0.1:8000`. |
| `EXPO_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL for Realtime client setup. |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key; safe only with correct RLS policies. |

No other Supabase key may be public.

Server runtime variables:

| Name | Required | Scope | Purpose |
| --- | --- | --- | --- |
| `PUBLIC_API_BASE_URL` | Yes | API | Public or local origin used in generated links. |
| `DATABASE_URL_DIRECT` | Yes | API, worker, migration | Direct Supabase Postgres connection for migrations and admin operations. |
| `DATABASE_URL_POOLER` | Yes | API, worker | Supabase pooler connection for request-time SQL. |
| `SUPABASE_URL` | Yes | API, worker | Supabase project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | API, worker only | Server-side Storage/admin calls; never exposed to clients. |
| `SUPABASE_JWT_SECRET` | Yes | API only | Signs short-lived Realtime JWTs compatible with Supabase. |
| `JWT_SIGNING_PRIVATE_JWK` | Yes | API only | Path to access-token signing private JWK. |
| `JWT_SIGNING_PUBLIC_JWKS` | Yes | API, worker | Path to public JWKS. |
| `JWT_ISSUER` | Yes | API | Access-token issuer. |
| `JWT_AUDIENCE` | Yes | API | Access-token audience. |
| `SENTRY_DSN` | No | API, worker, web | Error telemetry; optional during local porting. |
| `SENTRY_ENVIRONMENT` | Yes | all | Default `local`. |
| `LOG_LEVEL` | Yes | all | Default `info`. |

Secret handling rules:

- Do not commit `.env`, private keys, service role keys, Supabase JWT secret, AWS credentials, Cloudflare tunnel token, or SSH keys.
- Mobile/web bundles may only receive `EXPO_PUBLIC_*` variables listed above.
- `make secret-leak.check` must run before every push.

## Supabase Readiness

Supabase Singapore is the only P0 data platform: Postgres, Realtime, and Storage. Do not introduce AWS S3 in this phase.

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

Supabase Storage buckets:

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

## Later EC2 Demo

When the port has enough working code to demo publicly, add a separate EC2 deploy note or script. The later EC2 setup should stay minimal:

- one EC2 instance in `ap-southeast-1`;
- Docker Compose runtime;
- Cloudflare Tunnel for public ingress;
- no ECR, SSM, Parameter Store, CloudWatch, RDS, S3, ALB, ECS, or EKS.

Until then, EC2 is not a prerequisite for implementation.

## Readiness Gates

Port implementation can start when these commands pass locally:

```bash
make infra-prereqs.check
make secret-leak.check
```

Run `make supabase-readiness.check` once Supabase credentials are available and before implementing DB/realtime/storage code paths.
