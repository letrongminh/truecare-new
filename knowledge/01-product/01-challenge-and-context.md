# 01 — TrueCare Source of Truth

> Consolidated source of truth for TrueCare business challenge, business strategy, and operations playbook.
> Supersedes the old split across challenge, strategy, and operations files.
> Last updated: 2026-04-26.

---

## 0. Executive Decision

TrueCare is not a car-wash booking app. It is an intelligence-led merchant operating layer for Tasco/VETC's car-care network, starting with car wash because wash is frequent, low-risk, easy to prove, and naturally fits route-triggered demand.

The funded MVP is the lean baseline in `07-business-proposal-en.md`:

- **P0 Evidence Pilot:** 12-20 curated merchants.
- **Invited users:** 300-800 VETC users.
- **Geography:** 1 primary route-dense cluster in Hanoi or HCMC.
- **Productized software:** 5 modules.
- **Human-operated workflows:** 4 workflows.
- **Build horizon:** 12 weeks after pre-code gates pass.

The objective is to prove one repeatable operating unit where VETC route context creates better timing, better trust, better completion, and better merchant discipline than the offline status quo.

If a task does not help prove that operating unit, it does not enter P0.

---

## 1. Business Challenge

### 1.1 What TrueCare Must Solve

TrueCare has to solve six layers at the same time:

1. **Supply standardization:** Thousands of independent wash shops have inconsistent process, quality, availability, and data discipline.
2. **Demand activation:** VETC has 4M+ users, but toll users do not automatically become car-care customers.
3. **O2O fulfillment:** Discovery, booking, check-in, payment, quality proof, and complaint handling must work as one loop.
4. **Operations at scale:** Tasco needs network health, SLA watch, quality governance, exception handling, and merchant discipline.
5. **Data moat:** Route behavior, timing, merchant performance, wait-time, evidence, ratings, complaints, and repeat behavior must create a closed feedback loop.
6. **Venture-scale path:** Wash is the wedge. The platform path is maintenance, detailing, tires, battery, rescue, parking, fuel, fleet, and other mobility services.

### 1.2 Strategic Context

Tasco/VETC has an unusual asset stack:

- 4.0-4.1M VETC users.
- 75% ETC market share in Vietnam.
- About 2M transactions/day across toll, parking, and fuel touchpoints.
- VETC Wallet migration completed in October 2025.
- GoongIO maps stack for route, geocode, ETA, and distance matrix.
- Tasco Auto / Savico / Carpla / VETC 24/7 Rescue as automotive operating leverage.
- Brand trust and payment rail that standalone wash startups do not have.

This means Tasco is not entering as another marketplace. It can connect demand, route context, payment, service evidence, and merchant governance in one system.

### 1.3 China Benchmark Lessons

The relevant China benchmarks are not visual UI references. They are operating mechanisms.

| Benchmark | Lesson for TrueCare |
|---|---|
| Tuhu | Wash/wax is an entry service. It creates service habit and opens cross-sell into higher-margin care. |
| Tmall Auto Care | Online traffic only matters when paired with store retention, guarantee, membership, and operating standards. |
| JD Jingchehui | Route/proximity coverage and standardized process beat generic marketplace discovery. |
| Yigoli | Unmanned/IoT wash is a possible future format, not the primary Tasco wedge. |
| Failed 2015-2016 wash O2O apps | Subsidy-led booking without workflow capture, quality control, or loyalty collapses when discounts stop. |

Five operating principles follow:

1. Winners sell trust, convenience, and standardization, not just wash.
2. Merchant-side control is as important as consumer UX.
3. Membership/retention and cross-sell path matter after the first loop is proven.
4. Route-aware recommendations beat generic nearby discovery.
5. The industry is moving toward chainization, digitalization, and lower-tier expansion, but growth before governance is dangerous.

For the VETC-native loyalty model, point redemption, campaign rules, and reconciliation behavior, see `09-product-requirements-document.md` Section 8 (VETC Loyalty Ecosystem Integration). TrueCare should inherit VETC Loyalty rather than create a separate point currency in P0.

### 1.4 Target Persona

Primary persona: **Anh Tuan**

- 35 years old, sales/business manager in Hanoi.
- Drives 30-50km daily.
- Car is a work tool. Clean car equals professional image.
- Current workflow: remember manually, drive by known shop, gamble on wait-time, leave if crowded.

The switching trigger is simple:

> If TrueCare can remind at the right time, recommend a trusted shop on the actual route, show believable wait-time, and hold a slot, users like Anh Tuan can switch immediately.

### 1.5 Stakeholder Needs

| Stakeholder | Needs |
|---|---|
| Car owners / VETC users | Trusted shop on route, transparent pricing, believable wait-time, easy payment, proof-of-service, simple complaint/refund. |
| Wash merchants | More customers during dead hours, simple queue/slot tools, fair payout, low tech burden, quality reputation, upsell support. |
| Tasco/VETC | Higher app frequency, wallet monetization, service attach, data loop, mobility ecosystem expansion. |
| Ops team | Merchant launch readiness, network health, SLA alerts, complaints/refunds, payout reconciliation, quality governance. |

### 1.6 Constraints

- Fragmented SME supply with low software maturity.
- Hard-to-measure service quality. Before/after evidence is the closest practical proxy.
- Thin wash economics: 50-150K VND average order means broad subsidy is dangerous.
- Constant O2O exceptions: no-shows, stale slots, overloaded merchants, failed payments, weak networks, weather, bad quality.
- Pilot must be real in 8-12 weeks, not a paper architecture.

### 1.7 Tasco's Unfair Advantages

1. VETC user base and distribution.
2. Toll + parking + fuel data for route intelligence.
3. VETC Wallet and VETC Loyalty for payment, refund, point redemption, campaign earn, and future ecosystem membership.
4. GoongIO route/ETA/distance APIs.
5. Tasco Auto / Savico / Carpla operating network.
6. Trusted brand and venture capacity.

---

## 2. Business Strategy

### 2.1 One-Line Thesis

**TrueCare is Vietnam's first predictive mobility services intelligence platform, starting with car wash as the entry-point service inside Tasco's VETC ecosystem.**

### 2.2 Core Strategic Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Core moat | Route Intelligence | VETC has route/parking/fuel patterns competitors cannot replicate quickly. |
| AI design | 1 Core Agent + rules | Honest for pilot. Avoid 8-agent theater before data exists. |
| Launch wedge | Car wash | Frequent, low-risk, visible proof, route-compatible. |
| Merchant pitch | Dead-hour demand shaping | "We bring customers when bays are empty." Measurable day one. |
| Push model | Historical VETC pattern push | No background location dependency. Uses transaction timing patterns. |
| Slot freshness | Incentive-based discipline | Fresh data gets priority display and better demand. |
| North Star | Completed Transactions / Active User | Captures activation, completion, repeat, and operating reliability. |

### 2.3 Strategic Framework

```
Layer 4: GROWTH FLYWHEEL, scale phase
  Care Score + streaks + membership + cross-sell

Layer 3: MERCHANT ENABLEMENT, pilot and scale
  Gio Vang pricing + queue tools + ranking + badge

Layer 2: TRUST & STANDARDIZATION, pilot
  SLA + before/after proof + wait-time accuracy + complaint loop

Layer 1: ROUTE INTELLIGENCE, day one
  VETC route data + weather + timing prediction + supply matching
```

### 2.4 Product Scope

P0 productizes only the software required to prove the transaction and trust loop.

**Productized in P0**

1. Service catalog + SOP rules.
2. Booking, slot hold, check-in.
3. Payment and reconciliation ledger.
4. Before/after photo evidence.
5. Recommendation / growth surface.

VETC-native loyalty profile, point redemption, campaign earn, and reconciliation attach to the payment/growth modules only if the VETC Loyalty contract gate is approved. TrueCare-native point currency, streaks, and membership remain outside P0.

**Human-operated in P0**

1. Merchant admissions, scoring, and launch readiness.
2. Merchant daily summary and payout operations.
3. Control tower reporting, SLA watch, and network health.
4. Complaint triage, refund review, and escalation.

These manual workflows still need structured data, exports, runbooks, and tests. They do not need polished product surfaces in P0.

### 2.5 Phasing

| Phase | Scope | Gate |
|---|---|---|
| Hackathon demo / P0 evidence pilot | 12-20 merchants, 300-800 invited users, one route-dense cluster | Full loop works; merchants maintain slot state; users complete real transactions. |
| Repeatable cluster | 60-100 merchants in same/adjacent cluster | Completion >85%, repeat >20%, merchant weekly active >60%, wait-time accuracy 70%+. |
| Scale | 200-300 merchants, 2-3 cities max | Unit economics, QA stability, second-service signal. |
| Platform | 500+ then 1,000+ merchants | Cross-category and FleetCare only after governance holds. |

### 2.6 P0 Success Metrics

| Metric | Pilot target |
|---|---:|
| Completion rate | >85% |
| 30-day repeat rate | >20% |
| Merchant weekly active | >60% |
| Wait-time accuracy | +/-15 min for 70%+ of bookings by end of pilot |
| Booking conversion | >8% from recommendations shown |
| Dead-hour fill uplift | >15% |
| Complaint rate | <5% |
| No-show rate | <15% |
| Route-behavior proof | On-route bookings measured separately from near-home/work bookings |

### 2.7 Unit Economics

```
Average order value:          120K VND
Take rate at 10%:              12K VND
Payment processing at ~2%:    -2.4K VND
Net revenue/order:             9.6K VND

Monthly ops cost estimate:     20M VND
Break-even transactions:       ~2,100/month
At 50 merchants:               ~42/month/merchant
```

Pilot accepts loss. The first goal is loop validation and operating truth, not profit.

Expansion revenue after proof:

- Membership wash pass.
- Merchant priority placement.
- Fleet contracts.
- Cross-sell commission.
- Merchant operating services.

### 2.8 Competitive Moat

| Competitor | Threat | Missing vs Tasco |
|---|---|---|
| Grab / Be | Could add car-care offers | No VETC route data, no payment/service evidence loop. |
| MoMo / VNPay | Payment apps can add services | No route context or merchant operating control. |
| Google Maps | POI discovery | No booking/payment/SLA/governance. |
| Local startups | Standalone wash apps | No 4M+ VETC users, no route data, no wallet rail. |
| Wash chains | Physical quality control | Limited digital layer and cross-network intelligence. |

### 2.9 Critical Dependencies

1. VETC data contract: fields, freshness, auth, latency, fallback semantics.
2. VETC identity bridge: user ref, vehicle ref, phone, consent, deep link, session ownership.
3. Legal/compliance: consent, invoice, retention, photo evidence handling.
4. Merchant cohort: 12-20 targets, one flagship, backup merchants.
5. Service catalog v1: six services, duration, price rules, proof requirements.
6. Payment state machine: wallet, cash, failure, duplicate callback, refund states.

No feature sprint starts before these gates are written and approved.

### 2.10 NOT In Scope For P0

- National rollout.
- 30-50 merchant pilot from the ambition appendix.
- 500-2,000 invited user pilot from the ambition appendix.
- Full Control Tower product.
- Full VETC native embedding.
- Self-serve merchant onboarding.
- Automated merchant settlement.
- Automated refund approval without ops review.
- ML scoring.
- 7 or 8 agent system.
- Care Score as a core P0 feature.
- Wash Pass / membership as a core P0 feature.
- Cross-category services.
- FleetCare B2B.
- IoT bay sensors.
- Real-time background location push.
- Merchant financing.

### 2.11 Demo Script

```
1. Anh Tuan's commute route appears.
2. System detects: 8 days since wash + rain + route near available merchant.
3. Push: "Xe ban can rua. Tiem Minh Anh tren duong ve co 2 bay trong, cho ~12 phut."
4. User taps "Giu cho."
5. Merchant sees a VETC booking with ETA and bay assignment.
6. User checks in by QR.
7. Merchant captures before/after photos.
8. Current P0-Final payment completes through QR/bank transfer or cash fallback; VETC Wallet remains Route Moat Gate scope.
9. User gives binary rating.
10. Ops sees completed transaction, evidence, SLA, payout, and complaint status.
```

---

## 3. Operations Playbook

### 3.1 Route-Aware Care Agent

The P0 agent is rule-based. It decides when to recommend and which merchant to rank.

#### Inputs

| Input | Source | Freshness |
|---|---|---|
| User route patterns | VETC API: toll + parking + fuel | Daily batch or near-real-time |
| Weather | Weather API | Hourly |
| Slot availability | Merchant app or Zalo fallback | Per merchant update |
| ETA/distance | GoongIO Distance Matrix | On demand |
| Last wash date | Internal booking history | Real time |
| Vehicle type | User profile / VETC bridge | Static or updated by user |

#### Scoring Formula

```
care_urgency = days_since_last_wash / typical_wash_interval
weather_boost = 1.3 if rained_in_last_24h else 1.0
route_score = 1 / (detour_minutes + 1)
merchant_score = slot_available * freshness_weight * quality_rating

recommendation_score =
  care_urgency * weather_boost * route_score * merchant_score
```

If score crosses the pilot threshold, TrueCare shows an in-app card or queues a push at the predicted commute window.

#### Output

- Care timing prediction.
- Ranked merchant recommendations.
- Wait-time estimate with confidence.
- Push-ready decision record for measurement.

#### Push Rule

No background location required. Push timing comes from historical VETC transaction patterns, usually defaulting to 7-9am and 4-6pm unless user history suggests otherwise.

### 3.2 Slot Hold

```
User taps "Giu cho"
  -> Backend performs PostgreSQL atomic slot hold
  -> Merchant queue shows held bay
  -> 30-minute countdown starts
  -> User checks in by QR
  -> Hold auto-releases if no check-in
```

Rules:

- PostgreSQL owns booking capacity writes.
- PostgreSQL owns booking capacity writes in P0; Redis is limited to cache, pub/sub, and worker support.
- Two users requesting the same slot: first write wins, second receives `SLOT_ALREADY_HELD`.
- Hold duration starts at 30 minutes and must be validated in pilot.
- Merchant sees held slot as "VETC - Cho xac nhan."

#### No-Show Policy

| Event | Action |
|---|---|
| No check-in within 30 min | Auto-release + user notification |
| 2nd no-show in 30 days | Warning |
| 3rd no-show in 30 days | Future holds require 50K deposit |
| Deposit + no-show | Deposit refunded minus 20K penalty |
| Deposit + check-in | Deposit deducted from service payment |

### 3.3 Dead-Hour Demand Shaping

The merchant promise is dead-hour utilization.

Components:

1. Identify users whose predicted route passes within 2km of a merchant with open bays.
2. Show in-app or push prompt during merchant-configured low-demand windows.
3. Let merchant define Gio Vang discount, bounded by platform floor: price cannot drop below 70% of listed base.
4. Track route proximity, conversion, completion, and fill uplift separately from ordinary browsing.

### 3.4 Payment And Ledger

| Aspect | P0 rule |
|---|---|
| Primary method in current P0-Final | QR/Bank Transfer |
| Fallback | Cash at merchant, recorded in system |
| Deferred funded-baseline method | VETC Wallet after Route Moat Gate |
| QR commission | 10% receivable, accrued after merchant payment verification; not auto-deducted from user-to-merchant transfer |
| Cash commission | 0% at pilot, used as fallback and QR/wallet incentive |
| Merchant payout | Manual weekly transfer using exported CSV |
| Refund | Complaint -> ops review -> manual QR/cash resolution within SLA in current P0-Final; wallet refund after Route Moat Gate |

Payment states for current P0-Final follow the PRD Section 8 QR-first state machine. Duplicate user claims, duplicate merchant confirmations, cash fallback, refund approval, refund failure, and ledger idempotency are P0 test requirements. The funded VETC Wallet state machine remains a Route Moat Gate requirement before claiming VETC-native validation.

### 3.5 Complaint Taxonomy

| Category | Auto-approve? | Resolution | SLA |
|---|---|---|---|
| Merchant no-show / closed when booked as open | Yes | 100% refund | Immediate |
| Wait-time >2x promised | Yes | 20K voucher | Immediate |
| User cancel before check-in | Yes | 100% if >15 min before hold expiry | Immediate |
| Quality issue | Ops review | 50-100% refund by severity | 24h review, 48h credit |
| Wrong service delivered | Ops review | Up to 100% refund | 24h review, 48h credit |
| Charge dispute | Ops review | Case by case | 48h review |

Complaints open longer than 48h escalate to ops manager.

### 3.6 Failure Mode Registry

| Failure mode | Likelihood | Impact | P0 handling |
|---|---|---|---|
| Merchant does not update slots | High | High | Stale detection after 2h, lower ranking, ops alert |
| Wrong wait-time | Medium | High | Start with relaxed target, measure actual vs predicted, voucher if >2x |
| Payment failure | Low-medium | High | Cash fallback, retry state, ledger audit |
| Photo upload weak network | Medium | Medium | Local queue + retry |
| Concurrent hold conflict | Medium | Medium | PostgreSQL atomic write |
| User arrives late | Medium | Medium | 30-min hold + expiry notification |
| Bad merchant quality | Medium | High | Evidence, complaints, quality scoring, delisting path |
| VETC API downtime | Low | High | Fallback provider using GoongIO/GPS/default recommendations |
| Weather API wrong | Low | Low | Directional signal only in P0 |
| Merchant offline silently | Medium | High | Auto-flag, hide from recommendations, ops follow-up |
| Celery task crash | Medium | Medium | Dead letter queue + alert |
| Redis pub/sub missed message | Medium | Medium | DB outbox + sweeper |

No silent failure is allowed for money, booking state, evidence, complaint trust, or merchant quality.

### 3.7 Data Model

Core entities:

```
User
  id, vetc_id, name, phone, roles, preferences, consent_state

Vehicle
  id, user_id, plate, type, model, last_wash_date

Merchant
  id, name, address, location, bays, operating_hours,
  gio_vang_config, quality_score, slot_freshness_score

SlotCapacity
  id, merchant_id, date, hour, available_bays, status

Booking
  id, user_id, vehicle_id, merchant_id, slot_time, status,
  source, hold_expiry, check_in_time, completion_time

ServiceEvidence
  id, booking_id, before_photos, after_photos, uploaded_at, completeness_status

Rating
  id, booking_id, sentiment, comment, created_at

Complaint
  id, booking_id, category, status, refund_amount, resolution, sla_due_at

Payment
  id, booking_id, amount, method, commission, status, external_ref, idempotency_key

Payout
  id, merchant_id, period, total_orders, total_amount, commission_deducted, net_payout, status

Promotion
  id, merchant_id, type, discount_pct, time_window, status
```

Scale-only entities like CareScore can be added after sufficient usage history exists.

#### Derived Metrics

| Metric | Calculation / source |
|---|---|
| Merchant fill rate | completed bookings / total available slots |
| Average handling time | completion_time - check_in_time |
| Lateness rate | check_in_time > hold_expiry |
| Complaint rate | complaints / completed bookings |
| Net revenue per order | payment amount * commission - processing fee |
| 30-day repeat | users with 2+ bookings / active users |
| Booking-to-completion funnel | bookings -> check-ins -> completions -> ratings |
| Route-match rate | AI-recommended bookings / total bookings |
| Dead-hour fill uplift | fill rate with shaping vs baseline |
| Slot freshness | time since last capacity update |
| Wait-time accuracy | abs(predicted wait - actual wait) |

### 3.8 Service Operation Flow

```
1. Discover      User opens app or receives push
2. Select        User chooses merchant/service
3. Hold          Backend reserves bay/slot
4. Confirm       Merchant sees booking
5. Check in      QR scan at bay
6. Execute       Merchant performs wash
7. Capture       Before/after evidence
8. Await payment Merchant marks service done; booking remains awaiting_payment
9. Pay           QR/bank transfer or cash fallback
10. Complete     Merchant verifies payment; booking becomes completed
11. Improve      Rating, complaint, payout, metrics, scoring update
```

#### Event Management

| Trigger | Event |
|---|---|
| Slot stale >2h | Ops alert + hide from recommendations |
| Wait-time breach | SLA alert and voucher logic |
| Complaint open >48h | Ops manager escalation |
| Payment callback timeout | Payment retry/ops alert |
| Photo evidence incomplete | Merchant prompt + ops quality flag |
| FCM failure | Mark token inactive; use in-app/Zalo fallback where relevant |

#### Problem Management

Weekly review:

- Wait-time errors by merchant/time window.
- Complaint clusters by merchant/category.
- Slot freshness by merchant.
- No-show patterns by user segment.
- Payment failures by provider/state.
- Evidence completeness by merchant/staff.

### 3.9 Service Catalog V1

Service catalog must be locked before schema migrations.

| Service | Duration | Evidence required | Notes |
|---|---:|---|---|
| Rua ngoai co ban | 20-30 min | Before + after exterior | P0 default |
| Rua trong ngoai | 35-45 min | Before + after exterior/interior | Higher AOV |
| Hut bui noi that | 15-20 min | Interior after | Add-on |
| Ve sinh kinh/guong | 10-15 min | After | Add-on |
| Rua gam co ban | 20-30 min | Before + after lower body | Optional by merchant capability |
| Combo Gio Vang | Merchant-defined | Same as included services | Discount floor >=70% base |

### 3.10 Merchant Onboarding Checklist

Before merchant goes live:

- Business/KYC verified.
- Address, location, operating hours confirmed.
- Bay count and service durations confirmed.
- Service catalog/pricing signed.
- Bay QR codes printed and installed.
- Staff trained on queue, evidence, completion, and cash fallback.
- Test booking completed end to end.
- Payout export fields verified.
- Zalo fallback contact verified.
- Launch readiness signed by Ops + Quality Lead.

### 3.11 Field Validation Questions

Ask five drivers:

- How do you remember when to wash or maintain your car?
- What makes you trust a shop?
- How far off-route is still acceptable?
- What wait-time estimate would you believe?
- Would a held slot change your behavior?

Ask three merchants:

- Would you update slot availability daily if it affects ranking and demand?
- What dead-hour discount is acceptable?
- What proof/photo workflow is realistic for staff?
- What payout cadence builds trust?
- What would make a 10% commission feel fair?

---

## 4. Implementation Implications

Engineering, design, and backlog must now treat this file as the product/business/operations source of truth.

| Layer | Source |
|---|---|
| Business + product + operations | `01-challenge-and-context.md` |
| Funded business baseline and IC framing | `07-business-proposal-en.md` |
| Engineering implementation plan | `05-engineering-plan.md` |
| UI design and screen states | `06-design-spec.md` and `screen-artifacts/TrueCare-screen-specs.html` |
| Execution backlog | `TODOS.md` |

The former strategy and operations files have been removed. This file is the implementation authority for business, product, and operations decisions.
