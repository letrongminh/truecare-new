# Route Test Matrix v1

Canonical coverage matrix for `docs/port-plan.md` Section 14.

This file is the CI-enforced source for route-level coverage. Keep it in lock-step with the route manifest. A route is not implementation-complete until its matrix row has stable test IDs, required UX states, test files, and owner.

## CI Checker Contract

Command: `make route-test-matrix.check`

The checker must fail when:
- A mandatory route in `docs/port-plan.md` Section 14 has no row here.
- A row here references a route no longer present in the manifest.
- A row is missing `testIDPrefix`, owner, or required states.
- An H/VH mobile screen lacks a Maestro flow.
- An Ops route lacks a Playwright flow.
- Required states omit loading, empty, error, offline, forbidden, or retry unless the row has an explicit waiver.
- Referenced test files do not exist.

## Required States

Every mandatory route must define behavior for:
- loading
- empty
- error
- offline
- forbidden
- retry

## Matrix

| PRD ID | Persona | Route | Complexity | testIDPrefix | Unit/screen tests | E2E tests | Required states | Owner | Status |
|---|---|---|---|---|---|---|---|---|---|
| O1-Final | Consumer | `app/(auth)/signup.tsx` | M | `auth-signup` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| O2-Final | Consumer | `app/(auth)/quick-profile.tsx` | S | `quick-profile` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C1 | Consumer | `app/(consumer)/home.tsx` | H | `consumer-home` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C3 | Consumer | `app/(consumer)/merchant/[id].tsx` | VH | `merchant-detail` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C4 | Consumer | `app/(consumer)/booking/[id].tsx` | VH | `booking-detail` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C5-Final | Consumer | `app/(consumer)/checkin/[id].tsx` | M | `checkin` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C6-Final | Consumer | `app/(consumer)/payment/[id].tsx` | H | `payment` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C7 | Consumer | `app/(consumer)/evidence/[id].tsx` | H | `evidence` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C9 | Consumer | `app/(consumer)/profile/index.tsx` | M | `profile` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C10 | Consumer | `app/(consumer)/rewards/index.tsx` | M | `rewards` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C11 | Consumer | `app/(consumer)/rewards/redeem.tsx` | M | `reward-redeem` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| C12 | Consumer | `app/(consumer)/rewards/celebration.tsx` | S | `reward-celebration` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| MO1-Final | Merchant | `app/(merchant-onboarding)/signup.tsx` | M | `merchant-signup` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| MO2-Final | Merchant | `app/(merchant-onboarding)/shop-info.tsx` | M | `merchant-shop-info` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| MO3-Final | Merchant | `app/(merchant-onboarding)/photos-services.tsx` | VH | `merchant-photos-services` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| MO4-Final | Merchant | `app/(merchant-onboarding)/payment-setup.tsx` | H | `merchant-payment-setup` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| M1 | Merchant | `app/(merchant)/queue/index.tsx` | VH | `merchant-queue` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| M2 | Merchant | `app/(merchant)/slots/index.tsx` | H | `merchant-slots` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| M4 | Merchant | `app/(merchant)/summary/index.tsx` | M | `merchant-summary` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| M-Service | Merchant | `app/(merchant)/bookings/[id].tsx` | H | `merchant-booking` | TODO | TODO Maestro | loading, empty, error, offline, forbidden, retry | Mobile | TODO |
| OPS-1 | Ops | `apps/ops-web/src/routes/admissions` | H | `ops-admissions` | TODO | TODO Playwright | loading, empty, error, offline, forbidden, retry | Ops Web | TODO |
| OPS-2 | Ops | `apps/ops-web/src/routes/commission` | M | `ops-commission` | TODO | TODO Playwright | loading, empty, error, offline, forbidden, retry | Ops Web | TODO |
| OPS-3 | Ops | `apps/ops-web/src/routes/complaints` | H | `ops-complaints` | TODO | TODO Playwright | loading, empty, error, offline, forbidden, retry | Ops Web | TODO |
| OPS-4 | Ops | `apps/ops-web/src/routes/network-health` | M | `ops-network-health` | TODO | TODO Playwright | loading, empty, error, offline, forbidden, retry | Ops Web | TODO |
| OPS-5 | Ops | `apps/ops-web/src/routes/growth-ekyc` | M | `ops-growth-ekyc` | TODO | TODO Playwright | loading, empty, error, offline, forbidden, retry | Ops Web | TODO |

## Waivers

No waivers yet. A waiver must include route, omitted state, reason, owner, expiry date, and replacement coverage.

## Cross-Route Scenario Matrices

### Payment Transitions

Payment coverage spans API state, consumer UI, merchant UI, ops dispute handling, realtime/polling, and reward finalization.

Required cases:
- QR `pending -> initiated_qr -> user_claimed -> verified`.
- Cash `pending -> cash_offered -> verified`.
- `user_claimed -> merchant_denied -> initiated_qr` retry.
- `user_claimed -> merchant_denied -> cash_offered -> verified`.
- `initiated_qr/user_claimed/cash_offered -> disputed`.
- Any non-terminal payment -> cancelled when booking is cancelled or expired.
- Replay of user-claimed, merchant-confirmed, merchant-denied, cash-record, and switch-method is idempotent.
- Invalid transitions return registered Problem Details errors and leave state unchanged.
- Reward stamp remains pending until booking reaches completed; no reward finalizes on merchant denial.
- Ops dispute/audit context includes payment event history and enough actor/timestamp detail for support review.

Required tests:
- Backend property tests for allowed/forbidden transitions.
- Backend integration tests for each endpoint and idempotent replay.
- Maestro consumer flow for denial, retry QR, and switch-to-cash recovery.
- Maestro merchant flow for denial, cash record, and confirm replay.
- Ops Playwright flow for disputed payment review and audit trail.

### Realtime And Offline Lifecycle

Realtime/offline coverage spans Expo app state, persisted local mutations/files, SecureStore tokens, Realtime JWTs, polling fallback, and server idempotency.

Required cases:
- Realtime token expires while subscribed; client refreshes token or falls back to polling without losing current booking/payment state.
- Reconnect preserves event ordering or refetches authoritative state when gaps are detected.
- Background -> foreground invalidates active booking, merchant queue, payment, and reward queries.
- App kill/reopen retains pending evidence local file references and flushes upload after reconnect.
- App kill/reopen retains pending payment user-claimed mutation and flushes exactly once.
- Offline evidence retry reaches retry exhaustion and marks ops review needed.
- Offline payment replay returns the same idempotent server response and does not duplicate payment events.
- Polling fallback updates UI after simulated Supabase disconnect for booking, merchant queue, reward, and ops topics.

Required tests:
- Maestro lifecycle flows for background/foreground and kill/reopen.
- Maestro airplane-mode flows for evidence capture/upload and payment user-claimed queue.
- Backend integration tests for replay safety of queued mutations.
- Realtime authorization tests for expired token, wrong tenant, wrong merchant, and missing scope.
- Route-level tests assert stale banners and retry actions are visible when fallback polling is active.
