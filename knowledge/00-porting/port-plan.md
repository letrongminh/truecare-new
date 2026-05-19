# TrueCare Port Plan: Python Backend + Expo/React Frontend

Canonical plan generated on 2026-05-17.

This file supersedes:
- `docs/port-plan-python-expo.md`
- `docs/port-plan-production-ready.md`
- `docs/port-plan-review.md`
- `docs/port-plan-gap-analysis.md`

Source inputs:
- PRD: `/Users/minhlt/Downloads/Projects/TASCO/09-product-requirements-document.md`
- Current codebase: `/Users/minhlt/Downloads/Projects/TrueCare/truecare`
- Current stack: Kotlin/Ktor backend, SwiftUI iOS app, Postgres, RLS, workers, generated wire contracts, NATS/Kafka/Temporal paths
- Gap supplement: `docs/port-plan-gap-analysis.md`

## 1. Executive Decision

Port as a new functional-parity product, not as a line-by-line rewrite.

Target stack:
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Postgres/PostGIS.
- Mobile app: Expo React Native, Expo Router, TypeScript, TanStack Query, Tamagui.
- Ops web: Vite React, TanStack Router, TanStack Query, shadcn/Radix-style primitives.
- Realtime: Supabase Realtime private Broadcast from database events, with polling fallback.
- Storage: Supabase Storage or S3-compatible object storage, MinIO only for local development.
- Jobs: one Python worker process from the same image, using Postgres advisory locks and `FOR UPDATE SKIP LOCKED`.
- API contract: OpenAPI v1 generated from FastAPI/Pydantic, then TypeScript clients generated for mobile and Ops web.

Infrastructure removed from the P0/P1 production path:
- Kafka
- NATS
- Temporal
- Apicurio
- custom KSP codegen
- jOOQ codegen
- KMP/Swift generated wire package
- Kubernetes, Helm, ArgoCD for early deploy
- TimescaleDB, pgvector, h3 unless later route intelligence or analytics proves the need

Keep Postgres and PostGIS. They are product complexity, not accidental infrastructure.

### 1.1 End-to-End Completion Contract

This plan is an execution contract for a pilot-ready P0 product, not only a migration inventory. Production is not complete until all P0 PRD journeys are implemented end-to-end across backend, mobile, Ops web, worker, realtime/storage, migration, observability, and rollback.

P0 completion requires:
- Every P0 `/v1` route in this plan has a real handler, registered errors, OpenAPI schema, generated TypeScript client coverage, authorization checks, and unit or integration tests. No P0 route may return a generic unimplemented placeholder.
- Every P0 mobile and Ops route listed in the PRD route matrix is wired to generated-client data or a local offline queue, exposes loading/empty/error/offline/forbidden states, and is covered by route-file checks plus at least one screen or E2E test lane before cutover.
- Consumer, merchant, and ops journeys can complete without manual database intervention: signup or invite entry, discovery, booking, check-in, evidence, payment, rating, reward/referral, complaint, merchant onboarding, admissions, exports, and support fallbacks.
- Worker behavior is durable and replay-safe: scheduled jobs have a ledger, domain event consumers are idempotent, retries are bounded, dead letters are visible to ops, and crash/redeploy catch-up is tested.
- Supabase Realtime and Storage are production-configured, not mocked: private Broadcast policies, storage bucket policies, short-lived app-issued realtime JWTs, upload confirmation, and polling fallback are all verified.
- Migration and cutover are rehearsed: migration dry-run, seed verification, shadow-read comparison, backup restore, 48h staging soak, synthetic bookings, load/security smoke, release dashboards, and rollback runbook all pass.
- Feature flags are used only for rollout, API-origin switching, and rollback. They cannot hide incomplete P0 PRD journeys at production completion.

The required sources of truth must stay synchronized:
- OpenAPI spec and generated TypeScript client.
- `knowledge/00-porting/route-test-matrix-v1.md` and actual mobile/Ops route files.
- Alembic schema, seed manifest, migration map, and shadow-read harness.
- Maestro mobile flows, Playwright Ops flows, API integration tests, and readiness checklist below.

## 2. Verified Current Surface

Verified local facts on 2026-05-17:
- `apps/truecare/ios/App`: 223 Swift files, 40,801 lines.
- `tools/maestro/flows`: 105 Maestro flow files.
- `generated/migrations/V001__init.sql`: 37 tables, 28 RLS-enabled tables.
- Broad test/spec file scan: 94 files.

Critical source files to preserve behavior from:
- `apps/foundation/api/src/main/kotlin/app/map/api/booking/PostgresBookingService.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/payment/PostgresPaymentService.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/auth/PostgresAuthStores.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/merchant/PostgresMerchantDiscoveryService.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/reward/PostgresRewardService.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/promo/PostgresPromoService.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/evidence/EvidenceService.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/MeRoutes.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/RlsContext.kt`
- `apps/foundation/api/src/main/kotlin/app/map/api/RlsTransaction.kt`
- `generated/migrations/V001__init.sql`

## 3. Scope Rules

Production cutover requires full persona parity with the PRD.

Do not permanently cut:
- Reward Center, Redeem, Celebration.
- Referral tracking and sharing.
- Complaint workflow.
- Ops admissions, complaint/refund review, commission export, data room, fallback actions, growth/eKYC review.

Sequencing is allowed:
- Core marketplace can be built first.
- Reward/referral/complaint can be implemented after the core loop.
- Production completion is not declared until all PRD personas and journeys are covered.

Feature flags are for rollout and rollback, not for hiding permanent parity gaps.

### 3.1 Effort/Value Execution Strategy

Production-ready means stable, observable, and recoverable; it does not mean rebuilding every advanced subsystem from the old stack. Use the thinnest implementation that preserves the user journey, data integrity, and operational control.

Non-negotiable for production:
- Auth, refresh rotation, RBAC, tenant scope, and rate limits.
- Booking, payment, evidence, reward, merchant admission, and commission state machines.
- Atomic booking holds and payment idempotency.
- Merchant queue, consumer active booking, and ops admissions/complaints/exports.
- Migration dry-run, shadow-read checks, backup restore rehearsal.
- Observability, worker catch-up, force update, feature flags, and rollback path.

P0 effort minimizers that preserve value:
- Search is merchant-only using PostGIS + pg_trgm; POI/place search returns empty until P1.
- Password reset creates an ops support request; no email/SMS OTP flow in P0.
- Referral attribution uses `invite_codes.referred_by`; no separate `referral_sources` table in P0.
- Rating is binary positive/negative with optional comment; no star rating in P0.
- Daily summary and data room are SQL-backed aggregates/CSV, not a BI warehouse.
- Golden Hour uses a small `golden_hours` table, not a promotion rules engine.
- Notification preferences are one row per user, not a marketing automation system.
- Feature flags are static defaults plus per-user overrides, not a full experimentation platform.
- PgBouncer + managed services replace Kubernetes-scale orchestration.

P1 candidates after stable cutover:
- Meilisearch or Typesense if merchant search quality is insufficient.
- POI/place search and in-app map view.
- Automated password reset via email/SMS OTP.
- Dedicated referral attribution table and richer campaign analytics.
- Star ratings and richer review taxonomy.
- Native App Attest parity.

Gate:
- Every P0 simplification has an explicit P1 upgrade path.
- No P0 simplification weakens booking/payment correctness, tenant isolation, auditability, or rollback.

## 4. Production Mismatch Fixes

| ID | Issue in earlier plan | Canonical correction | Cutover gate |
|---|---|---|---|
| MM-01 | No complete screen-to-route mapping | Add mandatory PRD route manifest with complexity, API dependencies, UX states, and tests | Every PRD screen maps to route, API, test IDs, and E2E coverage |
| MM-02 | Native mobile details too thin | Specify Expo packages, permissions, config plugins, fallbacks, and physical-device tests | Camera, QR, GPS denied, SecureStore, push, offline queue pass on iOS/Android |
| MM-03 | UI library undecided | Use Tamagui for mobile, shadcn/Radix-style primitives for Ops web, shared tokens only | Mobile shell has approved primitives and responsive Vietnamese text |
| MM-04 | Migration too vague | Add table-by-table mapping, RLS policy mapping, seeds, checksums, shadow-read harness | Migration dry-run, checksums, and restore rehearsal pass |
| MM-05 | Auth/security too shallow | Implement refresh token families, theft detection, RBAC, rate limits, tenant context, DB RLS | Security suite proves no route or tenant bypass |
| MM-06 | Test strategy incomplete | Use pytest/testcontainers/Hypothesis/Schemathesis, Maestro, Playwright, parity harness | CI blocks merge/release on required lanes |
| MM-07 | Booking concurrency under-specified | Use atomic Postgres updates, idempotency keys, advisory locks, deadlock retry | 10/50/100 concurrent hold tests show no double-hold |
| MM-08 | Performance verification absent | Add k6/Locust probes, PostGIS explain snapshots, mobile device measurements | PRD p95 and mobile targets met on staging-like data |
| MM-09 | Realtime authorization incomplete | Use private Supabase Broadcast channels and RLS on `realtime.messages` | Unauthorized channel joins fail |
| MM-10 | API parity small gaps | Add price history and daily summary CSV endpoints | Contract includes and tests these endpoints |
| MM-11 | Observability vague | Specify Sentry, structlog, metrics, request IDs, alerts, runbooks | Launch dashboards and alerts ready |
| MM-12 | Review suggested scope cuts | Reject final-scope cuts; only phase work order | Full persona parity required before completion |
| MM-13 | Domain state-machine gaps | Add reward, merchant admission, commission receivable, no-show, and rated states | State-machine integration tests prove all PRD terminal states and guards |
| MM-14 | Operational controls missing | Add force-update, feature flags, global rate limits, PgBouncer/dual-pool, health/readiness/metrics | Launch build can be killed, forced to update, pooled safely, and monitored |
| MM-15 | Quality parity gaps | Add search, service tags, stale merchant, evidence timeout, no-show/deposit, account deletion, backend i18n | Production checklist covers every new gate before cutover |

## 5. Target Architecture

```text
Expo Mobile App
  |-- consumer persona
  |-- merchant persona
  |-- Expo Router routes
  |-- Tamagui UI primitives
  |-- SecureStore token storage
  |-- TanStack Query cache and mutation queues
  |-- FileSystem evidence queue
  |-- Supabase private realtime channels
  |-- generated API client
  \-- Maestro test IDs

Ops Web App
  |-- admissions
  |-- payment recipient verification
  |-- complaints/refunds/vouchers
  |-- commission/data exports
  |-- network health/fallback actions
  |-- generated API client
  \-- Playwright coverage

FastAPI Monolith
  |-- routers: auth, me, merchants, bookings, payments, evidence, promos, rewards, referrals, complaints, ops
  |-- services: domain state machines, idempotency, authorization, pricing, rewards
  |-- repositories: SQLAlchemy transactions and Postgres queries
  |-- middleware: request ID, auth, rate limit, tenant context, CORS
  |-- OpenAPI v1 contract
  \-- metrics/health/readiness

Worker Process
  |-- scheduled jobs with Postgres advisory locks
  |-- domain_events processing with SKIP LOCKED
  |-- stale hold expiry
  |-- evidence thumbnail/watermark/hash
  |-- push notifications
  |-- complaint SLA escalation
  |-- merchant summaries/exports
  |-- data export/delete jobs
  \-- retries and dead-letter handling

Postgres/PostGIS
  |-- Alembic migrations
  |-- RLS for production tenant tables
  |-- domain_events
  |-- audit_log/failure_log
  |-- PostGIS merchant search indexes
  \-- restore-tested backups

Supabase
  |-- Realtime private Broadcast
  |-- Storage or S3-compatible bucket
  \-- optional managed services only if explicitly selected later
```

Module boundaries:
- Routers validate requests, enforce auth dependencies, and shape responses only.
- Services own state transitions, idempotency, and domain decisions.
- Repositories own SQL and transaction mechanics.
- Background jobs call services where possible, not raw business logic duplicates.
- Mobile owns consumer and merchant phone workflows.
- Ops web owns deskside workflows. Do not force ops into mobile.
- `app/domain/` is the canonical source for every domain enum, terminal state, transition graph, and transition guard.
- Pydantic schemas, SQLAlchemy model enums/check constraints, Alembic migrations, OpenAPI values, workers, and generated clients derive from or test against `app/domain/`; never duplicate status strings by hand.

## 6. Backend Package Shape

```text
apps/api/
  app/main.py
  app/core/config.py
  app/core/security.py
  app/core/rate_limit.py
  app/core/errors.py
  app/core/logging.py
  app/db/base.py
  app/db/session.py
  app/db/rls.py
  app/domain/
    states.py
    booking_state_machine.py
    payment_state_machine.py
    evidence_state_machine.py
    reward_state_machine.py
    merchant_admission_state_machine.py
    commission_state_machine.py
  app/models/
  app/schemas/
  app/routers/
    auth.py
    me.py
    merchants.py
    merchant_services.py
    bookings.py
    payments.py
    evidence.py
    promos.py
    rewards.py
    referrals.py
    complaints.py
    ops.py
    realtime.py
  app/services/
    auth_service.py
    booking_service.py
    payment_service.py
    merchant_service.py
    evidence_service.py
    promo_service.py
    reward_service.py
    referral_service.py
    complaint_service.py
    ops_service.py
    idempotency_service.py
    realtime_service.py
  app/repositories/
  app/jobs/
    worker.py
    scheduled.py
    evidence_processor.py
    event_dispatcher.py
  app/observability/
  tests/
  alembic/
```

## 7. Data Model Plan

Keep and port:
- tenants
- users
- tenant_memberships
- profiles
- refresh_tokens
- invite_codes
- vehicles
- merchants
- merchant_services
- service_templates
- slot_capacity
- bookings
- payments
- evidence
- ratings
- promo_codes
- promo_code_usages
- reward_stamps
- reward_vouchers
- referrals
- complaints
- audit_log
- failure_log
- worker_jobs
- worker_runs
- domain_events
- processed_domain_events
- price_change_log
- device_tokens
- support_requests
- golden_hours
- notification_preferences
- location_history
- merchant_pipeline_log
- deletion_receipts

Required field additions and enums:
- `merchants.phone` nullable string, E.164 or local format, required for C3 call button when available.
- `invite_codes.referred_by` nullable user/merchant reference for P0 first-touch referral attribution.
- `notification_preferences` stores `booking_updates`, `golden_hour`, `referral_reward`, `wash_reminder`, `quiet_hours_start`, and `quiet_hours_end`.
- `golden_hours` stores `(merchant_id, day_of_week, start_time, end_time, discount_percent)`; discount cannot reduce price below 70% of listed base price.
- `support_requests` stores P0 manual password reset and user-support requests with owner, status, and audit fields.
- `users.vetc_id` nullable and `users.auth_provider` enum (`local`, `vetc`) for disabled VETC placeholder behavior.
- `bookings.no_show_count_snapshot`, `bookings.deposit_amount`, and booking terminal state `rated`.
- `payments.commission_status`, `payments.invoice_id`, `payments.settled_at`, `payments.waived_reason`, `payments.dispute_status`.
- `promo_codes.platform_funded` boolean, default true for P0.
- `service_templates.sop_checklist_url` and `service_templates.evidence_required` enum.
- `merchants.stale` boolean, default false.
- `worker_jobs` stores durable scheduler metadata: job name, schedule kind, enabled flag, next_run_at, last_success_at, max_lag_seconds, and catch_up_from cursor.
- `worker_runs` stores every scheduled execution: job name, owner_id, attempt, status, started_at, finished_at, lease_expires_at, high_watermark, rows_processed, and error context.
- `domain_events` is the canonical Postgres outbox: event_id, tenant_id, aggregate_type, aggregate_id, aggregate_version, event_type, payload, schema_version, trace_id, idempotency_key, available_at, locked_by, locked_until, attempts, processed_at, and dead_letter_reason.
- `processed_domain_events` is the inbox/idempotency ledger keyed by `(consumer_name, event_id)` with processed_at, result_hash, and error context.
- Merchant service mode tags: `fast_lane`, `premium_care`, `drive_thru`, `night_owl`, max 3 per merchant.
- Evidence quality values: `valid`, `weak_evidence`, `expired`, plus transient `missing_before` and `missing_after`.

Service template evidence requirement enum:
- `before_after_exterior`
- `before_after_interior`
- `interior_after`
- `after_only`
- `before_after_lower_body`

Replace or collapse:
- outbox -> `domain_events`
- processed_events -> `processed_domain_events`
- entity_translations -> app i18n files unless DB-driven copy is required

Archive or defer unless current screens depend on them:
- admission_scores
- app_attest_keys
- budget_items
- channel_sources
- feedback_log

Required Alembic baseline:
```text
0001_core_tenants_users_auth
0002_merchants_services_slots
0003_bookings_payments_evidence
0004_promos_rewards_referrals
0005_ops_complaints_privacy
0006_realtime_events_audit_observability
```

Production rollback stance:
- Alembic downgrades are only for local/dev when safe.
- Production rollback is restore-from-backup plus forward fix, rehearsed before launch.

## 8. API Contract

Product endpoints use `/v1`. Operational health and metrics endpoints are unversioned root endpoints.


Platform and control:
- `GET /v1/app/version-check`
- `GET /v1/flags`
- `GET /healthz`
- `GET /readyz`
- `GET /metrics`

Search and templates:
- `GET /v1/search?q=&lat=&lng=&type=merchant|place`
- `GET /v1/service-templates`

Auth and session:
- `POST /v1/auth/exists`
- `POST /v1/auth/signup`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `POST /v1/auth/logout-all`
- `GET /v1/auth/me`
- `POST /v1/auth/forgot-password`

Forgot-password P0 behavior:
- `POST /v1/auth/forgot-password` accepts `{ "identifier": "email_or_phone" }`.
- P0 creates a `support_requests` row for ops manual reset.
- No email/SMS OTP flow in P0.
- Ops resets password through `POST /v1/ops/users/{id}/reset-password`.

Me/profile/privacy:
- `GET /v1/me/profile`
- `PATCH /v1/me/profile`
- `GET /v1/me/vehicles`
- `POST /v1/me/vehicles`
- `PATCH /v1/me/vehicles/{id}`
- `GET /v1/me/bookings`
- `POST /v1/me/data-export`
- `GET /v1/me/data-export/{job_id}`
- `DELETE /v1/me/account`
- `POST /v1/me/notifications/register`
- `GET /v1/me/notifications/preferences`
- `PATCH /v1/me/notifications/preferences`
- `POST /v1/me/password`
- `GET /v1/me/sessions`
- `DELETE /v1/me/sessions/{id}`
- `POST /v1/me/cancel-delete`

Consumer marketplace:
- `GET /v1/merchants/nearby`
- `GET /v1/merchants/{id}`
- `GET /v1/merchants/{id}/services`
- `GET /v1/merchants/{id}/bays`
- `POST /v1/bookings/holds`
- `GET /v1/bookings`
- `GET /v1/bookings/{id}`
- `POST /v1/bookings/{id}/cancel`
- `POST /v1/bookings/{id}/arrived`
- `POST /v1/bookings/{id}/rate`


Rating request body for `POST /v1/bookings/{id}/rate`:
```json
{
  "rating": "positive | negative",
  "comment": "string, optional, max 500 chars"
}
```
Rules:
- Binary rating only: `positive` or `negative`. No star rating in P0.
- Comment is optional.
- User may submit rating after tapping payment claimed or choosing cash, even before merchant confirms payment.
- Reward stamp remains pending until booking reaches `completed`.
- Duplicate rating returns the existing rating idempotently.

Payments:
- `POST /v1/payments/initiate`
- `GET /v1/payments/{id}`
- `POST /v1/payments/{id}/user-claimed`
- `POST /v1/payments/{id}/merchant-confirmed`
- `POST /v1/payments/{id}/merchant-denied`
- `POST /v1/payments/{id}/cash-record`
- `POST /v1/payments/{id}/switch-method`


Payment denial body for `POST /v1/payments/{id}/merchant-denied`:
- `reason`: optional enum `not_received`, `wrong_amount`, `other`.
- Transition: `user_claimed -> merchant_denied`.
- User is notified to retry QR transfer or switch to cash.

Evidence:
- `POST /v1/evidence/{booking_id}/presign`
- `POST /v1/evidence/{evidence_id}/confirm`
- `GET /v1/evidence/{booking_id}`

Promo/reward/referral:
- `POST /v1/promo-codes/validate`
- `GET /v1/promo-codes/user`
- `GET /v1/rewards/progress`
- `GET /v1/rewards/vouchers`
- `POST /v1/rewards/vouchers/{id}/reserve`
- `POST /v1/rewards/vouchers/{id}/release`
- `POST /v1/rewards/vouchers/{id}/redeem`
- `GET /v1/referrals/me`
- `POST /v1/referrals/share-event`

Referral reward rules:
- M2M referral: referrer receives 1 month commission-free status; referee receives 30-day free trial.
- C2C referral: referrer and referee each receive a 20,000 VND promo code for next booking.
- P0 attribution is first-touch through `invite_codes.referred_by`.
- `referral_sources` is deferred to P1.

Complaints:
- `POST /v1/complaints`
- `GET /v1/complaints/{id}`

Merchant:
- `POST /v1/merchants/applications`
- `POST /v1/merchants/{id}/confirm-photo`
- `POST /v1/merchants/{id}/payment-setup`
- `GET /v1/merchants/{id}/queue`
- `GET /v1/merchants/{id}/calendar`
- `POST /v1/merchants/{id}/calendar/maintenance`
- `GET /v1/merchants/{id}/golden-hour`
- `PUT /v1/merchants/{id}/golden-hour`
- `GET /v1/merchants/{id}/daily-summary`
- `GET /v1/merchants/{id}/daily-summary.csv`

Daily summary response includes:
- `services_completed`: integer.
- `total_revenue`: integer VND.
- `qr_revenue`: integer VND.
- `cash_revenue`: integer VND.
- `promo_discount_total`: integer VND.
- `average_rating`: float.
- `complaint_count`: integer.
- `payout_status`: `pending` or `processed`.
- `bookings`: array of `{ time, customer_name, service_name, amount, method, promo_code, status }`.
- CSV export includes the same summary plus per-booking rows.

- `POST /v1/bookings/{id}/check-in`
- `POST /v1/bookings/{id}/start-service`
- `POST /v1/bookings/{id}/complete-service`
- `POST /v1/merchant-services`
- `PATCH /v1/merchant-services/{id}`
- `GET /v1/merchant-services/{id}/price-history`
- `POST /v1/merchant-services/custom`
- `POST /v1/merchant-services/{id}/resubmit`
- `POST /v1/merchants/{id}/ekyc/cmnd`
- `POST /v1/merchants/{id}/ekyc/selfie`
- `POST /v1/merchants/{id}/ekyc/bank`
- `GET /v1/merchants/{id}/ekyc/status`

Ops:
- `GET /v1/ops/merchants/pending`
- `POST /v1/ops/merchants/{id}/approve`
- `POST /v1/ops/merchants/{id}/reject`
- `POST /v1/ops/merchants/{id}/verify-payment-recipient`
- `POST /v1/ops/merchants/{id}/suspend`
- `POST /v1/ops/promo-codes`
- `POST /v1/ops/merchant-services/{id}/approve`
- `POST /v1/ops/merchant-services/{id}/reject`
- `GET /v1/ops/commission-receivables`
- `GET /v1/ops/data-room/{section}`
- `POST /v1/ops/exports`
- `GET /v1/ops/exports/{job_id}`
- `GET /v1/ops/complaints`
- `PATCH /v1/ops/complaints/{id}`
- `POST /v1/ops/bookings`
- `POST /v1/ops/bookings/{id}/check-in`
- `POST /v1/ops/evidence/upload`
- `POST /v1/ops/payments/{id}/confirm`
- `GET /v1/ops/users`
- `POST /v1/ops/users`
- `POST /v1/ops/users/{id}/reset-password`
- `POST /v1/ops/reward/voucher`
- `GET /v1/ops/audit-log`


Ops users list:
- `GET /v1/ops/users` query params: `role`, `scope`, `page`, `limit`.
- Returns paginated ops users with role and scope.
- Required for OPS-5 and admin user management.


Ops data room P0 sections for `GET /v1/ops/data-room/{section}`:
- `merchant_pipeline`: admission scores, pipeline stages, go-live status.
- `commission`: commission receivables and settlement status.
- `complaints`: SLA status, categories, resolution times.
- `bookings`: aggregate booking stats by status and time period.
- `rewards`: stamp counts, voucher status, campaign budget utilization.

Commission export fields:
- `merchant_id`, `period_start`, `period_end`, `total_bookings`, `total_revenue`, `commission_receivable`, `commission_status`, `invoice_id`, `waived_reason`, `settled_at`, `dispute_status`.
- Weekly cadence: every Monday for the previous week.

Realtime:
- `POST /v1/realtime/token` returns a short-lived FastAPI-issued Supabase-compatible JWT for private Broadcast subscriptions.
- Realtime JWT issuer remains the FastAPI auth service; Supabase Realtime only verifies the token and `realtime.messages` policies.
- Token TTL is 5 minutes. Mobile/web refresh before expiry while subscribed.
- Token claims include `sub`, `tenant_id`, `roles`, `merchant_ids`, `ops_scopes`, `exp`, `iat`, and `aud='authenticated'`.
- Broadcast payloads use IDs and state only; clients refetch full records through FastAPI.

Contract gates:
- OpenAPI spec contains every route and schema.
- Generated clients compile in mobile and Ops web.
- Schemathesis smoke passes locally and in CI.
- Error envelope is stable across all routers.
- `app/core/errors.py` defines every API error code with HTTP status, RFC 9457 `type` URI, localization key, retryability, and recommended client action.
- CI generates an API error catalog from `app/core/errors.py` and fails if routers/services raise unregistered errors.

## 9. Domain State Machines

Booking states:
```text
held
  -> checked_in
  -> in_progress
  -> awaiting_payment
  -> completed
  -> rated

held -> expired
held -> no_show
held -> cancelled
checked_in/in_progress/awaiting_payment -> payment_disputed
checked_in/in_progress -> cancelled_by_ops
```

Booking transition guards:
- `checked_in -> in_progress` requires before-photo captured/uploaded.
- `in_progress -> awaiting_payment` requires after-photo captured/uploaded and merchant tapped complete service.
- `awaiting_payment -> completed` requires payment verified by merchant or cash recorded by merchant.
- `completed -> rated` occurs when the user submits rating after payment verification.
- `no_show` is used when a held booking is not checked in before expiry and triggers no-show policy logic.

Payment states:
```text
pending
  -> initiated_qr
  -> user_claimed
  -> verified

pending -> cash_offered -> verified
initiated_qr/user_claimed/cash_offered -> disputed
user_claimed -> merchant_denied
merchant_denied -> cash_offered via switch_method
merchant_denied -> disputed
initiated_qr/user_claimed -> cash_offered via switch_method
cash_offered -> initiated_qr via switch_method
any non-terminal -> cancelled
```

Payment rules:
- Merchant cash recording is an event that verifies payment; it is not a standalone terminal booking state.
- Switching payment method is idempotent and records previous method in payment events.
- Commission status is tracked separately from payment status.
- Payment transition matrix tests must cover QR, cash, user-claimed, merchant-confirmed, merchant-denied, switch-method, disputed, cancelled, replay, and invalid transitions.
- Merchant-denied flows must prove rewards stay pending, booking does not complete, user can retry QR or switch to cash, and ops has enough event/audit context to resolve disputes.

Evidence states:
```text
required
  -> presigned
  -> uploaded
  -> processed
  -> approved

uploaded/processed -> weak_evidence
presigned -> expired
required -> missing_before / missing_after -> evidence_pending
```

Evidence quality classification:
- `valid`: meets all requirements.
- `weak_evidence`: below quality threshold but still usable, such as low resolution, poor lighting, or suspected reuse.
- `expired`: presigned URL expired before upload.
- `missing_before` and `missing_after`: transient statuses before worker classification.

Minimum photo requirements:
- Resolution: minimum 1280x720.
- File size: maximum 500KB after compression.
- Format: JPEG.
- Watermark: booking ID overlay added by worker.
- EXIF: stripped by client before upload; timestamp and geotag added server-side.

Reward state machine:
```text
no_progress
  -> stamp_1
  -> stamp_2
  -> stamp_3
  -> stamp_4
  -> stamp_5_reached
  -> voucher_issued
  -> voucher_reserved
  -> voucher_redeemed

voucher_reserved -> voucher_released
voucher_issued/reserved -> expired
voucher_issued/reserved/redeemed -> frozen -> restored / invalidated
```

Reward rules:
- When user submits rating while booking is still `awaiting_payment`, show reward progress as `stamp_pending` on C7 and Profile.
- When booking reaches `completed`, finalize the stamp automatically and update finalized progress count.
- C12 Celebration appears only when the threshold is reached and finalized, not while pending.
- A stamp is created only when booking reaches `completed` and user confirmation/rating conditions are satisfied.
- Duplicate stamps are prevented by idempotency on `(booking_id, user_id)`.
- If payment is disputed after stamp issuance, freeze related reward progress or voucher until ops resolution.
- If voucher is applied to a booking that expires or is cancelled before check-in, release voucher back to available.
- If voucher expires before use, mark expired and keep historical progress visible in Profile.
- If reward campaign budget cap is reached, pause new voucher issuance but continue stamp accrual.
- Cash bookings qualify for stamps only after merchant cash record and user confirmation; ops should sample-audit cash reward bookings.

Merchant admission state machine:
```text
pending_info
  -> shop_info
  -> photos
  -> payment_setup
  -> pending_review
  -> ops_review
  -> approved
  -> payment_recipient_verified
  -> live

ops_review -> rejected -> payment_setup
live -> suspended
suspended -> ops_review / live
```

Merchant visibility rules:

| State | Consumer can see | Can receive bookings |
|---|---|---|
| `pending_info` | No | No |
| `pending_review` | No | No |
| `rejected` | No | No |
| `approved` | No | No |
| `payment_recipient_verified` | No | No |
| `live` | Yes | Yes |
| `suspended` | No | No |

Go-live checklist:
1. Storefront photo matches submitted address.
2. Bay area photo shows actual wash bays.
3. Owner phone verified by call.
4. Bank account or QR ownership verified manually.
5. At least 1 active service configured.
6. At least 1 bay configured with availability.
7. Operating hours set.
8. Payment setup complete: bank info or QR uploaded.
9. Test booking completed end-to-end: hold, check-in, evidence, payment confirmation.
10. Reviewer, timestamp, and evidence stored in audit log.

Commission receivable state machine:
```text
accrued -> exported -> invoiced -> settled
invoiced -> waived
invoiced -> disputed -> resolved
```

Payment commission fields:
- `commission_status`
- `invoice_id`
- `settled_at`
- `waived_reason`
- `dispute_status`

Global state-machine rules:
- Booking, payment, evidence, reward, merchant admission, and commission transitions live in `app/domain/` state-machine modules.
- State-machine modules expose `can_transition`, `transition`, terminal-state helpers, and invalid-transition error codes used by services and tests.
- Booking completion requires service complete, evidence requirements satisfied or weak evidence explicitly allowed, and payment verified/cash recorded.
- Reward stamp finalization happens only after booking is completed and user confirmation/rating rules are satisfied.
- Ops state changes must write audit log entries.

Gates:
- Alembic check constraints and OpenAPI enum values match `app/domain/states.py`.
- Reward C10/C11/C12 flows pass Maestro and state-machine integration tests.
- No reward stamp finalizes before payment is verified.
- No duplicate reward stamp is created by retries.
- Merchant admission integration tests pass; no merchant reaches `live` without all go-live checklist items.
- Commission export CSV includes commission status, invoice, settlement, waiver, and dispute fields.

## 10. Booking Concurrency Pattern

Current schema uses `slot_capacity.status`, not `available_count`. The Python port must preserve atomicity with Postgres writes.

Hold algorithm:
```text
request: user_id, merchant_id, service_id, bay_number, time_slot, idempotency_key

transaction starts
  set local tenant/user/role context
  insert or read idempotency_keys row for user+key
  acquire pg_advisory_xact_lock(hash(tenant_id, merchant_id, time_slot))
  verify active holds per user < 3
  verify active holds for this merchant/user < 2
  update slot_capacity
     set status='held', held_by_user_id=:user_id, held_at=now(), expires_at=now()+hold_ttl
   where tenant_id=:tenant_id
     and merchant_id=:merchant_id
     and bay_number=:bay_number
     and time_slot=:time_slot
     and (
       status='available'
       or (status='held' and expires_at < now())
     )
   returning id
  if no row: SLOT_FULL
  insert booking with status='held'
  insert domain_event booking.held
  persist idempotency response body
transaction commits
```

Deadlock/retry:
- Retry serialization/deadlock failures up to 3 times with jitter.
- Never retry business errors such as `SLOT_FULL`, `HOLD_LIMIT_EXCEEDED`, `INVALID_PROMO`.
- Idempotency key returns the exact same response for replay within TTL.

Indexes:
- unique `(merchant_id, bay_number, time_slot)` on `slot_capacity`.
- partial index on active holds by `held_by_user_id` where status=`held`.
- index on bookings by user/status/expires_at.
- index on bookings by merchant/status/start_at.

Gate:
- Hypothesis/property tests for state transitions.
- Integration tests for 10, 50, and 100 concurrent hold attempts.
- No double-hold under load.


No-show policy:
- Track no-show count per user with a 30-day rolling window.
- 1st no-show: warning notification.
- 2nd no-show within 30 days: second warning notification.
- 3rd no-show within 30 days: require 50,000 VND deposit on next booking hold.
- `deposit_amount` is stored on Booking.
- If deposit is required, hold flow adds deposit step before slot is reserved.
- On check-in, deposit is deducted from service payment.
- On no-show with deposit, deposit is forfeited minus 20,000 VND penalty; remainder is refunded.
- `no_show_count` and `last_no_show_at` are tracked on user profile.

No-show gate:
- No-show tracking integration tests pass.
- Third no-show deposit requirement is enforced in hold flow.

## 11. Auth, RBAC, RLS, Rate Limits

Auth model:
- Access token TTL: 15 minutes.
- Refresh token TTL: 30 days.
- Refresh token family with rotation on every refresh.
- Refresh token reuse detection revokes the whole family and writes `failure_log`.
- Logout revokes current refresh token; logout all revokes the family.
- Tokens stored in `expo-secure-store`, never AsyncStorage.

Roles:
- `consumer`
- `merchant_pending`
- `merchant_live`
- `merchant_suspended`
- `ops`
- `finance_ops`
- `quality_ops`
- `admin`

Backend dependencies:
- `require_user()`
- `require_role(*roles)`
- `require_tenant()`
- `require_merchant_access(merchant_id)`
- `require_booking_access(booking_id)`
- `require_ops_scope(scope)`

Rate limits:
- Login: 5 attempts per 15 minutes per IP+identifier.
- Signup: 3 attempts per hour per IP+device.
- Signup device cap: max 3 accounts per device ID. Exceeding returns 429 with `Retry-After`.
- Refresh: 20 per hour per token family.
- Booking hold: max 3 active holds per user, max 2 active holds per merchant per user.
- Promo validation: 30 per hour per user.
- Evidence presign: max 8 active presigns per booking.
- Global: 100 requests per minute per IP across all endpoints. Return 429 with `Retry-After`.

RLS stance:
- Development can start with app-level filters.
- Production cutover requires DB RLS for tenant/user-scoped data.
- Each request transaction sets `app.current_tenant`, `app.current_user`, and `app.current_role` using `SET LOCAL`.
- Cross-tenant tests must fail at DB level, not only API level.

RLS phases:
- Phase A: tenant middleware and app-level filters for all repositories.
- Phase B: DB RLS for bookings, payments, evidence, slot_capacity, merchant_services, merchants, profiles, vehicles, complaints, reward tables, promo tables.
- Phase C: DB RLS for audit/failure/export tables and ops-scoped policies.


Connection pooling and roles:
- Production deployment includes PgBouncer in transaction mode with 200 prepared statements, sized for expected API and worker concurrency.
- `app` role: RLS-enforced, sets `app.current_tenant`, `app.current_user`, and `app.current_role` per transaction.
- `app_bypass` role: BYPASSRLS for auth bootstrap, ops exports, and worker batch jobs only.
- SQLAlchemy session middleware must replicate the current dual-pool pattern from `RlsContext.kt` and `RlsTransaction.kt`.
- Tests prove normal API requests cannot use `app_bypass`.

First-cutover App Attest replacement:
- Native App Attest parity is deferred.
- Compensate with rate limits, device token registration, refresh theft detection, request IDs, anomaly alerts, and ops kill switch.

## 12. Realtime Plan

Use Supabase private Broadcast channels.

Channels:
- `booking:user:{user_id}`
- `booking:merchant:{merchant_id}`
- `merchant:queue:{merchant_id}`
- `reward:user:{user_id}`
- `ops:tenant:{tenant_id}`

Events:
- booking created, checked_in, in_progress, awaiting_payment, completed, expired, cancelled
- payment user_claimed, cash_offered, verified, disputed
- evidence uploaded, processed, weak_evidence
- reward stamp_pending, stamp_finalized, voucher_issued, voucher_reserved, voucher_redeemed
- complaint created, assigned, resolved
- merchant admission/payment recipient status changed

Authorization:
- Clients subscribe with `config: { private: true }`.
- Database broadcasts use the matching private flag.
- Policies on `realtime.messages` use `realtime.topic()` and authenticated user identity.
- Authenticated identity comes from the FastAPI-issued Realtime JWT from `POST /v1/realtime/token`.
- Policies match topic names against JWT claims: `sub` for `booking:user:{user_id}` and `reward:user:{user_id}`, `merchant_ids` for merchant channels, and `ops_scopes` plus `tenant_id` for ops channels.
- Consumer can listen only to their own booking/reward topics.
- Merchant live user can listen only to their merchant queue topics.
- Ops can listen only to tenant topics allowed by their scope.
- Broadcast payloads contain IDs and state, not sensitive full records.

Fallback polling:
- Active booking: every 5 seconds while focused.
- Merchant queue: every 5 seconds while focused, every 15 seconds in background/low power.
- Payment pending: every 3 seconds for the first minute, then every 15 seconds.
- Show stale banner after repeated refresh failures.

Gate:
- Unauthorized channel joins fail.
- Expired, wrong-tenant, wrong-merchant, and missing-scope Realtime JWT channel joins fail.
- Authorized channel joins pass on iOS, Android, and web.
- Poll fallback updates UI after simulated Realtime disconnect.
- Realtime/offline lifecycle matrix passes: token expiry while subscribed, reconnect ordering, background/foreground, app kill/reopen, and queued mutation flush.

## 13. Worker Plan

One `worker` command runs from the same Python image.

```text
worker loop
  |-- claim due worker_jobs with durable run ledger
  |-- drain domain_events with SKIP LOCKED and processed_domain_events inbox checks
  |-- expire stale holds every 60s
  |-- release stale vouchers every 60s
  |-- process evidence uploads every 10s
  |-- evidence timeout check every 5m
  |-- stale merchant detection every 10m
  |-- merchant payment reminder every 5m
  |-- complaint SLA escalation every 5m
  |-- daily summary materialization every 15m
  |-- slot capacity pre-seed daily at 23:30 UTC
  |-- retention sweep daily at 03:00 UTC
  |-- welcome workflow trigger on first login
  |-- push notification retry
  |-- export jobs
  \-- data export/delete account tasks on demand
```

Job rules:
- Use Postgres advisory locks so two workers do not execute the same scheduled job.
- Use `domain_events` and `FOR UPDATE SKIP LOCKED` for retryable async events.
- Use `worker_jobs` and `worker_runs` as the durable scheduler ledger for all scheduled jobs.
- Each scheduled job writes started/succeeded/failed/skipped runs with owner_id, attempt count, lease expiry, high-water mark, rows processed, and error context.
- Worker startup scans stale `running` runs whose lease expired and either resumes from the recorded high-water mark or marks them failed before retry.
- Alerts fire when `worker_jobs.last_success_at` exceeds max_lag_seconds or a run exhausts retries.
- Every API transaction that needs async side effects writes `domain_events` in the same database transaction as the state change.
- Event consumers claim events with `FOR UPDATE SKIP LOCKED`, check `processed_domain_events`, process idempotently, then mark the event processed or dead-lettered.
- Event ordering is per `(tenant_id, aggregate_type, aggregate_id, aggregate_version)`; consumers must tolerate gaps and duplicate delivery.
- Event payloads are schema-versioned, IDs-only where possible, and never contain user-facing localized prose.
- Every job is idempotent.
- Dead-letter after bounded retries with enough context for ops review.
- Worker restart must catch up stale holds, evidence processing, exports, and complaint SLA tasks.

Slot pre-seeding:
- Each active merchant bay gets 30-minute slots for operating hours.
- `slot_capacity.status` starts as `available`.
- On hold: set `status='held'`, `held_by_user_id`, `held_at`, and `expires_at`.
- On expiry: reset to `available` and clear hold fields.
- Unique index: `(merchant_id, bay_number, time_slot)`.

Evidence timeout:
- If after-photo is not uploaded 30 minutes after check-in, send merchant prompt notification.
- Set evidence status to `evidence_pending` and flag for ops quality review.

Stale merchant detection:
- Query live merchants where slot capacity or queue heartbeat has not updated for more than 2 hours.
- Set `merchant.stale = true`.
- Hide stale merchants from nearby recommendations.
- Send ops alert.
- Merchant must manually refresh availability or complete a check-in to reappear.

Merchant payment reminder:
- If payment is `user_claimed` but not `merchant_confirmed` after 5 minutes, send merchant reminder.
- If still unconfirmed after 15 minutes, send ops escalation alert.

Retention sweep:
- Prune `idempotency_keys` older than 24 hours.
- Prune processed `domain_events` older than 7 days.
- Prune stale `device_tokens` unregistered for more than 30 days.
- Prune expired `refresh_tokens` older than 30 days past expiry.

Welcome workflow:
- On first successful login when no profile exists, bootstrap profile with `locale='vi'` and default name if skipped.
- Send welcome push notification.
- If referred, apply referral bonus.

Complaint escalation ladder:
```text
created
  -> 48h SLA timer starts
  -> no response at 36h: escalate to Ops Manager
  -> no response at 60h: escalate to CEO/designated lead
  -> requires_more_info: 7-day auto-close if no customer response
  -> refund_approved: refund processed, voucher handled
  -> rejected: customer notified with reason
```

Complaint voucher handling:
- If a voucher was used in the disputed booking, freeze it.
- On refund approval, invalidate the voucher.
- On rejection, restore the voucher.

Account deletion workflow:
```text
requested -> cancellable_20d -> processing -> completed
requested -> cancellable_20d -> cancelled
processing -> manual_escalation_7d -> completed
```

Account deletion rules:
- User requests deletion via `DELETE /v1/me/account`.
- 20-day cancellable window. User cancels via `POST /v1/me/cancel-delete`.
- After the window, worker begins fan-out deletion.
- Per-store activities: Postgres user data, storage files, push token revocation, analytics removal request.
- Each activity produces a receipt stored in `deletion_receipts`.
- If any store fails after 3 retries, escalate to manual escalation with a 7-day extension.
- User can request extension for third-party coordination if required by the applicable privacy process.

Data export rules:
- `POST /v1/me/data-export` triggers async job.
- `GET /v1/me/data-export/{job_id}` returns status and signed URL when complete.
- Bundle includes profile, vehicles, bookings, payments, evidence metadata, ratings, reward history, and referral data.
- Signed URL expires after 7 days.
- Export bundle is generated from Postgres and object metadata only; no Kafka/NATS/Typesense dependency remains.

Worker gates:
- Domain event tests prove same-transaction emit, duplicate delivery safety, per-consumer idempotency, dead-letter behavior, and per-aggregate ordering.
- Durable scheduler ledger tests prove crash recovery, missed-run catch-up, lease expiry, and max-lag alerts.
- Deletion dry-run passes.
- Data export bundle contains all user-owned data.
- Cancel-delete works within the 20-day window.
- Complaint SLA timer fires correctly.
- Voucher freeze/restore works.
- Tag auto-removal and stale merchant jobs run.

## 14. Mobile Route Manifest

These routes are mandatory for full parity.

Route coverage is tracked in `docs/route-test-matrix-v1.md`. That matrix is the CI-enforced source for route test IDs, required UI states, unit/screen/E2E coverage, and owner.

| PRD ID | Persona | Route | Complexity | Must cover |
|---|---|---|---|---|
| O1-Final | Consumer | `app/(auth)/signup.tsx` | M | invite/referral code, email/phone, duplicate, invalid invite, support fallback |
| O2-Final | Consumer | `app/(auth)/quick-profile.tsx` | S | optional profile, vehicle, skip, later edit |
| C1 | Consumer | `app/(consumer)/home.tsx` | H | GPS permission, nearby list, denied fallback, pull refresh, 60s focused refresh |
| C3 | Consumer | `app/(consumer)/merchant/[id].tsx` | VH | services, bay grid, promo validation, external maps, custom service badges |
| C4 | Consumer | `app/(consumer)/booking/[id].tsx` | VH | countdown, QR, fallback code, cancel, expire, maps resume refetch |
| C5-Final | Consumer | `app/(consumer)/checkin/[id].tsx` | M | full-screen QR, fallback code, arrived CTA |
| C6-Final | Consumer | `app/(consumer)/payment/[id].tsx` | H | merchant QR, cash, user-claimed, exact amount, pending confirm |
| C7 | Consumer | `app/(consumer)/evidence/[id].tsx` | H | before/after photos, rating, weak evidence warning, pending reward |
| C9 | Consumer | `app/(consumer)/profile/index.tsx` | M | vehicle edit, history, language, promo list, logout, privacy actions |
| C10 | Consumer | `app/(consumer)/rewards/index.tsx` | M | progress, active vouchers, budget paused, history |
| C11 | Consumer | `app/(consumer)/rewards/redeem.tsx` | M | eligible service, apply voucher, stacking conflicts |
| C12 | Consumer | `app/(consumer)/rewards/celebration.tsx` | S | threshold trigger, redeem now/later |
| MO1-Final | Merchant | `app/(merchant-onboarding)/signup.tsx` | M | merchant invite/signup, pending role |
| MO2-Final | Merchant | `app/(merchant-onboarding)/shop-info.tsx` | M | address, bay count, hours |
| MO3-Final | Merchant | `app/(merchant-onboarding)/photos-services.tsx` | VH | storefront/bay photos, compression, upload queue, templates, custom service |
| MO4-Final | Merchant | `app/(merchant-onboarding)/payment-setup.tsx` | H | bank info, QR upload, ownership pending review |
| M1 | Merchant | `app/(merchant)/queue/index.tsx` | VH | bay grid, live updates, booking list, promo/reward tags, never-sleep mode |
| M2 | Merchant | `app/(merchant)/slots/index.tsx` | H | bay status, service config, golden hour, price-change log |
| M4 | Merchant | `app/(merchant)/summary/index.tsx` | M | revenue, QR/cash totals, promo/reward rows, CSV export |
| M-Service | Merchant | `app/(merchant)/bookings/[id].tsx` | H | scan QR, before/after capture, complete service, payment confirm/cash record |
| OPS-1 | Ops | `apps/ops-web/src/routes/admissions` | H | review shop photos, service config, payment recipient, go-live/suspend |
| OPS-2 | Ops | `apps/ops-web/src/routes/commission` | M | receivables, CSV exports, reward-funded payouts |
| OPS-3 | Ops | `apps/ops-web/src/routes/complaints` | H | 6-category triage, refund/voucher decisions, SLA |
| OPS-4 | Ops | `apps/ops-web/src/routes/network-health` | M | stale merchants, SLA dashboard, fallback actions |
| OPS-5 | Ops | `apps/ops-web/src/routes/growth-ekyc` | M | merchant pipeline, eKYC/bank review, audit trail |

Gate:
- Every row has loading, empty, error, offline, forbidden, and retry states.
- Every row has stable `testID` selectors.
- `make route-test-matrix.check` proves every mandatory route has a matrix row, required state coverage, owner, and matching test files.
- H/VH screens have Maestro coverage before implementation is considered done.

## 15. Native Mobile Capabilities

Required packages:
- `expo-camera` for before/after photos and QR scanning.
- `expo-location` for nearby discovery and denied fallback.
- `expo-secure-store` for access/refresh token storage.
- `expo-notifications`, `expo-device`, `expo-constants` for push registration.
- `expo-image-manipulator` for resize/compress.
- `expo-file-system` for local evidence files.
- `expo-background-task` and TaskManager only for deferrable retry hints.
- Expo Router deep links for `truecare://` and universal link paths.

Evidence flow:
```text
capture with expo-camera
  -> avoid/strip EXIF where possible
  -> compress/resize with expo-image-manipulator to target <500KB
  -> store file in expo-file-system
  -> request presigned URL
  -> upload directly to storage
  -> confirm evidence with hash/size/content type
  -> delete local file after server confirms
  -> on failure queue retry with idempotency key
  -> after 10 attempts or 24h mark ops review needed
```

Payment user-claimed offline flow:
- User taps "Da chuyen".
- Create idempotent mutation with payment ID and expected amount.
- If online, call API immediately.
- If offline, queue mutation and show pending local state.
- Flush in order on reconnect/focus.
- Server enforces idempotency and state transition validity.

Booking resume flow:
- Every booking-related screen uses focus/resume invalidation.
- Maps handoff always triggers booking/payment refetch on return.
- Realtime is primary; polling is fallback.


VETC placeholder behavior:
- O1 signup shows disabled `Login with VETC` action at 0.5 opacity.
- C6 payment shows disabled `VETC Wallet - Coming soon` action at 0.5 opacity.
- Tapping opens a bottom sheet explaining the future benefit.
- Data model keeps `users.vetc_id` nullable and `users.auth_provider` as `local` or `vetc`.

C3 merchant phone action:
- Merchant detail screen includes a secondary call button that opens `tel:{merchant_phone}`.
- If no phone exists, show disabled state and ops support fallback.

Deep links:
- `truecare://booking/{id}`
- `truecare://payment/{id}`
- `truecare://complaint/{id}`
- `truecare://referral/{code}`
- `truecare://promo/{code}`
- `truecare://reward`
- `truecare://settings`
- `truecare://force-update`
- Universal links use `https://truecare.vn/` with AASA file at `/.well-known/apple-app-site-association`.
- Persist unresolved links in AsyncStorage and consume when the app becomes active.

Force update behavior:
- On launch, call `GET /v1/app/version-check`.
- Class A payload: show dismissible update prompt.
- Class B payload: block app usage until update.
- After push notification `force-update-invalidate`, refetch version check.
- Version payload is Ed25519-signed and includes minimum supported build, app store URL, localized messages, payload class, and expiry.

Feature flags:
- Client reads `GET /v1/flags` after auth and on app resume.
- Minimum flags: `presence`, `search`, `delete_now`, `reward_active`, `promo_active`, `vetc_login_visible`.
- Flags are kill switches and rollout controls, not permanent parity gaps.

Gate:
- Airplane mode test for evidence capture and later upload.
- Payment queue flush test.
- Maps handoff resume test.
- App kill/reopen retains pending evidence queue without losing local file references.
- Push notification token registration and foreground/background receive behavior tested on physical devices.
- Realtime/offline lifecycle tests prove evidence queue and payment queue survive background/foreground, app kill/reopen, expired Realtime token, reconnect, and replay.


## 16. Pricing, Search, Promo, Service Tags, and Go-Live Guards

Search decision:
- P0 uses PostGIS nearby ranking plus `pg_trgm` trigram matching for merchant name, address, and service type queries.
- Do not reintroduce Typesense or Photon for P0.
- Add Meilisearch in P1 only if pilot data proves PostGIS + pg_trgm search quality is insufficient.
- Search results are constrained to the pilot radius and respect merchant `live`, `stale`, service availability, and tenant filters.


Nearby merchant ranking formula:
```text
merchant_score =
  (available_bays > 0 ? 1000 : 0)
  + rating_average * 100
  + 50 / (distance_km + 0.1)
  + (mode_tags overlap user_preferences ? 100 : 0)

order by merchant_score desc
```
Parameters:
- Available bays: 1000 point binary boost.
- Rating: multiplied by 100. A 4.8 rating contributes 480 points.
- Distance: inverse factor `50 / (km + 0.1)`. One km contributes about 45.5 points; five km about 9.8 points.
- Mode match: 100 point boost when merchant tags overlap user preference.
- GPS denied/error: return static pilot-cluster list sorted from cluster center.
- Merchant stale more than 2h: exclude from ranking.

P0 search type behavior:
- `type=merchant` is the only supported value in P0.
- `type=place` is a P1 placeholder and returns an empty list in P0.

Search gate:
- `GET /v1/search` returns merchant-only P0 results ordered by the formula above for merchant name, address, and service type queries within 5km radius.
- Unauthorized or suspended merchants never appear.

Promo validation and stacking:
- Code not found -> `PROMO_NOT_FOUND`.
- Inactive code -> `PROMO_INACTIVE`.
- Expired code -> `PROMO_EXPIRED`.
- Total usage limit reached -> `PROMO_EXHAUSTED`.
- User already used per-user limit -> `PROMO_ALREADY_USED`.
- Merchant mismatch -> `PROMO_MERCHANT_MISMATCH`.
- Service template mismatch -> `PROMO_SERVICE_MISMATCH`.
- Order total below minimum -> `PROMO_MIN_ORDER_NOT_MET`.

Discount stacking rules:
- Promo Code + Gio Vang: choose higher discount, do not stack.
- Promo Code + Referral Discount: both apply because targets differ.
- Promo Code + Reward Voucher: cannot combine.
- Gio Vang + Referral Discount: cannot combine.
- Gio Vang + Reward Voucher: cannot combine.

Service mode tag enforcement:
- Canonical tags: `fast_lane`, `premium_care`, `drive_thru`, `night_owl`.
- Max 3 tags per merchant.
- `premium_care`: evidence coverage above 95% and rating above 4.5. If below threshold, auto-remove and notify merchant.
- `fast_lane`: actual service duration below 25 minutes in 90% of completed bookings. If violated, flag for ops review.
- `drive_thru`: merchant has confirmed shelter/masking in MO3 shop photos; ops verifies during go-live review.
- `night_owl`: operating hours end at or after 20:00.
- Tags are selected in MO3 and confirmed by ops during go-live review.

Go-live guard:
- Merchant cannot go live with zero active services.
- Merchant cannot go live with zero available bays.

## 17. Migration Plan

Create `docs/migration-map-v1.md` before implementation.

Required columns:
- old table
- old columns
- new table
- new columns
- transformation
- RLS policy mapping
- seed dependency
- rollback note
- verification query

Critical table groups:

| Group | Old source | Target stance | Verification |
|---|---|---|---|
| Tenancy/auth | tenants, users, tenant_memberships, refresh_tokens, invite_codes | Keep and normalize enum values | user count, membership count, active invite count |
| Consumer profile | profiles, vehicles, device_tokens, location_history | Keep | profile/user FK integrity, sample user journey |
| Merchant catalog | merchants, merchant_services, service_templates, slot_capacity, price_change_log | Keep | PostGIS index, price floor/ceiling, slot unique index |
| Core loop | bookings, payments, evidence, ratings | Keep | state distribution, completed booking reconciliation |
| Promotions | promo_codes, promo_code_usages | Keep | 8 validation rules replay on historical examples |
| Rewards/referrals | reward_stamps, reward_vouchers, referrals | Keep | no duplicate stamps, voucher lifecycle state count |
| Ops | complaints, merchant_pipeline_log, audit_log, failure_log | Keep | SLA status count, audit actor present |
| Privacy | deletion_receipts | Keep | deletion/export job dry-run |
| Infra collapse | outbox, processed_events | Replace with `domain_events` if needed | no stuck old events at cutover |
| Deferred analytics | budget_items, channel_sources, feedback_log, admission_scores | Archive unless current screens use them | archive checksum |
| i18n | entity_translations | Replace with app i18n files unless DB-driven copy is used | language smoke test |

Seed scripts:
- service templates
- pilot tenant
- ops users
- invite/referral codes
- 12-20 merchant staging cluster
- bay/slot capacity for 7 days
- promo codes covering all 8 validation cases
- reward campaign config

Shadow-read harness:
- Run old and new API read endpoints against a frozen snapshot.
- Compare JSON-normalized outputs for discovery, merchant detail, booking detail, payment detail, rewards, profile, merchant queue, daily summary.
- Log differences with request ID and fixture ID.

Parity fixture corpus:
- Canonical fixtures live in `test-fixtures/parity/`.
- Each fixture is a JSON file with: `id`, `domain`, `source_commit`, `scenario`, `setup`, `request`, `old_response`, `expected_new_response`, `must_match_fields`, `intentional_differences`, `waiver_reason`, and `owner`.
- Domains required for launch: booking, payment, reward, promo, evidence, auth/session, merchant discovery, merchant queue, daily summary, and complaints.
- Fixture IDs are stable and referenced from pytest, Schemathesis, Maestro, and Playwright tests where applicable.
- Intentional differences require a non-empty `waiver_reason` and owner; unowned drift blocks release.
- `make parity.capture` runs the current Kotlin service against selected scenarios and updates `old_response`.
- `make parity.verify` runs the Python service against the same fixtures and fails on unwaived drift.
- `make parity.update --fixture <id>` updates expected output only when paired with a reviewed waiver or accepted intentional behavior change.

Gate:
- Migration dry-run is repeatable.
- Row counts and checksums pass for critical tables.
- Shadow-read diff is zero for must-match fields or explicitly waived.
- `make parity.verify` passes for all launch-required domains.
- Restore-from-backup rehearsal completed in staging.

## 18. Testing Strategy

Backend:
- `pytest`
- `pytest-asyncio` or AnyIO style async tests
- `httpx.AsyncClient`
- `testcontainers-python` with PostgreSQL/PostGIS
- `hypothesis` for state/property tests
- `schemathesis` for OpenAPI contract tests
- factories for tenant, user, merchant, service, slot, booking, payment, evidence, promo, reward

Mobile:
- Vitest for pure functions/hooks.
- React Native Testing Library for screen behavior.
- Maestro for E2E because 105 YAML flows already exist and Maestro supports Expo/RN without app instrumentation.
- Stable `testID` selectors, not Vietnamese text.
- Physical-device tests for push notifications and camera edge cases.

Ops web:
- Vitest for utilities/components.
- Playwright for admissions, complaints, exports.

Parity harness:
- Current Kotlin service behavior becomes fixture oracle for booking, payment, reward, promo, evidence.
- New Python service runs the same fixtures.
- Differences are classified as compatible, intentional, or blocker.
- `test-fixtures/parity/` is the shared corpus consumed by the Kotlin oracle capture, Python pytest suite, contract tests, and selected E2E flows.
- CI blocks on unwaived parity drift in launch-required domains.

CI lanes:
- `lint-typecheck`
- `backend-unit`
- `backend-integration-db`
- `contract-schemathesis`
- `mobile-unit`
- `route-test-matrix-check`
- `mobile-maestro-smoke`
- `ops-playwright`
- `migration-dry-run`
- `load-smoke` nightly or pre-release

Critical regression tests:
- Booking hold concurrency.
- Payment confirmation idempotency.
- Full payment transition matrix: QR, cash, user-claimed, merchant-confirmed, merchant-denied, switch-method, disputed, cancelled, replay, and invalid transitions.
- Evidence upload retry.
- Realtime fallback.
- Realtime/offline lifecycle matrix: token expiry while subscribed, reconnect ordering, background/foreground, app kill/reopen, queued evidence/payment flush, and replay safety.
- Ops tenant scope enforcement.
- Promo/reward stacking rules.
- Complaint SLA escalation.
- Refresh token replay detection.

## 19. Performance and Reliability Gates

PRD targets:
- API p95 < 500 ms for main reads/writes.
- Nearby merchant p95 < 500 ms for 12-20 merchants within 5km.
- Booking hold p95 < 500 ms under expected pilot concurrency.
- Evidence upload perceived completion < 5s on normal network after compression.
- QR scan/check-in < 2s after camera is open.
- Mobile cold start < 3s on target devices.


Additional non-functional requirements:

| Metric | Target |
|---|---|
| Screen transition time | < 300 ms |
| Countdown accuracy | +/- 1 second |
| Global API rate limit | 100 req/min per IP |
| Photo signed URL expiry | 15 minutes |
| Photo upload success rate | > 99% |
| Booking hold success rate | > 99.9% |
| API uptime | 99.9% |
| Merchant dashboard uptime | 99.5% |
| Minimum touch target, consumer | 48px |
| Minimum touch target, merchant | 56px |
| Color contrast | WCAG AA |
| Minimum viewport width | 320px |
| Vietnamese diacritics line-height | >= 1.5 |
| Screen reader | All CTAs accessible |
| GPS fallback latency | Static list visible within 5 seconds if denied/error |

Backend load scenarios:
- Login/refresh burst.
- Nearby discovery with PostGIS radius and ordering.
- Merchant detail with services/bays without N+1.
- Concurrent booking holds: 10, 50, 100 attempts.
- Payment confirm replay/idempotency.
- Payment merchant-denied and switch-method replay/idempotency.
- Merchant queue polling plus realtime events.
- Ops admissions list with filters.

Mobile measurements:
- iOS low-end and Android low-end physical devices.
- App cold start.
- C1 render with 20 merchants.
- C3 service list and bay grid render.
- Camera open to photo captured.
- Photo compress/upload queue.
- QR scan to checked-in state.

Reliability gates:
- Worker restart catches up stale holds, complaint SLA, evidence processing.
- Domain event processing is idempotent.
- Failed push notification records retry and does not block booking/payment.
- Backup restore tested.
- Rollback runbook tested by switching mobile API base URL or feature flag.

## 20. Observability and Ops Readiness

Backend:
- Sentry Python SDK.
- `structlog` JSON logs.
- Request ID in every response and log line.
- `/healthz` checks process liveness only.
- `/readyz` checks Postgres, storage, and Supabase Realtime connectivity.
- `/metrics` exposes Prometheus-compatible FastAPI and worker metrics.
- Prometheus-compatible FastAPI instrumentation.

Mobile:
- Sentry React Native.
- Release/channel tags.
- User/session anonymized identifiers.
- Error boundaries around payment, evidence, booking, and merchant queue.


Backend internationalization:
- All server-rendered user-facing text for push titles/bodies, email subjects/bodies, SMS bodies, and localized error titles/details must use message bundles.
- Supported locales: `vi` primary, `en` secondary.
- Push payloads use action code plus `loc_key` and `loc_args`; do not put user-facing prose in push payloads.
- Error responses use RFC 9457 Problem Details with stable `type` URI and localized `title`/`detail` based on `Accept-Language`.
- Error codes and Problem Details metadata come from `app/core/errors.py`; route handlers raise typed domain errors instead of hand-writing titles/details.
- PII-free loc args only.

Minimum push action codes:
- `booking_confirmed`
- `booking_reminder`
- `booking_cancelled`
- `payment_received`
- `reward_earned`
- `complaint_update`
- `welcome_ready`
- `force_update`

I18n gate:
- No hardcoded Vietnamese or English prose in API response bodies or push payloads.
- Lint rule or static check enforces message-bundle usage in CI.
- CI verifies every error registry entry has `vi` and `en` title/detail message keys plus OpenAPI examples.

Alerts:
- API error rate.
- API p95 latency.
- Worker lag.
- Failed evidence jobs.
- Failed payment confirmations.
- Realtime channel join failures.
- Queue backlog.
- Refresh token replay detection.
- Complaint SLA breach.

Runbooks:
- Booking stuck in held/awaiting_payment.
- Merchant cannot scan QR.
- Evidence upload stuck.
- Payment dispute or wrong amount.
- Realtime outage fallback.
- Data export/delete request.
- Restore-from-backup.
- Mobile rollback/API origin switch.

## 20.1 Artifact Distribution Matrix

Every new artifact must have a repeatable build, publish, install, and rollback path before production cutover.

| Artifact | Build output | Publish target | Version source | CI lane | Rollback unit |
|---|---|---|---|---|---|
| FastAPI API | OCI image with `api` command | Selected deploy platform registry | git SHA + app semver | `api-image-build` | previous API image |
| Python worker | Same OCI image with `worker` command | Selected deploy platform registry | git SHA + app semver | `worker-image-build` | previous worker image |
| Generated TypeScript client | npm workspace package or checked-in generated client | internal package workspace first; registry only if multi-repo later | OpenAPI spec hash + git SHA | `client-generate-compile` | previous generated client commit |
| Expo mobile app | EAS build for iOS and Android | TestFlight / Play internal track, then stores | Expo runtime version + app build number | `mobile-eas-build` | previous store/TestFlight build plus API origin switch |
| Ops web | static Vite bundle | selected web host/CDN | git SHA + app semver | `ops-web-build` | previous web deployment |
| Migration tool | Python module/CLI in API image | same API image plus release command | Alembic revision + git SHA | `migration-dry-run` | restore backup plus forward fix |
| Seed tool | Python module/CLI in API image | same API image plus release command | seed manifest checksum | `seed-verify` | restore backup or idempotent seed rollback |

Distribution rules:
- CI must build every artifact from a clean checkout.
- Generated clients are never hand-edited; CI fails if OpenAPI output is stale.
- API and worker image tags must include immutable git SHA tags and human-readable release tags.
- Mobile runtime version changes only when an OTA update cannot safely carry the change.
- Migration commands must support dry-run, checksum output, and explicit production confirmation.
- Rollback rehearsal must include API image rollback, worker image rollback, Ops web rollback, and mobile API origin/feature-flag rollback.

## 21. Implementation Phases

Status last updated: 2026-05-18.

Completed slices:
- [x] Foundation scaffold: FastAPI API, Expo shell, Ops web shell, OpenAPI export, generated TypeScript client, migration map, route-test-matrix gate, and local Makefile gates.
- [x] Backend foundation POC: SQLAlchemy async session, Alembic baseline, auth signup/login/refresh/logout/me, RBAC dependencies, tenant context, RLS proof table, idempotency service, domain events repository, worker drain skeleton, and local Docker Postgres commands.
- [x] Core marketplace API slice 1: service templates, merchant discovery/detail/services/bays, booking hold/list/get/cancel, merchant queue read, same-transaction booking domain events, and regenerated OpenAPI client.
- [x] Core marketplace API slice 2: merchant check-in by QR/manual code, start service, complete service, transition events, integration coverage, and regenerated OpenAPI client.
- [x] Phase 2/3 backend completion slice: evidence presign/confirm/process, payments, rating, realtime token, promo, rewards, referrals, complaints, merchant custom service review/resubmit, price history, daily summary CSV, commission receivables, integration coverage, and regenerated OpenAPI client.
- [x] Phase 4 mobile foundation slice: Tamagui provider/config, SecureStore-backed auth store, generated API client runtime wrapper, TanStack Query provider, offline mutation queue, all 20 mandatory Expo Router files, mobile route-file gate, and JavaScript workspace typecheck.
- [x] Phase 5 Ops Web foundation slice: React Query provider, generated API client runtime wrapper, persisted bearer-token ops guard via `/v1/auth/me`, admissions/commission/complaints/network-health/growth-eKYC/audit route shells, shared loading/empty/error/offline/forbidden state surface, and ops route-file gate.
- [x] Backend hardening and Phase 6 readiness slice: structured JSON access logging, configurable global/auth rate-limit foundation with tests, migration dry-run planner for the 37-table map, deterministic seed manifest/checker, and shadow-read comparison dry-run harness.
- [x] Backend correctness closure + local cutover gates: production-table RLS migration and app-role coverage tests, booking hold storm tests for 10/50/100 requests, evidence confirm idempotency and retry exhaustion state, promo validation matrix with discount math, transactional audit rows plus `/v1/ops/audit-log`, daily summary CSV header/totals checks, and regenerated OpenAPI client.
- [x] P0-01 backend/API support slice: invite-gated signup, device cap, forgot-password support requests, profile, vehicles, sessions, password change, notification preferences/token registration, data export, account deletion/cancel, ops users/reset-password audit, mobile signup/profile data wiring, integration coverage, and regenerated OpenAPI client.
- [x] P0-02 merchant admission backend/API slice: merchant application, owner merchant membership upgrade, photo confirmation, local object-key payment setup and eKYC CMND/selfie/bank submissions, ops pending list, payment-recipient verification, approve/reject/suspend guards, transactional audit rows, cross-tenant admission RLS coverage, mobile onboarding basic data wiring, Ops admissions mutation wiring, and regenerated OpenAPI client.
- [x] P0 local route-closure backend/API slice: `/v1/me/bookings`, consumer arrived ping, merchant calendar/maintenance, Golden Hour table/API, ops data-room/export jobs, fallback booking/check-in/evidence/payment confirmation, ops reward voucher minting, transactional audit rows, integration coverage, and regenerated OpenAPI client.
- [x] P0 next local E2E closure slice: `/v1/auth/me` merchant context, stale-hold no-show/deposit worker path, replay-safe payment denial/switch/cash transitions, processed-domain-event/dead-letter worker coverage, local native capability adapters/file queue, consumer/merchant primary-action wiring, Ops fallback/export/complaint/audit action wiring, route matrix completed-row enforcement, and regenerated OpenAPI client.
- [x] Local E2E verification slice: stable local JWT signing key, deterministic consumer/merchant/ops QA fixtures, local API/Ops/Mobile Make targets, local-only runbook, and `make local.qa.smoke` covering auth exists/signup/login/me, discovery, hold/arrived/check-in, evidence, payment denial/switch/cash, rating, voucher redeem, referral share, complaint resolution, merchant queue/service transition, Ops fallback/export/audit actions, then restoring the fixture baseline.
- [x] Local E2E prerequisites and app-health slice: required CLI/Docker prerequisite checker, aggregate `make local.e2e.gates` target that restores fixture baseline at the end, API/Ops app health checker using seeded tokens, runner fail-fast targets for Maestro/Playwright prerequisites, and detailed E2E prerequisites documentation.

Current contract route status:
- [x] 103/103 contract routes have real handlers in the local FastAPI port.
- [x] 0/103 contract routes remain as typed `NOT_IMPLEMENTED` stubs.
- [ ] OpenAPI is still not frozen for production until Supabase Storage/Realtime, Maestro and Ops Playwright journeys, physical-device native checks, and cutover gates pass.

Current verification:
- [x] `make infra-prereqs.check`
- [x] `make secret-leak.check`
- [x] `make route-test-matrix.check`
- [x] `make mobile.route-files.check`
- [x] `make ops.route-files.check`
- [x] `make migration.dry-run`
- [x] `make seed.plan.check`
- [x] `make shadow-read.check`
- [x] `make db.up`
- [x] `make db.migrate`
- [x] `make local.e2e.prereqs`
- [x] `make local.e2e.gates`
- [x] `make local.qa.fixtures`
- [x] `make api.test`
- [x] `make api.integration`
- [x] `make client.generate`
- [x] `make worker.once`
- [x] `make local.qa.smoke`
- [x] `make local.app.check` against running local API and Ops web; mobile runtime status remains optional/manual until Expo/physical-device checks run.
- [x] `pnpm -r typecheck`
- [x] P0-02 targeted integration: merchant admission go-live guard, payment recipient verification, approve/reject/suspend audit, and cross-tenant admission reads blocked through app-role RLS.
- [x] Route-closure targeted integration: remaining 14 contract routes execute against local DB and ops mutations write audit rows.
- [x] P0-03 targeted integration: `/v1/auth/me` owner merchant context, no-show/deposit enforcement, payment denial/switch/cash replay safety, and local worker stale-hold expiry.
- [x] Worker recovery targeted integration: scheduled worker run ledger, processed-domain-event records, bounded retry exhaustion, and visible dead-letter rows.
- [x] Route matrix completed rows now require real mobile/Ops test file references and reject TODO coverage.
- [ ] `make supabase-readiness.check` after real Supabase credentials are available; the checker runs through `.venv` and does not require global `psql`/`jq`.

### Phase 0 - Production Design Freeze

Duration: 5-7 days.

Deliverables:
- [x] OpenAPI v1 contract skeleton and generated clients.
- [x] Route manifest and testID convention via `knowledge/00-porting/route-test-matrix-v1.md`.
- [x] UI system decision and shell primitives for Expo and Ops web shells.
- [x] Auth/RBAC/RLS spec and proof-of-concept implementation.
- [x] Rate-limit spec implementation.
- [x] Booking concurrency spike.
- [x] Offline/evidence queue local adapter spike.
- [ ] Realtime private channel policy spike.
- [x] Migration map for legacy 37-table schema.
- [x] Seed plan.
- [x] Test infrastructure skeleton for API unit/integration gates.

Exit gate:
- [x] Runner choice, UI library, RLS stance, and route manifest are no longer blocked for the first scaffold.
- [ ] Realtime private channel and shared-store production rate-limit spikes remain before Phase 0 is fully closed; offline evidence replay remains tracked under P0-07 physical/offline reliability.

### Phase 1 - Backend Foundation

Duration: 1.5-2 weeks.

Build:
- [x] FastAPI skeleton.
- [x] Alembic baseline.
- [x] SQLAlchemy async engine/session.
- [x] Request ID middleware.
- [x] RFC 9457 error envelope and registered typed errors.
- [x] Structured JSON logging.
- [x] Auth with refresh rotation.
- [x] Refresh-token reuse detection.
- [x] RBAC dependencies: `require_user`, `require_role`, `require_tenant`.
- [x] RLS tenant context through `SET LOCAL`.
- [x] Configurable rate limiter for global, login, signup, and refresh limits.
- [x] Idempotency service keyed by tenant, subject, and key with body-hash mismatch handling.
- [x] Domain events table and repository.
- [x] Worker skeleton with domain-event claim/drain no-op.
- [x] Health/readiness/metrics endpoints.
- [x] Local Docker Postgres commands: `db.up`, `db.down`, `db.migrate`.

Exit gate:
- [x] Auth/security integration suite passes.
- [x] DB RLS proof test passes for the first RLS table.
- [x] Generated client is regenerated from OpenAPI.
- [x] Rate-limit tests pass.
- [x] Structured logging checks pass.
- [x] RLS coverage expands from proof table to production tenant tables.

### Phase 2 - Core Marketplace Loop

Duration: 2-3 weeks.

Build:
- [x] Merchant discovery and detail.
- [x] Service templates and merchant service catalog reads.
- [x] Slot capacity and booking hold/list/get/cancel first cut.
- [x] Merchant queue read API.
- [x] Check-in QR/manual code.
- [x] Evidence presign/confirm/process.
- [x] Payment QR/cash/user-claimed/merchant-confirmed.
- [x] Rating.
- [x] Realtime token endpoint, domain events, and API polling surfaces.

Exit gate:
- [x] Full core loop passes API integration.
- [ ] Maestro smoke passes.
- [x] Concurrent hold tests pass.
- [x] No-show/deposit rule is implemented and covered by local worker integration.
- [x] Payment idempotency replay is implemented for initiate, user-claimed, merchant-confirmed, merchant-denied, switch-method, and cash-record paths.
- [x] Evidence retry tests pass.

### Phase 3 - Retention, Promo, Complaints, Ops Support

Duration: 2-3 weeks.

Build:
- [x] Promo code validation P0 backend.
- [x] Reward stamp/voucher lifecycle P0 backend.
- [x] Referral tracking and sharing event backend.
- [x] Complaint submission and ops resolution backend.
- [x] Merchant custom service review/resubmit.
- [x] Merchant price history.
- [x] Daily summary CSV.
- [x] Commission receivable export.
- [x] Voucher reserve/redeem and referral share mobile actions are wired locally.

Exit gate:
- [ ] Reward C10/C11/C12 mobile flows pass.
- [x] Referral backend smoke passes.
- [x] Complaint ops backend workflow passes.
- [x] Promo 8-case validation matrix and discount math pass.
- [ ] Promo stacking rules pass after Golden Hour/reward/voucher stacking surface is implemented.

### Phase 4 - Expo Mobile Parity

Duration: 4-6 weeks, parallelizable after Phase 0 and backend contract freeze.

Build lanes:
- [x] Mobile shell scaffold: Expo Router app shell.
- [x] Tamagui primitives/provider/config foundation.
- [x] Auth store foundation with SecureStore token persistence.
- [x] Generated client integration in app runtime.
- [x] Query client provider.
- [x] Offline mutation queue foundation.
- [x] Consumer lane route shells: O1/O2/C1/C3/C4/C5/C6/C7/C9/C10/C11/C12.
- [x] Merchant lane route shells: MO1-MO4/M1/M2/M4/M-Service.
- [x] Signup route accepts invite code and triggers real auth/device backend.
- [x] Profile route reads generated-client data for profile, vehicles, sessions, and notification preferences.
- [x] Merchant onboarding route screens submit application, photo confirmation, payment setup, and eKYC object keys through the generated client.
- [x] Consumer booking/check-in/evidence/payment/reward/profile primary actions are wired to generated-client mutations or the local offline queue.
- [x] Merchant queue/calendar/summary/service execution uses `/v1/auth/me` merchant context instead of hard-coded merchant IDs.
- [x] Local native capability adapters for camera permission, QR scan, GPS allow/deny fallback, push token registration, and file queue.

Exit gate:
- [x] All mandatory Expo Router files exist and compile in the JavaScript workspace.
- [x] Mobile route files expose matrix `testIDPrefix` values and use the shared state scaffold.
- [x] All mandatory route manifest rows have loading/error/offline/forbidden state requirements and local coverage references.
- [ ] Maestro smoke passes on iOS and Android.
- [ ] Physical-device camera/push/GPS tests pass.

### Phase 5 - Ops Web

Duration: 1-2 weeks.

Build:
- [x] Ops web scaffold: Vite React shell.
- [x] Ops auth/RBAC foundation: persisted bearer token and `/v1/auth/me` ops-role guard.
- [x] Admissions queue route shell with pending merchants API binding and payment-recipient action surface.
- [x] Admissions mutation wiring for approve, reject, payment-recipient verify, and suspend.
- [x] Commission receivables route shell with generated client binding.
- [x] Complaint triage route shell with refund/voucher decision visibility.
- [x] Network health route shell for stale merchants and fallback actions.
- [x] Growth/eKYC route shell for merchant pipeline review.
- [x] Audit log route shell.
- [x] Ops fallback booking/export/complaint/voucher/audit-search actions are wired through the generated client.

Exit gate:
- [x] Mandatory Ops web route files exist, expose matrix `testIDPrefix` values, and compile.
- [ ] Playwright ops journeys pass.
- [x] Exports return correct CSV headers and totals.
- [x] Implemented ops actions write audit log.

### Phase 6 - Migration, Soak, Cutover

Duration: 1-2 weeks.

Build:
- [x] Migration script with dry-run mode.
- [x] Seed manifest/checker.
- [x] Shadow-read compare dry-run harness.
- [ ] Production deploy pipeline.
- [ ] Backup/restore rehearsal.
- [ ] Feature-flagged API origin switch.
- [ ] Launch dashboards and alerts.

Cutover gate:
- [ ] 48h staging soak.
- [ ] 20+ synthetic bookings with no state divergence.
- [ ] Migration dry-run and restore rehearsal pass.
- [ ] Security suite pass.
- [ ] Load smoke pass.
- [ ] Mobile release candidate installed on target devices.
- [ ] Rollback runbook executed once in staging.

## 22. P0 Completion Backlog

These slices are the remaining decision-complete backlog from the current port state to pilot-ready end-to-end production. Each slice must update OpenAPI/client, mobile/Ops surfaces, tests, route matrix, and readiness checklist when it changes public behavior.

| Slice | Scope | Dependencies | Acceptance gate |
|---|---|---|---|
| P0-01 Auth/profile/device/support completion | Invite-code signup gate, auth exists, logout-all, profile/vehicles, sessions, password change, forgot-password support request, notification preferences, max 3 accounts per device, ops user reset/manual support flow | Phase 1 auth foundation | API tests pass; mobile O1/O2/C9 screens are data-wired; ops user reset writes audit; fraud/device tests cover allow, deny, and manual reset |
| P0-02 Merchant onboarding/admission/eKYC go-live | Backend/API and basic mobile/Ops wiring are complete for merchant application, photo confirmation, eKYC CMND/selfie/bank object keys, payment setup/verification, approve/reject/suspend, go-live guard, audit, and admission RLS. Remaining: admission scoring, real storage policy, offline/native uploads, and Playwright journey. | Storage policy spike; Ops auth | Merchant cannot go live until checklist passes; Ops admissions Playwright flow passes; audit rows written for every state change |
| P0-03 Booking/payment/evidence end-to-end | Backend and local mobile/Ops route closure now covers active booking list, arrived ping, no-show/deposit after repeated no-shows, replay-safe payment denial/switch/cash, evidence presign/confirm with local file queue fallback, ops fallback booking/check-in/evidence/payment confirmation, and local API smoke execution. Remaining: Maestro booking/payment/evidence smoke and physical camera/QR/GPS checks. | Core booking/payment/evidence APIs | API integration covers state machine; Maestro booking/payment/evidence smoke passes; physical camera/QR/GPS tests pass on iOS and Android |
| P0-04 Promo/reward/referral completion | Golden Hour table/API, ops voucher mint, voucher reserve/redeem action wiring, referral share action wiring, and local API smoke coverage are implemented locally. Remaining: mobile Golden Hour surface, promo stacking rules, reward C10/C11/C12 Maestro flow, and referral reward issuance from invite first-touch attribution. | Promo/reward/referral backend | Promo 5 stacking cases pass; reward/referral integration tests pass; C10/C11/C12 Maestro flow passes |
| P0-05 Mobile parity completion | Generated-client primary actions, `/v1/auth/me` merchant context, local native adapters, and completed-row route coverage references are wired. Remaining: full Vietnamese UX polish, deep-link/maps resume validation, Maestro iOS/Android smoke, and physical-device native checks. | P0-01 through P0-04 APIs | Route matrix has no P0 mobile gaps; `mobile.route-files.check`, typecheck, Maestro iOS/Android smoke, and physical-device native checks pass |
| P0-06 Ops web completion | Ops UI wiring now covers fallback actions, export creation/status, complaint resolution/voucher minting, commission export, and audit search. Remaining: audit detail, richer reconciliation UI, and Playwright journeys. | P0-02 through P0-04 backend | Route matrix has no P0 Ops gaps; Playwright Ops journeys pass; CSV/data-room totals reconcile; all mutations write audit rows |
| P0-07 Realtime/storage/worker completion | Local worker ledger, scheduled stale-hold expiry, processed-domain-event records, bounded retry exhaustion, and visible dead-letter rows are implemented and tested. Remaining: Supabase private Broadcast policies, storage bucket policies, realtime token refresh, polling fallback, advisory-lock hardening, and crash/redeploy catch-up rehearsal. | Supabase credentials and schema freeze | Supabase readiness passes; realtime authorization negative tests pass; worker recovery tests prove no duplicate effects and visible dead letters |
| P0-08 Migration/cutover/production readiness | Fly.io API/worker deploy pipeline, static Ops deployment, feature-flagged API origin, PgBouncer dual pool, backup/restore rehearsal, dashboards/alerts, 48h staging soak, load/security smoke, rollback runbook | P0-01 through P0-07 | Cutover gate passes; 20+ synthetic bookings show no state divergence; rollback runbook executed once in staging |

Backlog rules:
- A slice is not done until its API, UI, worker/realtime impact, route matrix, tests, and readiness checklist entries are updated together.
- Thin implementations are acceptable only when the PRD journey works, the data model is auditable, and the production rollback path is clear.
- Any newly discovered P0 PRD gap must be assigned to one of the eight slices before implementation starts.

## 23. Workstream Parallelization

| Lane | Scope | Dependencies |
|---|---|---|
| A | OpenAPI, DB, auth, RLS, core backend | none after Phase 0 starts |
| B | Expo shell, Tamagui, auth session, generated client | OpenAPI draft |
| C | Consumer mobile flows | Expo shell, core marketplace APIs |
| D | Merchant mobile flows | Expo shell, merchant/booking/payment APIs |
| E | Ops web | generated client, ops routes |
| F | Realtime/worker | DB schema and domain events |
| G | Migration/test/observability | DB schema and deploy target |

Rules:
- Booking/payment/evidence service work should be sequential inside backend to avoid state-machine conflicts.
- Consumer and merchant mobile can run in parallel after shared shell and components are frozen.
- Ops web can run independently once generated client exists.
- QA builds fixtures continuously, not at the end.

## 24. Production Readiness Checklist

Backend and API contract:
- [ ] OpenAPI v1 frozen for every P0 route.
- [x] Generated clients compile after OpenAPI generation.
- [x] All 103 current contract routes have real FastAPI handlers; no P0 contract route remains mounted as `NOT_IMPLEMENTED`.
- [x] Auth refresh rotation implemented.
- [x] Refresh-token reuse detection implemented.
- [ ] Role middleware and tenant checks cover every P0 route.
- [x] DB RLS enabled and tested for production tenant tables.
- [x] P0 auth/profile/device/support API routes implemented for invite-gated signup, auth exists, logout-all, forgot-password support request, profile, vehicles, sessions, password change, notification preferences, notification token registration, data export, account deletion/cancel, ops users, and ops password reset.
- [x] P0 merchant admission API routes implemented for application, photo, payment setup, eKYC submissions/status, pending list, payment recipient verification, approve/reject/suspend, go-live guard, audit, and admission RLS.
- [x] Local route-closure APIs implemented for my bookings, arrived ping, merchant calendar/maintenance/Golden Hour, ops data-room/exports, ops fallback booking/check-in/evidence/payment confirmation, and ops reward voucher.
- [ ] Idempotency implemented for booking, payment, evidence, promo, reward, referral, complaint, and ops fallback mutations.
- [x] Domain events are locally idempotent, retryable, and covered by `processed_domain_events` per consumer.
- [x] Worker scheduler ledger records local scheduled stale-hold job runs.
- [ ] Worker advisory locks, bounded retries, dead-letter visibility, and ops review paths are tested.

Consumer product parity:
- [x] O1/O2 backend: invite code, auth exists, signup/login/logout-all, device cap, and support reset request implemented with integration tests.
- [ ] O1/O2 onboarding: invite code, auth exists, signup/login/logout-all, device cap, support reset request, loading/error/offline/forbidden states, and Maestro smoke.
- [ ] C1/C3 discovery: nearby/search/service-template APIs wired to mobile, stale merchant exclusion, empty/error/offline states, and E2E coverage.
- [x] C4/C5 local booking wiring: hold, active booking, cancel, QR/manual fallback check-in, no-show/deposit states, and state-surface coverage references are implemented; E2E runner execution remains open.
- [x] C6 local payment wiring: QR, cash, user-claimed, merchant-confirmed, merchant-denied, switch-method, and idempotent replay are implemented; E2E runner execution remains open.
- [x] C7 local evidence/rating wiring: camera adapter, file queue, presign/confirm/retry fallback, and binary rating are implemented; physical-device coverage remains open.
- [x] C9 backend/profile read surface: profile, vehicles, sessions, password change, data export/delete/cancel-delete, notification preferences, token registration, and mobile profile data read are implemented with integration/typecheck coverage.
- [ ] C9 full mobile parity: profile edit, vehicle edit, session revoke, data export/delete/cancel-delete actions, notification preference edit states, offline/forbidden UX, and Maestro coverage.
- [ ] C10/C11/C12 rewards: progress, vouchers, reserve/release/redeem and referral share are wired locally; celebration polish, referral reward issuance, and Maestro coverage remain open.

Merchant product parity:
- [x] MO1-MO4 backend/API and basic mobile wiring: application, photo confirmation, eKYC CMND/selfie/bank object-key submission, payment setup, go-live checklist guard, loading/error/forbidden states, and integration/typecheck coverage.
- [ ] MO1-MO4 production UX: real storage upload, offline upload queue, physical camera/GPS checks, admission scoring, and Maestro/Playwright journey coverage.
- [x] M1 local queue/calendar wiring: queue API, `/v1/auth/me` merchant context, calendar, maintenance, and polling reads are implemented; realtime refresh and E2E coverage remain open.
- [x] M2 local service execution wiring: check-in, start, complete, payment confirmation/denial surfaces, fallback code display, and replay-safe transition tests are implemented; physical/E2E coverage remains open.
- [ ] M4 summaries/services: daily summary response/CSV, Golden Hour API, merchant service CRUD, custom service review/resubmit, and price history are implemented; mobile/Ops Golden Hour surfaces and stale-service guard remain open.

Ops and support parity:
- [x] Audit log exists for every implemented ops state change.
- [x] Admissions/payment-recipient/eKYC approve-reject-suspend backend and Ops-web mutation wiring write audit rows.
- [ ] Admissions/payment-recipient/eKYC approve-reject-suspend journeys pass Playwright.
- [x] Complaints triage shows SLA, refund/voucher decision surface, resolution action, and audit-backed backend mutation.
- [x] Finance/commission CSV, export creation/status, and local data-room APIs have integration coverage and Ops UI action wiring; Playwright evidence remains open.
- [x] Ops fallback booking, check-in, evidence upload, payment confirmation, user creation, password reset, exports, data-room export job creation, and reward voucher minting are implemented and audited.
- [x] Ops user list/create/reset-password backend is implemented; reset-password writes audit and revokes active refresh tokens.
- [ ] Manual support runbook covers password reset, device-cap reset, weak evidence review, payment dispute, refund/voucher, and merchant suspension.

Realtime, storage, and native reliability:
- [ ] Supabase private Broadcast policies pass positive and negative tenant/user/merchant/ops authorization tests.
- [ ] Supabase Storage buckets and signed upload confirmation pass local and Supabase readiness checks.
- [ ] Realtime token refresh and polling fallback are tested for consumer, merchant, and ops channels.
- [ ] SecureStore token handling is tested.
- [ ] Camera, QR scanner, GPS allow/deny/fallback, file queue, and push token registration have local adapters; push receipt, deep links, maps resume, and physical-device checks on iOS and Android remain open.
- [ ] Offline evidence and payment mutation queues replay safely after app restart and network recovery.

Data, migration, and cutover:
- [x] Table migration map exists for the legacy 37-table schema.
- [x] Seed manifest/checker exists.
- [x] Local QA fixture seed, gitignored token artifact, and local E2E runbook exist for Docker Postgres/FastAPI/Ops/Mobile verification.
- [x] Shadow-read dry-run harness exists.
- [x] Migration dry-run planner exists.
- [ ] Production migration dry-run passes against staging data with checksums.
- [ ] Restore-from-backup rehearsal completes and is documented.
- [ ] Historical completed bookings reconcile against payments, ratings, rewards, complaints, and commission exports.
- [ ] PgBouncer dual-pool architecture is configured for app traffic and migration/admin bypass traffic.
- [ ] Slot pre-seeding and retention sweep jobs are implemented.

Observability and release:
- [x] Structured JSON logs with request ID implemented.
- [x] `/healthz`, `/readyz`, and `/metrics` implemented.
- [ ] Sentry Python, React Native, and Ops web projects are configured.
- [ ] Alerts cover API error rate, p95 latency, worker lag, failed evidence jobs, failed payment confirmations, queue backlog, and realtime auth failures.
- [ ] Force-update and feature-flag endpoints are production-configured for API-origin rollback.
- [ ] Release dashboard exists for launch week.
- [ ] 48h staging soak, 20+ synthetic bookings, security smoke, load smoke, mobile RC install, and rollback rehearsal all pass.

## 25. First Tickets

| # | Status | Ticket | Owner lane | Dependency | Acceptance gate |
|---|---|---|---|---|---|
| 1 | [x] Backend/API done; Maestro/full mobile actions remain in P0-05 | Implement invite-gated signup, auth exists, logout-all, forgot-password support request, sessions, and password change | A/B/C/E | Existing auth foundation | API tests pass; O1/O2/C9 screens are wired; ops reset writes audit |
| 2 | [x] Backend/API done; explicit blocked mobile state remains in P0-05 | Add device registration and max 3 accounts per device with ops/manual reset path | A/C/E | Ticket 1 | Fraud tests cover allow, deny, and reset; mobile shows blocked state |
| 3 | [x] Backend/API and profile read surface done; physical push receipt remains in P0-05/P0-07 | Complete notification preferences and push token registration | A/C/F | Ticket 1 | Preferences API, mobile settings, push token persistence, and typecheck pass |
| 4 | [x] Backend/API and basic mobile/Ops wiring done; storage/native/Playwright remain in Tickets 5, 7, 9, 10 | Complete merchant onboarding, photo, eKYC, bank/payment setup, and go-live checklist | A/D/E | Storage policy spike | Merchant cannot go live until checklist passes; admission RLS and audit tests pass |
| 5 | [ ] Blocked on credentials | Implement Supabase Storage bucket policies and evidence/merchant upload confirmation against Supabase readiness env | A/D/F | Supabase credentials | Storage positive/negative policy tests pass; upload confirmation works |
| 6 | [x] Local backend/mobile/Ops done; Maestro/physical E2E remains | Complete booking no-show, deposit, rated state, payment merchant-denied, switch-method, and cash-record UX flows; backend fallback booking/check-in/evidence/payment confirmation routes are already implemented | A/C/D | Core booking/payment APIs | State-machine integration tests pass; Maestro booking/payment smoke remains before production closure |
| 7 | [ ] Local adapters done; physical checks open | Implement mobile camera/QR/GPS/deep-link/file-queue native lane | C/D | Tickets 5 and 6 | Physical iOS/Android checks pass; offline evidence replay is idempotent |
| 8 | [ ] Local voucher/referral actions done; stacking/issuance open | Complete promo stacking, Golden Hour mobile surface, voucher reserve/release/redeem, and referral reward issuance | A/C | Promo/reward backend | Promo 5 stacking tests, reward/referral tests, and C10/C11/C12 Maestro pass |
| 9 | [ ] Local primary actions and state coverage refs done; Maestro/UX polish open | Replace remaining P0 mobile route shells with generated-client data and full UI states | C/D | Tickets 1-8 route APIs | Route matrix has no P0 mobile gaps; Maestro smoke passes on iOS/Android |
| 10 | [ ] Local Ops UI wiring done; Playwright/audit detail open | Complete Ops UI wiring for fallback actions, data room, exports, audit search/detail, complaints, and admissions journeys | E/A | Tickets 1, 4, 6, 8 | Playwright Ops journeys pass; CSV/data-room totals reconcile; all mutations audited |
| 11 | [ ] Open | Implement Supabase private Broadcast policies, realtime token refresh, and polling fallback | F/A/C/D/E | Supabase credentials; core route wiring | Positive and negative realtime authorization tests pass for consumer, merchant, and ops |
| 12 | [ ] Local ledger/retry/dead-letter done; advisory-lock/catch-up rehearsal open | Upgrade worker from drain skeleton to durable scheduler with ledger, locks, retries, dead letters, and catch-up | F/A | Domain event schema | Worker recovery tests pass; dead letters visible to Ops |
| 13 | [ ] Open | Configure Fly.io API/worker deploy, static Ops deploy, PgBouncer dual pool, and API-origin feature flag | G/A/E | P0 route freeze | Staging deploy pipeline and rollback switch pass |
| 14 | [ ] Open | Run migration/cutover rehearsal: staging migration, seed, shadow-read, restore, synthetic bookings, load/security smoke | G/QA | Tickets 1-13 | Cutover gate passes with documented rollback evidence |
| 15 | [ ] Open | Finalize production observability: Sentry, dashboards, alerts, launch-week release dashboard, and support runbook | G/E | Tickets 10-14 | Alert checks fire in staging; support runbook covers all manual fallback paths |

## 26. Locked P0 Decisions

| Decision | Locked P0 choice | Implementation constraint | Owner |
|---|---|---|---|
| Push provider | Expo Push Service | Direct APNs/FCM is P1 unless Expo limits block pilot requirements | Mobile/backend |
| Deploy target | Fly.io for API and worker; Supabase Singapore for Postgres, Realtime, and Storage; static hosting from the selected deploy pipeline for Ops web | API and worker image tags include git SHA; mobile API origin can roll back through feature flags | Tech lead |
| Auth owner | FastAPI owns auth | Supabase Realtime only verifies short-lived FastAPI-issued JWTs with tenant/user/merchant/ops-scope claims | Backend |
| E2E runner | Maestro for mobile, Playwright for Ops web | Release is blocked if required P0 flows fail | QA |
| UI library | Tamagui mobile, shadcn/Radix-style Ops web | Generated client is the shared API boundary; no hand-written duplicate service clients | Frontend |
| RLS launch stance | DB RLS is required for production cutover | App-role and bypass/admin paths are separate and tested | Backend/security |
| P0 search | Merchant-only PostGIS + pg_trgm | `type=place` remains a P1 placeholder until pilot quality requires it | Backend |

P1 defaults:
- Search upgrade: evaluate Meilisearch/place search only after P0 pilot metrics show merchant-only search is insufficient.
- Push upgrade: evaluate direct APNs/FCM only if Expo Push Service fails latency, deliverability, or compliance needs.

## 27. Source References

Local:
- `/Users/minhlt/Downloads/Projects/TASCO/09-product-requirements-document.md`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/generated/migrations/V001__init.sql`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/apps/foundation/api/src/main/kotlin/app/map/api/booking/PostgresBookingService.kt`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/apps/foundation/api/src/main/kotlin/app/map/api/payment/PostgresPaymentService.kt`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/apps/foundation/api/src/main/kotlin/app/map/api/auth/PostgresAuthStores.kt`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/apps/foundation/api/src/main/kotlin/app/map/api/evidence/EvidenceService.kt`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/apps/foundation/api/src/main/kotlin/app/map/api/RlsContext.kt`
- `/Users/minhlt/Downloads/Projects/TrueCare/truecare/apps/foundation/api/src/main/kotlin/app/map/api/RlsTransaction.kt`

External docs checked:
- FastAPI async tests: https://fastapi.tiangolo.com/advanced/async-tests/
- SQLAlchemy session basics: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
- SQLAlchemy asyncio: https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html
- Supabase Realtime authorization: https://supabase.com/docs/guides/realtime/authorization/
- Supabase Broadcast: https://supabase.com/docs/guides/realtime/broadcast/
- Expo Camera: https://docs.expo.dev/versions/latest/sdk/camera/
- Expo FileSystem: https://docs.expo.dev/versions/latest/sdk/filesystem/
- Expo ImageManipulator: https://docs.expo.dev/versions/latest/sdk/imagemanipulator/
- Expo SecureStore: https://docs.expo.dev/versions/latest/sdk/securestore/
- Expo Notifications: https://docs.expo.dev/versions/latest/sdk/notifications/
- Expo BackgroundTask: https://docs.expo.dev/versions/latest/sdk/background-task/
- TanStack Query persistence: https://tanstack.com/query/v5/docs/framework/react/plugins/persistQueryClient
- Tamagui introduction: https://tamagui.dev/docs/intro/introduction
- Tamagui Expo guide: https://tamagui.dev/docs/guides/expo
- Maestro React Native: https://docs.maestro.dev/platform-support/react-native
- PostgreSQL pg_trgm search: https://www.postgresql.org/docs/current/pgtrgm.html
