# Environment Contract v1

All production-like secrets are server-side and stored in AWS SSM Parameter Store SecureString under `/truecare-new/staging/*`.

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
| `DATABASE_URL_DIRECT` | Yes | API, worker, migration | Direct Supabase Postgres connection for migrations and admin operations. |
| `DATABASE_URL_POOLER` | Yes | API, worker | Supabase pooler connection for request-time SQL. |
| `SUPABASE_URL` | Yes | API, worker | Supabase project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | API, worker only | Server-side Storage/admin calls; never exposed to clients. |
| `SUPABASE_JWT_SECRET` | Yes | API only | Signs short-lived Realtime JWTs compatible with Supabase. |
| `JWT_SIGNING_PRIVATE_JWK` | Yes | API only | Path to access-token signing private JWK. |
| `JWT_SIGNING_PUBLIC_JWKS` | Yes | API, worker | Path to public JWKS. |
| `JWT_ISSUER` | Yes | API | Access-token issuer. |
| `JWT_AUDIENCE` | Yes | API | Access-token audience. |
| `SENTRY_DSN` | No | API, worker, web | Error telemetry. |
| `SENTRY_ENVIRONMENT` | Yes | all | `staging` or `production`. |
| `LOG_LEVEL` | Yes | all | Default `info`. |

## AWS / Deploy Variables

| Name | Required | Scope | Purpose |
| --- | --- | --- | --- |
| `AWS_REGION` | Yes | CI, operator | Must be `ap-southeast-1` for P0. |
| `AWS_ACCOUNT_ID` | Yes | CI, operator | ECR and IAM account id. |
| `EC2_INSTANCE_ID` | Yes | CI, operator | Target EC2 instance for SSM deploy. |
| `ECR_REGISTRY` | Yes | CI, operator | `<account>.dkr.ecr.ap-southeast-1.amazonaws.com`. |
| `ECR_API_REPOSITORY` | Yes | CI | Default `truecare-new-api`. |
| `ECR_OPS_WEB_REPOSITORY` | Yes | CI | Default `truecare-new-ops-web`. |
| `CLOUDFLARE_TUNNEL_ID` | Yes | operator | Used by readiness checks. |
| `CLOUDFLARE_TUNNEL_TOKEN` | Yes | EC2 only | Runs cloudflared; never in client or logs. |
| `PUBLIC_HOSTNAME` | Yes | all | Default `truecare-new.noboil.dev`. |

## Image Variables

The EC2 Compose runtime consumes immutable image tags:

| Name | Required | Purpose |
| --- | --- | --- |
| `TRUECARE_API_IMAGE` | Yes | API image, tagged by git SHA. |
| `TRUECARE_WORKER_IMAGE` | Yes | Worker image; same image as API with worker command. |
| `TRUECARE_OPS_WEB_IMAGE` | Yes | Ops web image, tagged by git SHA. |

## Secret Handling Rules

- Do not commit `.env`, private keys, service role keys, Supabase JWT secret, AWS credentials, or Cloudflare tunnel token.
- Store runtime secrets in SSM SecureString.
- GitHub Actions uses OIDC role assumption only.
- Mobile/web bundles may only receive `EXPO_PUBLIC_*` variables listed above.
- `make secret-leak.check` must run before every push.
