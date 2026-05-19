# Local E2E Runbook

This runbook verifies the local-only TrueCare port without Supabase credentials or physical-device certification.
See `docs/e2e-verification-prerequisites.md` for the complete local, runner, and production-like prerequisite matrix.

## Scope

- Uses Docker Postgres on `127.0.0.1:55432`.
- Uses a gitignored local JWT key at `.local-jwt-signing-private.jwk.json` so fixture tokens work across `make local.api`, Ops web, and smoke scripts.
- Writes local QA credentials, tokens, and deterministic IDs to `.local-e2e.json`.
- Does not mark Supabase Storage/Realtime, Maestro, Playwright, or physical-device gates complete.

## Bootstrap

```bash
make venv
make local.e2e.prereqs
make infra-prereqs.check secret-leak.check route-test-matrix.check mobile.route-files.check ops.route-files.check
make db.up db.migrate
make api.test api.integration worker.once
make client.generate
pnpm -r typecheck
```

The same local gate set can be run with:

```bash
make local.e2e.gates
```

This aggregate target reseeds `local.qa.fixtures` at the end so `.local-e2e.json` and the local DB are ready for app testing after integration tests run.

## Seed And Smoke

```bash
make local.qa.fixtures
make local.qa.smoke
```

`make local.qa.fixtures` creates these deterministic local users:

| Persona | Identifier | Password |
|---|---|---|
| Consumer | `qa.consumer@truecare.local` | `correct-horse-battery` |
| Merchant owner | `qa.merchant@truecare.local` | `correct-horse-battery` |
| Ops | `qa.ops@truecare.local` | `correct-horse-battery` |

Use `.local-e2e.json` for the current access tokens and IDs while running local QA.
`make local.qa.smoke` verifies auth exists/signup/login/me plus transient bookings, payments, complaints, vouchers, and exports, then restores the deterministic fixture baseline and refreshes `.local-e2e.json` so later tests start clean.

## Run The Apps

Start the API:

```bash
make local.api
```

Start Ops web in another terminal:

```bash
make local.ops
```

Open `http://127.0.0.1:5173`, paste the Ops access token from `.local-e2e.json`, and verify admissions, complaints, commission/export, network fallback, and audit search.

Verify the running API and Ops web:

```bash
make local.app.check
```

Start mobile in another terminal:

```bash
make local.mobile
```

For physical devices, run API with a LAN-reachable host and override `LOCAL_API_BASE_URL`; keep those checks manual until the physical-device gate is explicitly run.

If the Expo/Metro status endpoint is reachable, include it in the local app check:

```bash
LOCAL_MOBILE_STATUS_URL=http://127.0.0.1:8081/status make local.app.check
```

Runner gates stay open until the required tools are installed and the commands pass:

```bash
make local.mobile.maestro
make local.ops.playwright
```

## Manual QA Checklist

- Consumer: signup/login, quick profile, discovery, merchant detail, hold booking, arrived/check-in, evidence, payment, rating, rewards/redeem, profile data export.
- Merchant: onboarding basics, queue, slots/maintenance, booking service transition, daily summary.
- Ops: token guard, admissions actions, complaints resolve/voucher, commission/export, network fallback booking/payment, audit search.
- Offline: stop API, confirm mobile/Ops offline or error states; restart API and retry.
