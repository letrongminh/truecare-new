# Environment Contract v1

All production-like secrets are server-side and stored only in the EC2-local `/opt/truecare-new/.env` file for P0. Do not introduce AWS SSM Parameter Store in P0.

## Public Client Variables

These may be embedded in Expo/mobile or browser bundles.

| Name | Required | Purpose |
| --- | --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | Yes | Public API origin, default `https://truecare-new.noboil.dev`. |
| `EXPO_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL for Realtime client setup. |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key; safe only with correct RLS policies. |

No other Supabase key may be public.

## Server Runtime Variables

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

## EC2 / Deploy Variables

These are operator-side variables used by readiness and deploy scripts. They are not application runtime secrets.

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

## Supabase Storage Buckets

Supabase Storage is the only object storage layer in P0.

| Bucket | Privacy | Purpose |
| --- | --- | --- |
| `evidence` | Private | Before/after vehicle evidence and derived metadata. |
| `merchant-qr` | Private | Merchant payment QR assets. |
| `exports` | Private | Short-lived data export bundles. |

## Secret Handling Rules

- Do not commit `.env`, private keys, service role keys, Supabase JWT secret, AWS credentials, Cloudflare tunnel token, or SSH keys.
- Keep EC2 runtime secrets in `/opt/truecare-new/.env` with `0600` permissions.
- Mobile/web bundles may only receive `EXPO_PUBLIC_*` variables listed above.
- `make secret-leak.check` must run before every push.
