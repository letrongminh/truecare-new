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

Status last updated: 2026-05-17.

Completed slices:
- [x] Foundation scaffold: FastAPI API, Expo shell, Ops web shell, OpenAPI export, generated TypeScript client, migration map, route-test-matrix gate, and local Makefile gates.
- [x] Backend foundation POC: SQLAlchemy async session, Alembic baseline, auth signup/login/refresh/logout/me, RBAC dependencies, tenant context, RLS proof table, idempotency service, domain events repository, worker drain skeleton, and local Docker Postgres commands.

Current verification:
- [x] `make infra-prereqs.check`
- [x] `make secret-leak.check`
- [x] `make route-test-matrix.check`
- [x] `make db.up`
- [x] `make db.migrate`
- [x] `make api.test`
- [x] `make api.integration`
- [x] `make client.generate`
- [x] `make worker.once`
- [ ] `make supabase-readiness.check` after real Supabase credentials, `psql`, and `jq` are available.
- [ ] JavaScript workspace install/typecheck after `pnpm` is enabled.

### Phase 0 - Production Design Freeze

Duration: 5-7 days.

Deliverables:
- [x] OpenAPI v1 contract skeleton and generated clients.
- [x] Route manifest and testID convention via `knowledge/00-porting/route-test-matrix-v1.md`.
- [x] UI system decision and shell primitives for Expo and Ops web shells.
- [x] Auth/RBAC/RLS spec and proof-of-concept implementation.
- [ ] Rate-limit spec implementation.
- [ ] Booking concurrency spike.
- [ ] Offline/evidence queue spike.
- [ ] Realtime private channel policy spike.
- [x] Migration map for legacy 37-table schema.
- [ ] Seed plan.
- [x] Test infrastructure skeleton for API unit/integration gates.

Exit gate:
- [x] Runner choice, UI library, RLS stance, and route manifest are no longer blocked for the first scaffold.
- [ ] Booking, evidence, realtime, seed, and production rate-limit spikes remain before Phase 0 is fully closed.

### Phase 1 - Backend Foundation

Duration: 1.5-2 weeks.

Build:
- [x] FastAPI skeleton.
- [x] Alembic baseline.
- [x] SQLAlchemy async engine/session.
- [x] Request ID middleware.
- [x] RFC 9457 error envelope and registered typed errors.
- [ ] Structured JSON logging.
- [x] Auth with refresh rotation.
- [x] Refresh-token reuse detection.
- [x] RBAC dependencies: `require_user`, `require_role`, `require_tenant`.
- [x] RLS tenant context through `SET LOCAL`.
- [ ] Production rate limiter.
- [x] Idempotency service keyed by tenant, subject, and key with body-hash mismatch handling.
- [x] Domain events table and repository.
- [x] Worker skeleton with domain-event claim/drain no-op.
- [x] Health/readiness/metrics endpoints.
- [x] Local Docker Postgres commands: `db.up`, `db.down`, `db.migrate`.

Exit gate:
- [x] Auth/security integration suite passes.
- [x] DB RLS proof test passes for the first RLS table.
- [x] Generated client is regenerated from OpenAPI.
- [ ] Rate-limit tests pass.
- [ ] Structured logging checks pass.
- [ ] RLS coverage expands from proof table to production tenant tables.

### Phase 2 - Core Marketplace Loop

Duration: 2-3 weeks.

Build:
- [ ] Merchant discovery and detail.
- [ ] Service templates and merchant services.
- [ ] Slot capacity and booking hold lifecycle.
- [ ] Merchant queue APIs.
- [ ] Check-in QR/manual code.
- [ ] Evidence presign/confirm/process.
- [ ] Payment QR/cash/user-claimed/merchant-confirmed.
- [ ] Rating.
- [ ] Realtime events and polling fallback.

Exit gate:
- [ ] Full core loop passes API integration and Maestro smoke.
- [ ] Concurrent hold tests pass.
- [ ] Payment idempotency tests pass.
- [ ] Evidence retry tests pass.

### Phase 3 - Retention, Promo, Complaints, Ops Support

Duration: 2-3 weeks.

Build:
- [ ] Promo code validation with 8 cases and stacking rules.
- [ ] Reward stamp/voucher lifecycle with budget cap.
- [ ] Referral tracking and sharing links.
- [ ] Complaint submission, SLA, ops resolution, refund/voucher decision.
- [ ] Merchant custom service review/resubmit.
- [ ] Merchant price history.
- [ ] Daily summary CSV.
- [ ] Commission receivable export.

Exit gate:
- [ ] Reward C10/C11/C12 flows pass.
- [ ] Referral attribution tests pass.
- [ ] Complaint ops workflow passes.
- [ ] Promo stacking tests pass.

### Phase 4 - Expo Mobile Parity

Duration: 4-6 weeks, parallelizable after Phase 0 and backend contract freeze.

Build lanes:
- [x] Mobile shell scaffold: Expo Router app shell.
- [ ] Tamagui primitives.
- [ ] Auth store.
- [ ] Generated client integration in app runtime.
- [ ] Query client.
- [ ] Offline queue.
- [ ] Consumer lane: O1/O2/C1/C3/C4/C5/C6/C7/C9/C10/C11/C12.
- [ ] Merchant lane: MO1-MO4/M1/M2/M4/M-Service.
- [ ] Native capability lane: camera, QR, GPS, SecureStore, push, deep links, file queue.

Exit gate:
- [ ] All mandatory route manifest rows have loading/error/offline/forbidden states.
- [ ] Maestro smoke passes on iOS and Android.
- [ ] Physical-device camera/push/GPS tests pass.

### Phase 5 - Ops Web

Duration: 1-2 weeks.

Build:
- [x] Ops web scaffold: Vite React shell.
- [ ] Ops auth/RBAC.
- [ ] Admissions queue and detail.
- [ ] Payment recipient verification.
- [ ] Commission export.
- [ ] Complaint triage/refund/voucher decision.
- [ ] Network health/fallback actions.
- [ ] Growth/eKYC review and merchant pipeline.
- [ ] Audit log views.

Exit gate:
- [ ] Playwright ops journeys pass.
- [ ] Exports return correct CSV headers and totals.
- [ ] Ops actions write audit log.

### Phase 6 - Migration, Soak, Cutover

Duration: 1-2 weeks.

Build:
- [ ] Migration script with dry-run mode.
- [ ] Seed scripts.
- [ ] Shadow-read compare harness.
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

## 22. Workstream Parallelization

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

## 23. Production Readiness Checklist

Product parity:
- [ ] Consumer onboarding O1/O2 complete.
- [ ] Consumer discovery C1/C3 complete.
- [ ] Booking C4/C5 complete with QR and fallback code.
- [ ] Payment C6 complete with QR/cash and merchant confirmation.
- [ ] Evidence/rating C7 complete.
- [ ] Profile C9 complete.
- [ ] Reward C10/C11/C12 complete.
- [ ] Merchant onboarding MO1-MO4 complete.
- [ ] Merchant queue/service/summary M1/M2/M4 complete.
- [ ] Merchant service execution complete.
- [ ] Ops admissions, finance, complaints, network health, growth/eKYC complete.

Backend safety:
- [ ] OpenAPI v1 frozen.
- [ ] Generated clients compile.
- [ ] Auth refresh rotation implemented.
- [ ] Token theft detection implemented.
- [ ] Role middleware covers every route.
- [ ] DB RLS enabled and tested for production tenant tables.
- [ ] Idempotency implemented for booking/payment/evidence/promo/reward mutations.
- [ ] Domain events are idempotent and retryable.
- [ ] `domain_events` / `processed_domain_events` contract covers async side effects and per-consumer idempotency.
- [ ] Worker scheduler ledger records every scheduled job run and supports catch-up after crash/redeploy.
- [ ] Worker has advisory locks and dead-letter handling.

Data and migration:
- [ ] Table mapping approved.
- [ ] Seed scripts approved.
- [ ] Shadow-read harness implemented.
- [ ] Migration dry-run clean.
- [ ] Restore-from-backup rehearsal complete.
- [ ] Historical completed bookings reconcile against payments/ratings/rewards.

Mobile reliability:
- [ ] SecureStore token handling tested.
- [ ] Camera and QR tested on physical devices.
- [ ] GPS allowed/denied/fallback tested.
- [ ] Offline evidence queue tested.
- [ ] Payment offline mutation queue tested.
- [ ] Deep links and maps resume tested.
- [ ] Push notification token registration and receive behavior tested.

Ops and support:
- [ ] Audit log for every ops state change.
- [ ] Manual fallback actions implemented.
- [ ] Complaint SLA visible.
- [ ] Commission CSV verified.
- [ ] Data export/delete account jobs verified.
- [ ] Support runbook written.


Additional production gates:
- [ ] `notification_preferences`, merchant phone, golden hours, and support requests modeled.
- [ ] Discovery scoring formula verified against stale merchant exclusion.
- [ ] Referral rewards use invite-code first-touch attribution.
- [ ] Payment merchant-denied flow implemented.
- [ ] Rating endpoint is binary and idempotent.
- [ ] Daily summary, commission export, and data room fields verified.
- [ ] P0 password reset creates ops support request.
- [ ] Max 3 accounts per device fraud rule enforced.
- [ ] Reward, merchant admission, and commission state machines covered by integration tests.
- [ ] `no_show` and `rated` booking states implemented and migrated.
- [ ] Search endpoint uses PostGIS + pg_trgm for P0.
- [ ] Promo 8 validation cases and 5 stacking rules implemented.
- [ ] Service mode tag enforcement and stale merchant detection implemented.
- [ ] Force update and feature flags endpoints implemented.
- [ ] Account deletion cancel window and data export bundle verified.
- [ ] Backend i18n message bundles enforced.
- [ ] PgBouncer dual-pool architecture configured.
- [ ] Slot pre-seeding and retention sweep jobs implemented.

Observability:
- [ ] Sentry Python and React Native configured.
- [ ] Structured JSON logs with request ID.
- [ ] `/healthz`, `/readyz`, `/metrics` implemented.
- [ ] Alerts for API error rate, p95 latency, worker lag, failed evidence jobs, failed payment confirmations, queue backlog.
- [ ] Release dashboard for launch week.

## 24. First Tickets

1. Create OpenAPI v1 skeleton and generated TypeScript client pipeline.
2. Create `docs/migration-map-v1.md` with all 37 current tables.
3. Create Expo route manifest tickets from Section 14.
4. Implement backend auth/RBAC/RLS proof of concept with one protected route and one RLS table.
5. Implement booking hold transaction spike against current `slot_capacity` shape.
6. Implement mobile offline evidence queue spike using `expo-camera`, `expo-image-manipulator`, and `expo-file-system`.
7. Convert top 10 Maestro flows to new route/testID selectors.
8. Add Supabase private Broadcast policy spike for `booking:user:{user_id}`.
9. Add migration dry-run command and staging seed data.
10. Add k6/Locust smoke for nearby and booking hold.
11. Implement version check and feature flags endpoints.
12. Implement PostGIS + pg_trgm search endpoint.
13. Implement account deletion cancel window and export bundle.
14. Implement promo validation matrix and stacking rules.
15. Configure PgBouncer dual-pool deployment.
16. Implement notification preferences and support reset request table.
17. Implement merchant-denied payment flow.
18. Implement daily summary response/CSV and ops data room sections.
19. Implement referral reward rules using invite-code first-touch attribution.
20. Implement signup device cap and manual password reset flow.

## 25. Remaining Decisions

| Decision | Recommended answer | Owner |
|---|---|---|
| Push provider | Expo Push Service for pilot; direct APNs/FCM only if Expo limits block requirements | Mobile/backend |
| Deploy target | Fly/Render/Railway for API+worker; managed Postgres/Supabase for DB/realtime/storage | Tech lead |
| Auth owner | FastAPI owns auth; Supabase Realtime uses short-lived app-issued JWTs with tenant/user/merchant/ops-scope claims | Backend |
| E2E runner | Maestro for mobile, Playwright for Ops web | QA |
| UI library | Tamagui mobile, shadcn/Radix Ops web | Frontend |
| RLS launch stance | DB RLS required for production cutover | Backend/security |
| P1 search upgrade | Keep P0 merchant-only PostGIS + pg_trgm; add Meilisearch/place search only if pilot quality requires it | Backend |

## 26. Source References

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
