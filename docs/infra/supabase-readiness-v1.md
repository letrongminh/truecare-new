# Supabase Readiness v1

Supabase Singapore is the P0 data platform for Postgres, Realtime, and object storage. Do not introduce AWS S3 in P0.

## Project Requirements

- Region: Singapore / `ap-southeast-1`.
- Products enabled:
  - Postgres
  - Realtime
- Storage
- Required database extensions:
  - `postgis`
  - `pg_trgm`
  - `pgcrypto`
- Avoid unless explicitly justified:
  - `timescaledb`
  - `vector`
  - `h3`

## Database Role Assumptions

- API request path uses a pooler connection.
- Migration/admin path uses direct Postgres connection.
- Server-side elevated tasks use Supabase `service_role` or an approved custom role that bypasses RLS.
- No bypass key or service role credential is exposed to mobile or web clients.

## Realtime Requirements

Realtime uses private Broadcast channels with app-issued Supabase-compatible JWTs.

Mandatory channel families:

- `booking:user:{user_id}`
- `booking:merchant:{merchant_id}`
- `merchant:queue:{merchant_id}`
- `reward:user:{user_id}`
- `ops:tenant:{tenant_id}`

JWT claims must include enough authorization context for `realtime.messages` RLS policies:

- `sub`
- `role`
- `tenant_id`
- `merchant_ids`
- `ops_scopes`
- `exp`
- `aud`

The Realtime gate passes only when:

- allowed user joins succeed;
- wrong tenant joins fail;
- wrong merchant joins fail;
- missing scope joins fail;
- expired token joins fail;
- token refresh while subscribed reconnects cleanly.

## Storage Requirements

Private buckets:

- `evidence`
- `merchant-qr`
- `exports`

Storage gate passes only when:

- server can issue a signed upload URL for evidence;
- mobile can upload with that signed URL;
- server can confirm object metadata;
- unauthorized clients cannot list private buckets;
- evidence download URLs are short-lived.
- no application code path requires AWS S3, MinIO, or another object store for P0.

## Readiness Check

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

The script validates extensions, role assumptions, Realtime table availability, and Storage bucket metadata.
