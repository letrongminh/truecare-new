# E2E Verification Prerequisites

This checklist separates local functional verification from production-like end-to-end closure.

## Local Required Prerequisites

- Repo: `/Users/minhlt/Downloads/Projects/TrueCare/truecare-new`.
- Branch: `main`.
- Required CLIs: `git`, `make`, `curl`, `python3`, `node`, `corepack`, `pnpm`, and `docker`.
- Node must be an active even-numbered release `>=22`.
- Docker must be running and able to start the local Postgres container on `127.0.0.1:55432`.
- No real `.env` is required for local-only verification.

Verify the machine state:

```bash
make local.e2e.prereqs
```

## Local QA Fixtures

Local fixture commands create:

- `.local-jwt-signing-private.jwk.json`: stable local JWT signing key.
- `.local-e2e.json`: seeded QA credentials, access tokens, and deterministic IDs.

Seeded personas:

| Persona | Identifier | Password |
|---|---|---|
| Consumer | `qa.consumer@truecare.local` | `correct-horse-battery` |
| Merchant owner | `qa.merchant@truecare.local` | `correct-horse-battery` |
| Ops | `qa.ops@truecare.local` | `correct-horse-battery` |

Refresh fixtures and run the local API smoke:

```bash
make local.qa.fixtures
make local.qa.smoke
```

`make local.qa.smoke` verifies auth, discovery, booking, evidence, payment recovery, rating, rewards, referral, complaint, merchant queue/service transition, and Ops fallback/export/audit routes. It restores the deterministic fixture baseline after the smoke run.

## Local App Verification

Start API:

```bash
make local.api
```

Start Ops web in another terminal:

```bash
make local.ops
```

Then verify the running app endpoints:

```bash
make local.app.check
```

Optional Expo/Metro status check:

```bash
LOCAL_MOBILE_STATUS_URL=http://127.0.0.1:8081/status make local.app.check
```

Start mobile separately:

```bash
make local.mobile
```

For a physical device, expose the API on the LAN:

```bash
LOCAL_API_HOST=0.0.0.0 LOCAL_API_BASE_URL=http://<LAN-IP>:8000 make local.api
LOCAL_API_BASE_URL=http://<LAN-IP>:8000 make local.mobile
```

## Runner Prerequisites

These are not required for local API smoke, but they are required before marking runner E2E complete:

- Maestro CLI plus an available iOS Simulator, Android Emulator, or physical device.
- Project-local `@playwright/test` plus Playwright browser binaries.
- Ops web running at `LOCAL_OPS_URL`, default `http://127.0.0.1:5173`.

Runner commands:

```bash
make local.mobile.maestro
make local.ops.playwright
```

The current runner files are smoke-level checks. Do not mark full Maestro or Playwright journeys done until the runner flows cover real consumer, merchant, and Ops mutations and pass locally.

## Supabase And Production-Like Prerequisites

Production-like closure requires real `.env` values copied from `.env.example`:

- `SUPABASE_PROJECT_REF`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL_DIRECT`
- `DATABASE_URL_POOLER`
- public Supabase URL and anon key for mobile

After real credentials are available:

```bash
make supabase-readiness.check
```

Only mark Supabase readiness complete after Storage policies, signed upload confirmation, Realtime private Broadcast policies, token refresh, polling fallback, and negative authorization checks pass against the real Supabase project.

## Final E2E Exit Criteria

- Local gates pass through `make local.e2e.gates`.
- `make local.app.check` passes against running API and Ops web.
- Manual consumer, merchant, and Ops P0 checklist passes without database intervention.
- Maestro mobile journey passes on simulator/emulator or device.
- Playwright Ops journey passes against local API/Ops.
- Supabase readiness passes with real credentials.
- Physical-device checks pass for camera, QR, GPS, push receipt, deep links, maps resume, and offline replay.
- Production readiness gates pass: OpenAPI freeze, role/tenant audit, idempotency matrix, worker advisory-lock/catch-up rehearsal, backup/restore, staging soak, load/security smoke, observability, and rollback runbook.
