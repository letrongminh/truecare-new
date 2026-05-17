# 10 — AI-Native ServiceOS Specification

> **TrueCare AI Proactive Intelligence — World-Class UX Blueprint**
>
> Last updated: 2026-04-26
> Status: Planning COMPLETE. Integrates with `09-product-requirements-document.md` v2.0 (including Section 8: VETC Loyalty Ecosystem Integration).
> Source of truth for AI architecture, agent specifications, data flywheel, and AI UX standards.
> For business baseline, see `business-proposal/07-business-proposal-en.md` Section 15 (Data Moat & AI Moat Blueprint).
> For product requirements, see `09-product-requirements-document.md`.
> For loyalty ecosystem behavior, see `09-product-requirements-document.md` Section 8.
> For engineering, see `05-engineering-plan.md`.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [AI Philosophy & Principles](#2-ai-philosophy--principles)
3. [AI Architecture Overview](#3-ai-architecture-overview)
4. [The Seven AI Agents — Full Specification](#4-the-seven-ai-agents--full-specification)
5. [Contextual Intelligence Card — The Visible AI Surface](#5-contextual-intelligence-card--the-visible-ai-surface)
6. [Proactive Push Notification Intelligence](#6-proactive-push-notification-intelligence)
7. [Silent AI Actions](#7-silent-ai-actions)
8. [Data Flywheel — Compounding Moat](#8-data-flywheel--compounding-moat)
9. [AI Implementation Phases](#9-ai-implementation-phases)
10. [AI Success Metrics & Health Dashboard](#10-ai-success-metrics--health-dashboard)
11. [AI Governance & Ethics](#11-ai-governance--ethics)
12. [World-Class UX Compliance Checklist](#12-world-class-ux-compliance-checklist)
13. [Integration Points with Existing PRD](#13-integration-points-with-existing-prd)
14. [LLM Strategy — When & Why](#14-llm-strategy--when--why)
15. [Anti-AI-Washing Safeguards](#15-anti-ai-washing-safeguards)
16. [Glossary](#16-glossary)

---

## 1. Executive Summary

**TrueCare is an AI-native ServiceOS**, not a car-wash booking app with AI features bolted on. AI is the operating infrastructure — invisible to users, compounding with every transaction, intervening at decision points to make the system smarter over time.

Seven action-level AI agents orchestrate demand prediction, merchant quality scoring, slot dispatch, demand shaping, photo anomaly detection, cross-sell recommendation, and dynamic pricing. None is a chatbot. None uses a conversational interface. Every agent intervenes in a real workflow, produces measurable business impact, and feeds its learnings back into a compounding data flywheel.

**The AI does not chat with you. It acts on your behalf.** Users experience the results — perfectly timed push notifications, intelligently ranked merchants, optimally assigned bays — without ever seeing a loading spinner labeled "AI."

### Integration with Main PRD

This specification is the AI companion to `09-product-requirements-document.md`. Where the main PRD defines what the user sees and does (screens, flows, interactions), this document defines the intelligence layer that powers those experiences. Cross-references are marked with `→ PRD Section X.Y`.

| Main PRD Section | AI Spec Coverage |
|---|---|
| Section 3 — Product Vision | AI Promise (Section 2 below) |
| Section 5.1 M5 — Recommendation | Full 7-agent specification (Section 4 below) |
| Section 6.2 — Home Screen | CIC card on Home (Section 5 below) |
| Section 10 — Notification System | Push Decision Engine (Section 6 below) |
| Section 15 — Success Metrics | AI Health Metrics (Section 10 below) |
| Section 16 — Implementation Plan | AI Phases P0-P4 (Section 9 below) |
| `09-product-requirements-document.md` Section 8 | Loyalty-aware triggers: point balance, tier eligibility, campaign budget, redemption history, wallet payment, and service-cycle retention |

---

## 2. AI Philosophy & Principles

### 2.1 The Core Belief

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│  "The best AI is the one you don't see.                          │
│   It doesn't dance on your screen.                               │
│   It puts the right button in front of you at the right moment,  │
│   and you tap it without thinking."                              │
│                                                                   │
│  AI is INFRASTRUCTURE, not a FEATURE.                            │
│  AI operates in the BACKGROUND, not the FOREGROUND.              │
│  AI makes DECISIONS, not CONVERSATIONS.                          │
│  AI compounds with DATA, not degrades with SCALE.                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Seven AI UX Principles

| # | Principle | Definition | Anti-Pattern (What We Never Do) |
|---|---|---|---|
| P1 | **Invisible** | AI runs in the background. Users see results, never "AI processing." | "Đang phân tích bởi AI..." spinner overlay |
| P2 | **Proactive** | System initiates at the right moment. User confirms with one tap. | User must open app, search, browse, ask |
| P3 | **Instant** | All AI inference <50ms for real-time paths, <1s for batch paths. No perceived latency. | LLM call with 500ms-2s latency for real-time user-facing action |
| P4 | **Fallback-Safe** | AI is suggestion, never authority. AI wrong → user chooses differently. No blocking paths. | "Tính năng AI đang lỗi, vui lòng thử lại sau" dead end |
| P5 | **Silently Learning** | Every user action is implicit feedback. No "Was this recommendation helpful?" prompts. | Rating request for each AI output |
| P6 | **Accumulating Personalization** | Day 1: generic defaults. Day 30: knows habits. Day 90: predicts needs. | Static AI that never improves per-user |
| P7 | **Context-Aware, Not Intrusive** | Push only when recommendation score exceeds confidence threshold. Strict anti-spam. | Daily "Chúc ngày mới tốt lành!" engagement bait |

### 2.3 The AI Promise (→ PRD Section 3.4)

TrueCare is AI-native, not AI-washed. This means AI does not converse — it acts:

- **AI predicts** when your car needs care before you think about it
- **AI ranks** merchants by quality, not by who pays for placement
- **AI assigns** the optimal bay to minimize your wait time
- **AI detects** incomplete or fraudulent service evidence
- **AI recommends** the next service your vehicle actually needs
- **AI prices** Gio Vang discounts to maximize merchant revenue

The user doesn't "use AI features." The AI operates invisibly. The user experiences a product that seems to know what they need, when they need it, without being asked.

### 2.4 AI Decision Classification

Every AI decision in TrueCare is categorized to determine the right technical approach:

```
                              ┌─────────────────────────┐
                              │   REQUIRES REAL-TIME?    │
                              │   (<200ms latency)       │
                              └───────────┬─────────────┘
                                    YES   │   NO
                        ┌─────────────────┴─────────────────┐
                        ▼                                   ▼
              ┌──────────────────┐              ┌──────────────────────┐
              │ MUST BE EXACT?   │              │ IS DATA STRUCTURED?  │
              │ (deterministic)  │              └──────────┬───────────┘
              └────────┬─────────┘                   YES   │   NO
                 YES   │   NO                     ┌────────┴────────┐
              ┌────────┴────────┐                 ▼                 ▼
              ▼                 ▼           ┌───────────┐    ┌───────────┐
        ┌───────────┐    ┌───────────┐      │ ML MODEL  │    │ LLM (P4) │
        │ ALGORITHM │    │ ML MODEL  │      │ Batch/API │    │ Text/NLP  │
        │           │    │ Real-time │      └───────────┘    └───────────┘
        │ Agent 3   │    │ Agent 1,2 │
        └───────────┘    └───────────┘
```

---

## 3. AI Architecture Overview

### 3.1 System Diagram

```
╔══════════════════════════════════════════════════════════════════════════╗
║                   TRUECARE AI PROACTIVE INTELLIGENCE                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ┌─────────────────── DATA INPUT STREAMS ───────────────────┐          ║
║  │                                                           │          ║
║  │  STREAM A              STREAM B             STREAM C      │          ║
║  │  VETC Mobility         Service Outcome      Merchant Perf │          ║
║  │  ┌────────────┐       ┌────────────┐       ┌───────────┐ │          ║
║  │  │Toll events │       │Photos      │       │Slot fresh │ │          ║
║  │  │Parking     │       │SOP ticks   │       │Peak/dead  │ │          ║
║  │  │Fuel events │       │Duration    │       │Quality    │ │          ║
║  │  │Route data  │       │Rating      │       │Payout     │ │          ║
║  │  └────────────┘       │Complaint   │       └───────────┘ │          ║
║  │                       │Rebook      │                      │          ║
║  │                       └────────────┘                      │          ║
║  └──────────────────────┬───────────────────────────────────┘          ║
║                         │                                               ║
║                         ▼                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐  ║
║  │                    AI AGENT ORCHESTRATION LAYER                    │  ║
║  │                                                                   │  ║
║  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  ║
║  │  │ AGENT 1      │  │ AGENT 2      │  │ AGENT 3      │           │  ║
║  │  │ Care Timing  │  │ Merchant     │  │ Slot         │           │  ║
║  │  │ Predictor    │  │ Quality      │  │ Dispatcher   │           │  ║
║  │  │              │  │ Score        │  │              │           │  ║
║  │  │ P0: Rule     │  │ P0: Rule     │  │ P0: Algorithm│           │  ║
║  │  │ P1: XGBoost  │  │ P1: Ridge    │  │ P1: +ML dur  │           │  ║
║  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │  ║
║  │         │                 │                  │                    │  ║
║  │  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐           │  ║
║  │  │ AGENT 4      │  │ AGENT 5      │  │ AGENT 6      │ AGENT 7  │  ║
║  │  │ Demand       │  │ Photo        │  │ Cross-Sell   │ Dynamic  │  ║
║  │  │ Shaping      │  │ Anomaly      │  │ Recommender  │ Pricing  │  ║
║  │  │              │  │ Detector     │  │              │          │  ║
║  │  │ P0: Rule     │  │ P0: Manual   │  │ P0: Deferred │ P0: Fixed│  ║
║  │  │ P2: ML       │  │ P2: CV       │  │ P2: ML Hybrid│ P2: Bandit│  ║
║  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │  ║
║  └─────────┼─────────────────┼──────────────────┼───────────────────┘  ║
║            │                 │                  │                       ║
║            ▼                 ▼                  ▼                       ║
║  ┌──────────────────────────────────────────────────────────────────┐  ║
║  │              PROACTIVE INTELLIGENCE OUTPUT LAYER                  │  ║
║  │                                                                   │  ║
║  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │  ║
║  │  │ PUSH       │ │ HOME CARD  │ │ IN-APP     │ │ AUTO-ACTION│   │  ║
║  │  │ NOTIF      │ │ (CIC)      │ │ SURFACE    │ │ (silent)   │   │  ║
║  │  │            │ │            │ │            │ │            │   │  ║
║  │  │ Agent 1,4  │ │ Agent 1,2  │ │ Agent 6    │ │ Agent 3,7  │   │  ║
║  │  │ Timing +   │ │ Timing +   │ │ Cross-sell │ │ Dispatch + │   │  ║
║  │  │ Demand     │ │ Quality    │ │ recs       │ │ Pricing    │   │  ║
║  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │  ║
║  │                                                                   │  ║
║  │  ┌────────────────────────────────────────────────────────────┐  │  ║
║  │  │ USER ACTION: TAP ONCE → SYSTEM HANDLES THE REST             │  │  ║
║  │  └────────────────────────────────────────────────────────────┘  │  ║
║  └──────────────────────────────────────────────────────────────────┘  ║
║                                                                          ║
║  ════════════════════════════════════════════════════════════════════    ║
║  DATA FLYWHEEL: Action → Data → Better AI → Better UX → More Action     ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### 3.2 Agent Dependency Map

Agents are not isolated chatbots. They form a self-reinforcing ecosystem where each model's output feeds another's input.

```
             ┌──────────────────┐
             │ Care Timing      │
             │ Predictor (1)    │
             └────────┬─────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
 ┌──────────────────┐   ┌──────────────────┐
 │ Demand Shaping   │◄──│ Slot Dispatcher  │
 │ Engine (4)       │   │ (3)              │
 └──────────────────┘   └──────────────────┘
           │                     │
           └──────────┬──────────┘
                      ▼
             ┌──────────────────┐       ┌──────────────────┐
             │ Dynamic Pricing  │───────► Merchant Quality │
             │ (Gio Vang) (7)   │       │ Score (2)        │
             └──────────────────┘       └──────────────────┘
                      │                          ▲
                      │                          │
                      └──── Photo Anomaly ───────┘
                            Detector (5)
                      │
                      ▼
             ┌──────────────────┐
             │ Cross-Sell       │
             │ Recommender (6)  │
             └──────────────────┘
```

---

## 4. The Seven AI Agents — Full Specification

### 4.1 Agent Classification Summary

| # | Agent | AI Approach | Phase | Latency | UX Surface | LLM? |
|---|---|---|---|---|---|---|
| 1 | Care Timing Predictor | Rule → XGBoost (P1) | P0 | Batch | Push + CIC | No |
| 2 | Merchant Quality Score | Rule → Ridge (P1) | P0 | Batch | Ranking | No |
| 3 | Slot Dispatcher | Algorithm + ML duration (P1) | P0 | Real-time <200ms | Silent | No |
| 4 | Demand Shaping Engine | Rule → Propensity ML (P2) | P0 | Batch | Push | No |
| 5 | Photo Anomaly Detector | Manual → Siamese CV (P2) | P2 | Batch | Ops queue | No |
| 6 | Cross-Sell Recommender | ML Hybrid (P2) | P2 | Batch | CIC | No |
| 7 | Dynamic Pricing (Gio Vang) | Fixed → Bandit ML (P2) | P2 | Batch | Silent | No |

### 4.2 Agent 1: Care Timing Predictor

**What it does:** Predicts when a specific user should wash their car and determines the optimal moment to notify them.

**P0 — Rule-Based Specification:**

| Dimension | Value |
|---|---|
| **Input** | `days_since_last_wash` (from booking history), `typical_wash_interval` (default: 7 days, personalized from onboarding), `weather_rain_24h` (boolean), `detour_minutes` (from GoongIO), `slot_available` (boolean), `merchant_quality_score` (from Agent 2) |
| **Scoring Formula** | `care_urgency = days_since_last_wash / typical_wash_interval` |
| | `weather_boost = 1.3 if rained_in_last_24h else 1.0` |
| | `route_score = 1 / (detour_minutes + 1)` |
| | `merchant_score = slot_available × freshness_weight × quality_rating` |
| | `recommendation_score = care_urgency × weather_boost × route_score × merchant_score` |
| **Output** | `recommendation_score` (0.0-10.0). If > threshold (default: 2.0): queue push notification. |
| **Cold-Start Defaults** | `care_urgency=1.0`, `weather_boost=1.0`, `route_score=0.5`, `quality_rating=3.0` |
| **Push Timing** | From historical VETC transaction patterns. Default windows: 7-9am, 4-6pm. Per-user: computed from individual toll event timestamps. |
| **Configurability** | All weights stored in `scoring_config` database table. Admin API endpoint for tuning. No redeploy required. |
| **UX Surface** | Push notification (→ PRD Section 10, N1). CIC card on Home (→ Section 5 below). |
| **User Action** | 1 tap on push → app opens Home with hero card ready. 0 taps needed if user already has app open. |

**P1 — ML Upgrade (XGBoost):**

| Dimension | Value |
|---|---|
| **Why ML** | Rule-based weights are hand-tuned and static. ML learns per-user timing patterns, weather sensitivity, and route flexibility from observed behavior. |
| **Training Data** | Labeled outcomes: (`input_features`, `booking_made: true/false`) per push event. ~1,200 samples available after 3-month pilot. |
| **Features** | VETC toll frequency (times/week), parking dwell patterns, fuel station visit frequency, day-of-week, hour-of-day, rain_mm_24h, temperature, user_avg_booking_interval, user_push_open_rate_7d |
| **Target** | `P(booking within 48h | push sent)` |
| **Retrain Cadence** | Weekly batch retrain from accumulated labeled data |
| **A/B Test** | 50/50 split: rule-based vs ML-based push timing. Metric: push-to-booking conversion rate |
| **Expected Impact** | +30-50% push-to-booking rate vs broadcast push baseline |
| **Latency** | Batch prediction: ~50ms per user. Pre-computed during 15-min scoring cycle (→ PRD Section 5.1 M5 Intelligence Worker). |

**UX Impact of ML Upgrade:** Users experience no visible change. The push notification still looks identical. The difference is that the push arrives at an individually optimal time rather than a fixed window, resulting in higher open rates.

### 4.3 Agent 2: Merchant Quality Score

**What it does:** Computes a 0-100 composite quality score for each merchant based on evidence completeness, customer ratings, complaint history, and SOP compliance.

**P0 — Rule-Based Specification:**

| Dimension | Value |
|---|---|
| **Input** | `evidence_completeness_pct` (% of bookings with both before+after photos), `rating_satisfied_pct` (% of ratings that are 👍), `complaint_rate_30d` (complaints/completed_bookings), `sop_compliance_pct` (% of bookings with completed SOP checklist), `slot_freshness_hours` (time since last slot update) |
| **Scoring Formula** | `score = (w_evidence × evidence_completeness) + (w_rating × rating_satisfied) + (w_complaint × (1 - complaint_rate)) + (w_sop × sop_compliance) + (w_freshness × max(0, 1 - slot_freshness/24))` |
| **Default Weights** | `w_evidence=25`, `w_rating=30`, `w_complaint=25`, `w_sop=15`, `w_freshness=5`. Sum = 100. |
| **Output** | 0-100 composite score. Updated after every booking completion. |
| **Configurability** | All weights in `scoring_config` table. |
| **UX Surface (Consumer)** | Merchants ranked by score on Home and Map screens (→ PRD Sections 6.2, 6.3). Score never shown as a number to consumers — only reflected in ranking order. |
| **UX Surface (Merchant)** | Score displayed on Queue Board: "⭐ Điểm chất lượng: 78/100." Guidance text: "Chụp đủ ảnh và SOP đúng để tăng điểm." |
| **UX Surface (Ops)** | Score visible in merchant profile. Alert when score drops below 30 for 30 consecutive days (delisting review trigger). |

**P1 — ML Upgrade (Ridge Regression):**

| Dimension | Value |
|---|---|
| **Why ML** | Rule-based weights are uniform across all merchants. ML learns which factors actually predict complaint rates and customer retention, which vary by merchant archetype and location. |
| **Training Data** | Labeled outcomes: (`feature_vector`, `complaint_rate_90d`, `customer_retention_90d`) per merchant. |
| **Features** | Evidence completeness trend (improving/declining), rating sentiment trend, SOP checklist item-specific pass rates, response time to bookings, photo upload latency, peak-hour vs dead-hour quality variance |
| **Target** | Composite: minimize complaint_rate_90d + maximize retention_90d |
| **Retrain Cadence** | Monthly |
| **Expected Impact** | Ranking conversion +15%, complaint rate -40% vs unsorted merchants |
| **Anti-Demotivation Rule** | Score is shown to merchant privately. Consumers never see the number — only the resulting ranking. Merchants are not publicly shamed. |

### 4.4 Agent 3: Slot Dispatcher

**What it does:** Assigns incoming bookings to specific bays to minimize wait time, maximize fill rate, and prevent double-booking.

**P0 — Algorithm Specification:**

| Dimension | Value |
|---|---|
| **Approach** | **Constraint algorithm — NOT AI.** This is deterministic resource allocation. Zero ML, zero LLM. |
| **Input** | `booking_request {slot_time, service_type, preferred_bay}`, `bay_status[]`, `existing_bookings[]`, `service_duration[]` |
| **Algorithm** | 1. If `preferred_bay` is available at `slot_time` → assign to `preferred_bay`. |
| | 2. Else: find the bay with the largest gap between its last booking end-time and the next booking start-time at `slot_time`. |
| | 3. If no bay available: return `SLOT_ALREADY_HELD` with alternative merchants. |
| | 4. All assignments go through atomic `UPDATE slot_capacity WHERE status='available'` (→ PRD Section 5.1 M2). |
| **Auto-Accept** | All booking writes route through the same `POST /api/bookings/hold` endpoint. Server-side `source: auto_accept` triggers algorithm above. Race condition prevented by PostgreSQL row-level lock. |
| **Latency** | <200ms (single atomic DB write, no external calls). |
| **UX Surface** | Silent. Consumer sees "Bay 2" in booking. Merchant sees bay color change. No user-facing AI UI. |
| **Why Not ML** | Dispatch is a constrained optimization problem. ML adds latency, non-determinism, and complexity with no benefit over a well-designed algorithm. The algorithm is 20 lines of code and always correct. |

**P1 — ML Enhancement (Duration Prediction Only):**

The core dispatch algorithm remains unchanged. ML only improves the `service_duration` input:

| Dimension | Value |
|---|---|
| **What ML Predicts** | `actual_service_duration` for each merchant × service_type combination |
| **Training Data** | Historical `(merchant_id, service_type, predicted_duration, actual_duration)` pairs |
| **Features** | Merchant ID, service type, day of week, hour of day, bay number, staff shift, weather (rain slows exterior wash) |
| **Impact** | More accurate duration → better gap calculation → fewer scheduling conflicts. Wait-time accuracy improves from ±15min to ±10min for 80%+ of bookings. |

### 4.5 Agent 4: Demand Shaping Engine

**What it does:** Identifies which users to target with Gio Vang (dead-hour discount) offers to fill empty bays during low-demand periods.

**P0 — Rule-Based Specification:**

| Dimension | Value |
|---|---|
| **Input** | `route_cohort` (users whose predicted route passes within 2km of merchant cluster), `gio_vang_active` (boolean per merchant), `time_window` (merchant-configured Gio Vang hours), `available_bays` |
| **Rule** | For each merchant with `gio_vang_active = true` AND `time in gio_vang_window`: |
| | 1. Find all users whose predicted route passes within 2km during the Gio Vang window |
| | 2. Filter: users not already booked, users not in cooldown (last push <4h ago) |
| | 3. Push to all eligible users (no individual targeting in P0) |
| **Output** | Batch push queue for Notification Worker |
| **UX Surface** | Push notification: "⚡ Gio Vang! {merchant_name} giam {discount}% tu {start}-{end}. Con {bays} bay. Dat ngay?" |
| **User Action** | 1 tap on push → Merchant Detail with Gio Vang price displayed |
| **Measurement** | Dead-hour fill rate with Gio Vang vs baseline same-hour average fill rate |
| **Expected Impact** | +15% dead-hour fill rate from baseline proximity push (P0 rule-based). +15-40% with P2 ML targeting. |

**P2 — ML Upgrade (Propensity Model):**

| Dimension | Value |
|---|---|
| **Why ML** | Rule-based push targets everyone equally. ML learns which users actually respond to Gio Vang offers based on price sensitivity, timing flexibility, and past behavior. |
| **Training Data** | `(user_features, gio_vang_offer_details, booking_made: true/false)` |
| **Features** | User historical Gio Vang response rate, user price sensitivity (avg booking price vs average), user timing flexibility (variance in booking times), distance from cluster center, day_of_week, time_of_day, discount_pct |
| **Model** | Logistic regression predicting `P(booking | gio_vang_offer)` |
| **Targeting** | Rank eligible users by predicted probability. Push top-N users (N = available_bays × 3, to account for conversion rate). |
| **Retrain Cadence** | Monthly |
| **Expected Impact** | Dead-hour fill +15-40% over rule-based baseline |

### 4.6 Agent 5: Photo Anomaly Detector

**What it does:** Detects incomplete, mismatched, or potentially fraudulent before/after photo pairs in service evidence.

**P0 — Manual Specification:**

| Dimension | Value |
|---|---|
| **Approach** | Human ops review. All bookings with `evidence_status = partial` (before only, after missing) flagged for ops review. Quality Lead manually inspects flagged evidence. |
| **Why No ML in P0** | Requires 3-6 months of accumulated labeled photo pairs before ML training is viable. P0 has 12-20 merchants producing ~300 bookings/month — insufficient volume for CV model. |
| **UX Surface (Ops)** | Control Tower complaint/evidence queue. Manual review interface. |

**P2 — ML Upgrade (Siamese CV Network):**

| Dimension | Value |
|---|---|
| **Why ML** | Manual review doesn't scale beyond 50 merchants. ML pre-screens evidence, saving 70% of ops review time. |
| **Why Not LLM (GPT-4V)** | (a) Privacy: medical/vehicle photos cannot be sent to third-party cloud AI providers. (b) Cost: $0.01-0.03/image pair. At 500 bookings/day = $150-450/month. (c) Latency: 2-5s per inference. CV model: 50ms on edge server. |
| **Approach** | Siamese network (ResNet-50 backbone). Compare embedding vectors of before and after photos. Train on labeled pairs from ops review history. |
| **Deployment** | On-premise edge server within Vietnam. Data never leaves TrueCare infrastructure. |
| **Input** | Before photo, after photo, metadata (geotag delta, timestamp delta, device ID) |
| **Output** | Anomaly score 0-100. `score > 70` → auto-flag for human review. `score < 30` → auto-approve. `30-70` → queue for spot-check. |
| **Training Data** | Labeled pairs from ops review: `{before_photo, after_photo, anomaly_label: true/false, anomaly_type}` |
| **Retrain Cadence** | Monthly from new labeled data |
| **Expected Impact** | 70% reduction in ops review time. False positive rate <5%. |
| **UX Surface** | Ops control tower: flagged evidence queue with anomaly score and thumbnail. One-tap confirm/reject. |

### 4.7 Agent 6: Cross-Sell Recommender

**What it does:** Recommends the next service a user's vehicle likely needs based on booking history, vehicle profile, and seasonal patterns.

**P0-P1 — Deferred:**

| Dimension | Value |
|---|---|
| **Status** | Entirely deferred. P0-P1 have wash-only services. No cross-sell surface exists. |
| **Data Collection** | Track cross-sell demand signals: user asks "có hút bụi không?" → logged as demand signal. Merchant offers add-on at checkout → logged as supply signal. |

**P2 — ML Upgrade (Hybrid Recommender):**

| Dimension | Value |
|---|---|
| **Approach** | Hybrid: Collaborative Filtering (user-service matrix) + Content-Based (vehicle profile similarity) |
| **Input** | User booking history (services booked, frequency), vehicle profile (type, age, mileage estimate from VETC fuel frequency), season |
| **Collaborative Filtering** | "Users with similar vehicle profiles who booked X also booked Y" |
| **Content-Based** | "Your vehicle is a 5-year-old SUV with 80K km → recommend underbody wash, interior vacuum" |
| **Cold Start** | Vehicle type + age + season → heuristic recommendations. As data accumulates, collaborative signal strengthens. |
| **UX Surface** | CIC card on Home: "💡 Da 3 thang tu lan hut bui gan nhat. Dat them?" (→ Section 5) |
| **User Action** | 1 tap → add-on service appended to next booking |
| **Retrain Cadence** | Quarterly |
| **Expected Impact** | Cross-sell attach rate +10-25 percentage points |
| **Why Not LLM** | Recommendation logic is collaborative filtering + content similarity. LLM adds latency and cost with no accuracy improvement. LLM may be used in P4 to generate the explanation text ("Đã 3 tháng từ lần hút bụi gần nhất") but the recommendation itself is ML-driven. |

### 4.8 Agent 7: Dynamic Pricing / Gio Vang Optimizer

**What it does:** Suggests the optimal Gio Vang discount percentage for each merchant to maximize revenue while respecting the platform-enforced floor (>=70% base price).

**P0-P1 — Merchant-Defined:**

| Dimension | Value |
|---|---|
| **Status** | Fixed discount. Merchant manually sets percentage in Slot Management (→ PRD Section 7.5). Floor enforced at >=70% base price. |
| **Data Collection** | Track: at discount X%, fill rate was Y%, revenue = (base × (1-X)) × fill_rate. Collect elasticity data per merchant. |

**P2 — ML Upgrade (Contextual Bandit):**

| Dimension | Value |
|---|---|
| **Approach** | Contextual Bandit (explore/exploit). |
| **Exploration** | Occasionally suggest a new discount percentage (±5% from current) to learn price elasticity. |
| **Exploitation** | Use the discount that has historically maximized revenue for this merchant in similar conditions (day, weather, available bays). |
| **Guardrails** | Floor: >=70% base price (platform-enforced). Ceiling: merchant's manual setting (AI cannot go higher). Max change: ±10% per week (avoids shocking merchant). |
| **UX Surface** | Slot Management suggestion card: "📊 Giảm 25% giúp bạn thêm ~12 khách/tuần, doanh thu +8%. [Thử]" — merchant must explicitly accept. AI never changes pricing without merchant consent. |
| **User Action** | 1 tap to accept suggestion. Ignore to keep current pricing. |
| **Retrain Cadence** | Weekly update of bandit reward estimates |
| **Expected Impact** | Revenue per merchant +8-15% during Gio Vang hours |
| **Why Not LLM** | Pricing is numerical optimization. LLM is not designed for constrained optimization problems. Contextual bandit is the proven approach for this use case. |

---

## 5. Contextual Intelligence Card — The Visible AI Surface

### 5.1 Philosophy

The **Contextual Intelligence Card (CIC)** is the only visible AI surface in the consumer app. It replaces the chatbot/avatar concept entirely. It is a text card on the Home screen that appears when an AI agent has a high-confidence recommendation, and disappears when there is nothing worth saying.

The CIC is not a conversation. It has no input field. The user does not type or speak. The system initiates. The user confirms with one tap.

### 5.2 Position & Behavior

```
┌─────────────────────────────────────────┐
│ TRUECARE                   🔔     👤   │  ← Header (→ PRD Section 6.2)
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │  ← CIC Card
│  │ ✨ Chào anh Tuấn!              │   │     Vị trí: CỐ ĐỊNH dưới header
│  │                                 │   │     Xuất hiện: KHI score > threshold
│  │ Trời sắp mưa to vào chiều nay. │   │     Ẩn: KHI không có gì đáng nói
│  │ Tiem Minh Anh có mái che,       │   │     (không force hiển thị)
│  │ còn 2 bay trống. Đặt nhé?      │   │
│  │                                 │   │
│  │ [Đặt ngay]  [Xem thêm]  [✕]   │   │  ← 1-tap CTA + dismiss
│  └─────────────────────────────────┘   │
│                                         │
│  DE XUAT HANG DAU                       │
│  ┌─────────────────────────────────┐   │
│  │ ★ TIEM MINH ANH     ⭐ 82/100  │   │  ← Hero recommendation
│  │ 1.2km · ~12 phút · Còn 2 bay  │   │     ranked by Agent 2
│  │ 🏷 Gio Vang: giảm 20%         │   │
│  │ [======== GIU CHO ==========] │   │
│  └─────────────────────────────────┘   │
│                                         │
│  CUNG GAN BAN                           │
│  AutoSpa Cau Giay    8ph 2.8km [Giu]  │  ← Alternatives ranked by Agent 2
│  CleanCar Lang Ha    18ph 1.8km [Giu] │
│  Rua Xe TC           25ph 0.5km [Giu] │
└─────────────────────────────────────────┘
```

### 5.3 CIC Rules

| # | Rule | Specification |
|---|---|---|
| R1 | **Tối đa 1 CIC/lần mở app** | Không carousel. Không stack. Chỉ 1 message hiển thị mỗi lần user vào Home. |
| R2 | **Tối đa 2 dòng text** | Không paragraph. Không wall-of-text. "Chao anh Tuan! Troi sap mua. Tiem Minh Anh co mai che, dat nhe?" — đủ. |
| R3 | **Luôn có CTA button** | Mỗi CIC có primary action button. Không CIC nào chỉ là "thông báo." Phải có hành động. |
| R4 | **Không input field** | User không gõ, không nói. Chỉ tap button. |
| R5 | **Tự refresh khi có event** | Khi user mở lại app sau 2h → CIC mới nếu có gợi ý mới. Khi weather thay đổi → CIC tự cập nhật. |
| R6 | **Dismiss được** | "✕" để đóng CIC. Đóng = implicit "không quan tâm" → ghi nhận để model học. |
| R7 | **Không bao giờ pop-up** | CIC chỉ trên Home. KHÔNG hiển thị khi user đang Booking Active, Payment, QR scan. |
| R8 | **Fallback: không CIC** | Nếu không agent nào đạt confidence threshold → không CIC. Home vẫn hoạt động bình thường với hero card. |

### 5.4 CIC Trigger Logic

```
┌─────────────────────────────────────────────────────────────────┐
│                    CIC DISPLAY DECISION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT AGENTS                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Agent 1      │  │ Agent 2      │  │ Agent 4      │          │
│  │ Care Score   │  │ Quality      │  │ Demand       │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           │                                      │
│                           ▼                                      │
│                  ┌─────────────────┐                            │
│                  │ CIC GENERATOR   │                            │
│                  │                 │                            │
│                  │ 1. Xác định     │                            │
│                  │    template     │                            │
│                  │ 2. Điền slots   │                            │
│                  │    {name},      │                            │
│                  │    {merchant},  │                            │
│                  │    {weather}... │                            │
│                  │ 3. Kiểm tra     │                            │
│                  │    confidence   │                            │
│                  └────────┬────────┘                            │
│                           │                                      │
│              ┌────────────┴────────────┐                        │
│              ▼                         ▼                        │
│     confidence > 0.7           confidence < 0.7                │
│              │                         │                        │
│              ▼                         ▼                        │
│     ┌────────────────┐       ┌────────────────┐               │
│     │ SHOW CIC       │       │ HIDE CIC       │               │
│     │ on Home screen │       │ (no card shown)│               │
│     └────────────────┘       └────────────────┘               │
│                                                                  │
│  PRIORITY ORDER (if multiple agents qualify):                   │
│  1. Wash reminder (Agent 1) — highest value                     │
│  2. Gio Vang alert (Agent 4)                                    │
│  3. Cross-sell (Agent 6, P2)                                    │
│  4. Maintenance reminder (Agent 1 extended, P1)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.5 CIC Template Library

**P0 Templates (3 templates, rule-triggered):**

| ID | Trigger Condition | Template Text | CTA | Destination |
|---|---|---|---|---|
| T1 — Wash Reminder + Rain | `recommendation_score > 2.0` AND `weather_rain_24h = true` | "Chao {name}! 🌧 Troi sap mua to vao {time_window}. {top_merchant} co mai che, con {bays} bay trong. Dat nhe?" | "Đặt ngay" | Merchant Detail ({top_merchant}) |
| T2 — Wash Reminder (Dry) | `recommendation_score > 2.0` AND `weather_rain_24h = false` | "Chao {name}! Xe {plate} da {days} ngay chua rua. {top_merchant} tren duong ve con {bays} bay, cho ~{wait} phut." | "Đặt ngay" | Merchant Detail ({top_merchant}) |
| T3 — Gio Vang Alert | `gio_vang_active = true` AND `current_time in gio_vang_window` AND `user_proximity_km < 2` | "⚡ Gio Vang! {merchant} giam {discount}% tu {start}-{end}. Con {bays} bay." | "Đặt Gio Vang" | Merchant Detail ({merchant}) |

**P1 Templates (7 additional, personalized timing):**

| ID | Trigger Condition | Context |
|---|---|---|
| T4 — Post-Rain | `weather_rain_24h = false` AND `rained in last 48h` | "Vua mua xong, xe ban co the bi ban. {merchant} gan day con bay." |
| T5 — Weekend | `day_of_week IN (Friday, Saturday)` AND `morning window` | "Cuoi tuan roi! Rua xe truoc khi di choi? {merchant} con {bays} bay." |
| T6 — Maintenance | `days_since_last_maintenance_related_booking > 90` | "Da 3 thang tu lan bao duong gan nhat. Kiem tra nhanh?" |
| T7 — Route Changed | `new_route_pattern_detected = true` | "Hom nay ban di duong khac. {merchant} tren duong moi con bay." |
| T8 — Hot Day | `temperature > 35C` | "Troi nong qua! Rua xe giai nhiet? {merchant} co {bays} bay trong." |
| T9 — Streak | `consecutive_weekly_bookings > 3` | "🎉 Ban da rua xe 3 tuan lien tiep! Tiet kiem 10% lan tiep theo." |
| T10 — Comeback | `days_since_last_booking > 30` | "Lau roi khong gap! Xe ban da {days} ngay chua rua. Quay lai nhe?" |

---

## 6. Proactive Push Notification Intelligence

### 6.1 Push Decision Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                    PUSH DECISION ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT SIGNALS (evaluated per user, every 15 min)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Agent 1      │  │ Agent 4      │  │ Weather API  │          │
│  │ Care Score   │  │ Demand Fit   │  │ Rain 24h?    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           │                                      │
│                           ▼                                      │
│                  ┌─────────────────┐                            │
│                  │ SCORING ENGINE  │                            │
│                  │                 │                            │
│                  │ push_score =    │                            │
│                  │   w1 × care    │                            │
│                  │ + w2 × demand  │                            │
│                  │ + w3 × weather │                            │
│                  │ + w4 × history │                            │
│                  └────────┬────────┘                            │
│                           │                                      │
│              ┌────────────┴────────────┐                        │
│              ▼                         ▼                        │
│     push_score > 0.7            push_score < 0.7               │
│              │                         │                        │
│              ▼                         ▼                        │
│     ┌────────────────┐       ┌────────────────┐               │
│     │ SEND PUSH      │       │ QUEUE          │               │
│     │ + schedule at  │       │ Re-evaluate     │               │
│     │ optimal time   │       │ in 30 min       │               │
│     └────────┬───────┘       └────────────────┘               │
│              │                                                   │
│              ▼                                                   │
│     ┌────────────────────────────────────────┐                 │
│     │ PUSH DELIVERY                          │                 │
│     │ - FCM primary (Android + iOS)          │                 │
│     │ - In-app fallback (silent notif)       │                 │
│     │ - Zalo fallback (merchant only)        │                 │
│     │ - Track: delivered, opened, converted  │                 │
│     └────────────────────────────────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Anti-Spam Rules (Enforced at Engine Level)

| # | Rule | Rationale |
|---|---|---|
| AS1 | Max 2 pushes per user per day | Prevent notification fatigue |
| AS2 | Min 4 hours between pushes | Contextual spacing |
| AS3 | Never push 10pm-6am | Respect sleep hours |
| AS4 | If last 3 pushes ignored → cooldown 48h | User is not interested right now |
| AS5 | If user dismissed push (swiped away) → same template cooldown 7 days | Respect explicit disinterest |
| AS6 | If user opted out of notifications → only in-app notifications | Respect user choice |
| AS7 | No push while user has active booking | Don't distract during active service |

### 6.3 Push Personalization Levels

| Level | Description | Phase | Example |
|---|---|---|---|
| L1 — Segment | Push theo user segment (commute window, vehicle type) | P0 | "Xe SUV cua ban can rua gam..." |
| L2 — Personalized | Push theo individual route + personal history | P0 | "Anh Tuan, tren duong Nguyen Trai hom nay..." |
| L3 — Predictive | Timing from VETC pattern prediction, not fixed windows | P0 | Push lúc 17:05 vì user thường qua toll lúc 17:15 |
| L4 — Contextual | Push factoring real-time context (weather, traffic, Gio Vang) | P0 | "Sap mua to vao chieu nay..." |
| L5 — Behavioral | Push timing adapted from individual engagement history | P1 | User A opens at 8am → push at 7:55am |
| L6 — Sentiment-Aware | Push tone adapted from user sentiment profile | P4 | LLM-generated tone variation |

---

## 7. Silent AI Actions

Silent AI Actions are decisions the AI makes with zero user-visible UI — neither notification nor screen element. Users and merchants experience the result without knowing AI was involved.

### 7.1 Silent AI Actions Catalog

| # | Action | Agent | Trigger | Frequency | Result |
|---|---|---|---|---|---|
| S1 | Optimal bay assignment | Agent 3 | New booking received | Per booking | Consumer sees "Bay 2" in booking. Merchant sees bay color change. |
| S2 | Merchant ranking update | Agent 2 | After each booking completion | Per booking | Merchant order in list silently changes. Higher quality merchants rise. |
| S3 | Stale slot detection | Agent 3 | Cron job | Every 15 min | Merchant >2h without update → hidden from recommendations. Ops receives alert. |
| S4 | ETA recalculation | Agent 3 | During active navigation | Every 30 sec | ETA on Booking Active updates. Merchant sees updated ETA. |
| S5 | Discount suggestion | Agent 7 (P2) | Daily batch | Once/day | Merchant sees suggestion card in Slot Management (accept/reject). |
| S6 | Quality drift detection | Agent 2 | Weekly batch | Once/week | Score drops below threshold → ops alert. Merchant NOT notified (prevents demotivation). |
| S7 | Anomaly pattern detection | Agent 5 (P2) | Daily batch | Once/day | Photos flagged → ops review queue. Merchant NOT notified (prevents adversarial behavior). |
| S8 | User profile auto-update | Agent 1, 6 | After each booking | Per booking | Last wash date, preferred merchants, preferred times, price sensitivity — silently updated. |

### 7.2 Silent AI Principles

| # | Principle | Description |
|---|---|---|
| P1 | **No notification** | Silent actions never send a push or in-app notification. |
| P2 | **No confirmation** | Never "AI has assigned you to Bay 2. Confirm?" — just show "Bay 2." |
| P3 | **No explanation** | Never "Bay 2 was selected because..." — just show the result. |
| P4 | **Always undoable** | AI assigns Bay 2. User can still choose Bay 1 manually. Implicit correction. |
| P5 | **Always logged** | Every silent action logged in `agent_decisions` table with input, output, confidence, and outcome. Ops dashboard for audit. |

---

## 8. Data Flywheel — Compounding Moat

### 8.1 Flywheel Mechanics

```
╔══════════════════════════════════════════════════════════════════╗
║                    TRUECARE DATA FLYWHEEL                        ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │                    1 TRANSACTION                            │ ║
║  │  Booking held → Check-in → Photos → Payment → Rating       │ ║
║  └────────────────────────┬────────────────────────────────────┘ ║
║                           │                                       ║
║                           ▼                                       ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │              DATA CAPTURED (per transaction)                │ ║
║  │                                                             │ ║
║  │  Stream A: Route segment, timing, detour distance           │ ║
║  │  Stream B: Photos (before/after), actual duration,          │ ║
║  │            rating sentiment, complaint (if any),            │ ║
║  │            rebook (if any)                                  │ ║
║  │  Stream C: Slot utilization %, merchant response time,      │ ║
║  │            Gio Vang active? discount % applied              │ ║
║  └────────────────────────┬────────────────────────────────────┘ ║
║                           │                                       ║
║                           ▼                                       ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │              MODELS IMPROVE                                 │ ║
║  │                                                             │ ║
║  │  Agent 1: timing prediction better calibrated              │ ║
║  │  Agent 2: quality score more predictive of real outcomes   │ ║
║  │  Agent 3: duration prediction more accurate                │ ║
║  │  Agent 4: demand targeting precision increases             │ ║
║  │  Agent 5: anomaly detection more precise (P2)              │ ║
║  │  Agent 6: recommendations more relevant (P2)               │ ║
║  │  Agent 7: pricing more optimal (P2)                        │ ║
║  └────────────────────────┬────────────────────────────────────┘ ║
║                           │                                       ║
║                           ▼                                       ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │              UX IMPROVES                                    │ ║
║  │                                                             │ ║
║  │  Push timing chính xác hơn → open rate +30%                │ ║
║  │  Ranking chính xác hơn → conversion rate +15%              │ ║
║  │  Wait time chính xác hơn → complaint rate -40%             │ ║
║  │  Gio Vang targeting chính xác hơn → fill rate +25%         │ ║
║  └────────────────────────┬────────────────────────────────────┘ ║
║                           │                                       ║
║                           ▼                                       ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │              MORE TRANSACTIONS                              │ ║
║  │                                                             │ ║
║  │  UX tốt hơn → user quay lại → nhiều transaction hơn        │ ║
║  │  → loop tiếp tục → moat dày hơn                            │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ════════════════════════════════════════════════════════════     ║
║  P0: 300 users × 1 booking/user/month = ~300 data points/mo      ║
║  P1: 5K users × 2 bookings/user/month = ~10K data points/mo     ║
║  P2: 20K users × 2.5 bookings = ~50K data points/mo → ML VIABLE ║
╚══════════════════════════════════════════════════════════════════╝
```

### 8.2 Flywheel Activation Timeline

| Phase | Timeline | Active Users | Monthly Transactions | Cumulative Data | AI Capability Unlocked |
|---|---|---|---|---|---|
| P0 Launch | M0 | 0 | 0 | 0 | Rule-based agents (1, 2, 3, 4) active |
| P0 Month 1 | M1 | ~200 | ~200 | 200 | Rule weights tuned from real data |
| P0 Month 2 | M2 | ~400 | ~400 | 600 | Confidence intervals calculable |
| P0 Month 3 | M3 | ~600 | ~600 | 1,200 | Pilot gate evaluation. Proceed to P1 if metrics met. |
| P1 | M4-M6 | 5K | ~10K/mo | ~30K | ML training viable for Agents 1, 2, 3 |
| P2 | M7-M12 | 20K | ~50K/mo | ~300K | ML for Agents 4, 5, 6, 7. Full 7-agent stack. |
| P3 | M13-M24 | 50K+ | ~125K/mo | ~1.5M | ML v2 retrained. Deep learning for Agent 5. |
| P4 | M24+ | 100K+ | ~250K/mo | ~3M+ | LLM-augmented layer for NLP, copy generation. |

### 8.3 Three Proprietary Data Streams

| Stream | Source | Data Points | Replicability |
|---|---|---|---|
| **Stream A — VETC Mobility Intelligence** | VETC toll, parking, fuel events | Route segments, timing, frequency, direction. Coverage: 4M+ vehicles, ~2M transactions/day. | **UNREPLICABLE** — no competitor has ETC data access |
| **Stream B — Service Outcome Loop** | TrueCare bookings | Before/after photos, SOP checklist data, actual duration, rating, complaint text, rebook behavior | **24-month lag** for competitor to start loop |
| **Stream C — Merchant Performance Series** | Merchant operations | Slot freshness, peak/dead patterns, quality drift, compliance trends, payout history | **18-month lag** to build time-series |

**Compounding logic:** Stream A is a regulatory moat. Streams B and C accrete with every booking. The more Tasco scales, the thicker the data moat. This is the mechanism Tuhu and ServiceTitan used to build 10-30x revenue multiples.

---

## 9. AI Implementation Phases

### 9.1 Phase 0: Pre-Launch (Week 0-12, within main PRD timeline)

| Week | AI Deliverable | Details |
|---|---|---|
| W1-2 | `scoring_config` DB table + Admin API | All agent weights tunable via API without redeployment. Data collection pipeline initialized for Streams A, B, C. |
| W3-4 | Agent 1, 2, 3 — Rule/Algorithm v1 | Scoring formula in code, weights from DB. Dispatch algorithm in booking endpoint. |
| W5-6 | Agent 4 — Rule v1 + CIC v1 | 3 CIC templates. Push decision engine with threshold gating. Anti-spam rules enforced. |
| W7-8 | Agent decision logging infrastructure | `agent_decisions` table: agent_id, input_snapshot, output, confidence, outcome, timestamp. Foundation for A/B testing. |
| W9-10 | AI Health Dashboard (Ops) | Input freshness metrics, agent action rates, push delivery/engagement rates, score distribution histograms. |
| W11-12 | ML training data pipeline | Schema for labeled outcome data: `booking_outcome`, `actual_duration`, `complaint_resolution`, `photo_anomaly_label`. Start collecting with manual labels. |

### 9.2 Phase 1: ML Activation (Month 4-6, post-pilot gate)

| Task | Agent | Details |
|---|---|---|
| Train ML v1 | Agent 1 | XGBoost timing predictor. Features from Stream A + B. Train on ~1,200 labeled outcomes. A/B test vs rule. |
| Train ML v1 | Agent 2 | Ridge regression quality scorer. Train on complaint outcome labels. A/B test ranking conversion. |
| Train ML v1 | Agent 3 | Duration prediction model (XGBoost). Feed improved estimates into existing dispatch algorithm. |
| CIC v2 | CIC | 10 templates. ML selects optimal template + timing per user based on engagement history. |
| Push engagement model | Push | ML predicts `P(user_opens_push)` for each user. Prioritize high-propensity users. |
| Model monitoring infra | All | Prometheus metrics: prediction distribution drift, feature importance stability, A/B test dashboard. |

### 9.3 Phase 2: Full Stack (Month 7-12)

| Task | Agent | Details |
|---|---|---|
| Train ML v1 | Agent 4 | Logistic regression propensity model for Gio Vang targeting. A/B test fill rate. |
| Train ML v1 | Agent 5 | Siamese CV network (ResNet-50) on labeled photo pairs. Deploy on-premise edge server. Integration test with complaint workflow. |
| Train ML v1 | Agent 6 | Hybrid recommender (Collaborative Filtering + Content-Based). Cold-start heuristics. |
| Train ML v1 | Agent 7 | Contextual bandit for Gio Vang pricing. Explore/exploit with merchant guardrails. |
| CIC ranking ML | CIC | ML selects which CIC template to show from multiple eligible candidates. |
| A/B testing framework | All | Multi-armed bandit for agent parameter optimization. Auto-allocate traffic to best variant. |

### 9.4 Phase 3-4: Advanced AI (Month 13-24+)

| Task | Details |
|---|---|
| Agent 1-7 ML v2 | Retrain all models on larger dataset. Deep learning for Agent 5 (Vision Transformer). Transformer for Agent 1 (time-series attention). |
| LLM Pipeline (P4) | GPT-4o-mini / Claude Haiku for: Complaint NLP analysis, personalized push copy generation, weekly ops report generation, merchant onboarding Q&A. Human-in-the-loop review for all generated content. |
| Real-time ML serving | Move from batch prediction → real-time feature serving with feature store. |
| Federated Learning evaluation | Assess if privacy-preserving ML is needed for multi-tenant merchant data. |

---

## 10. AI Success Metrics & Health Dashboard

### 10.1 Per-Agent Performance Metrics

| Agent | Primary Metric | P0 Target (Rule) | P1+ Target (ML) | Measurement Method |
|---|---|---|---|---|
| A1 — Care Timing | Push-to-booking conversion rate | >3% | >5% | (bookings from push) / (pushes delivered) |
| A2 — Quality Score | Spearman correlation: score vs complaint rate | r < -0.3 | r < -0.6 | Monthly correlation calculation |
| A3 — Slot Dispatch | Wait-time accuracy (±15min) | 70% of bookings | 80% of bookings | abs(actual_wait - predicted_wait) <= 15min |
| A4 — Demand Shaping | Dead-hour fill rate uplift | >15% vs baseline | >30% vs baseline | fill_rate_with_gio_vang / fill_rate_baseline_same_hour |
| A5 — Photo Anomaly (P2) | Ops review time saved | N/A | >70% | (manual_review_time - auto_screened_time) / manual_review_time |
| A6 — Cross-Sell (P2) | Attach rate uplift | N/A | >10 pp | % bookings with add-on service |
| A7 — Dynamic Pricing (P2) | Revenue per merchant uplift | N/A | >8% | revenue_with_ai_price / revenue_with_fixed_price |

### 10.2 AI Health Dashboard (Ops Internal)

These metrics are visible in the ops control dashboard — never to end users:

| Panel | Metrics | Alert Condition |
|---|---|---|
| **Input Freshness** | % of agent inputs refreshed within SLA (VETC <24h, weather <1h, slots <30min) | Any stream <90% fresh → alert |
| **Agent Action Rate** | % of decisions made by agent vs fallback/default per agent | Sudden change >30% → investigate |
| **Rule vs Baseline A/B** | Conversion rate with AI scoring vs random/default baseline | AI < baseline → emergency rollback |
| **Model Drift** | KL divergence of input feature distributions over 7-day windows | Divergence > threshold → retrain trigger |
| **Push Health** | Delivery rate, open rate, opt-out rate per notification type | Opt-out rate >5%/month → review push frequency |
| **Agent Confidence Distribution** | Histogram of confidence scores per agent per day | Mean confidence dropping >20% → investigate input data quality |
| **Data Flywheel Velocity** | New labeled data points per agent per week | Velocity dropping → investigate data pipeline |

### 10.3 Agent Decision Audit Table

Every AI decision is logged to `agent_decisions`:

```sql
CREATE TABLE agent_decisions (
  id UUID PRIMARY KEY,
  agent_id VARCHAR(50) NOT NULL,        -- e.g., 'care_timing_predictor'
  agent_version VARCHAR(20) NOT NULL,   -- e.g., 'rule_v1', 'ml_v2'
  input_snapshot JSONB NOT NULL,        -- Full input features at decision time
  output JSONB NOT NULL,                -- Decision output (score, action, assignment)
  confidence FLOAT,                     -- 0.0-1.0
  user_id UUID,                         -- NULL for merchant-level decisions
  merchant_id UUID,                     -- NULL for user-level decisions
  booking_id UUID,                      -- NULL if not booking-related
  outcome JSONB,                        -- Actual outcome (filled later, e.g., 'booked': true)
  created_at TIMESTAMP DEFAULT NOW(),
  outcome_at TIMESTAMP                  -- When outcome was recorded
);

CREATE INDEX idx_agent_decisions_agent_created ON agent_decisions(agent_id, created_at);
CREATE INDEX idx_agent_decisions_outcome_null ON agent_decisions(created_at) WHERE outcome IS NULL;
```

---

## 11. AI Governance & Ethics

### 11.1 Data Governance (→ Business Proposal Section 15.6)

| Concern | Mechanism |
|---|---|
| **Consent** | Explicit opt-in per data stream. Granular toggles in VETC app settings. Decree 13/2023/NĐ-CP compliant. |
| **Data Retention** | Route data: 24 months. Service evidence: 12 months. Complaint records: 36 months. |
| **Anonymization** | Vehicle plate hashed for ML training. PII stripped from analytics datasets. |
| **Cross-Border** | All data hosted in Vietnam (Decree 53/2022/NĐ-CP). No data leaves Vietnam for AI processing. |
| **Merchant Data Isolation** | Merchant only sees own data. Tenant isolation enforced at RLS level. |
| **Audit Log** | All data access logged. Quarterly security review. |

### 11.2 AI-Specific Governance

| Concern | Mechanism |
|---|---|
| **Model Bias** | Monitor agent output distribution across user segments (vehicle type, location, booking frequency). Flag if any segment has systematically worse recommendations. |
| **Merchant Fairness** | Agent 2 (Quality Score) must not penalize new merchants with low data volume. Cold-start scores use Bayesian prior with regression to mean. |
| **Explainability** | Every agent decision logged with full input snapshot. Ops can query: "Why was user X recommended merchant Y?" |
| **Human Override** | All AI decisions are overridable. Booking dispatch: user can change bay. Ranking: user can browse all merchants. Pricing: merchant must explicitly accept. |
| **Model Rollback** | Every model version stored. If ML v2 underperforms rule v1 → rollback within 5 minutes via feature flag. |
| **Adversarial Robustness** | Agent 5 (Photo Anomaly): monitor for adversarial image manipulation attempts. Agent 7 (Pricing): guardrails prevent exploitation by merchants gaming the bandit. |

### 11.3 What AI NEVER Does

| Prohibition | Rationale |
|---|---|
| **Never blocks a core user action** | AI output is suggestion. User can always ignore and proceed manually. |
| **Never exposes raw scores to consumers** | Merchant quality score is internal. Consumers see ranking order, not numbers. |
| **Never makes pricing decisions without merchant consent** | Agent 7 suggests. Merchant accepts/rejects. |
| **Never sends user data to external AI providers** | On-premise ML. CV on edge server. LLM only for non-PII text in P4. |
| **Never generates fake evidence** | AI detects anomalies. AI never creates, modifies, or synthesizes service photos. |
| **Never publicly shames merchants** | Quality alerts are private to merchant and ops. No public leaderboard. |

---

## 12. World-Class UX Compliance Checklist

Every AI touchpoint MUST pass this checklist before shipping:

| # | Standard | Status |
|---|---|---|
| UX1 | User can complete core task (book, pay, rate) with AI completely disabled? | ✅ Yes — default ranking, manual bay selection always available |
| UX2 | AI output only shown when confidence exceeds threshold? | ✅ Yes — CIC and push gated on score > threshold |
| UX3 | User can override any AI decision in 1 tap? | ✅ Yes — choose different merchant, different bay, dismiss CIC |
| UX4 | AI action never blocks core flow? | ✅ Yes — AI is suggestion layer, never a gate |
| UX5 | User never sees "AI processing" loading state? | ✅ Yes — all inference pre-computed or <50ms |
| UX6 | Graceful fallback if AI service is down? | ✅ Yes — rule-based defaults, random ranking fallback |
| UX7 | AI requires no additional permissions beyond what's already collected? | ✅ Yes — no new data collection |
| UX8 | AI never demotivates merchants (no public shaming)? | ✅ Yes — quality score private. Ranking implicit. |
| UX9 | AI has anti-spam rules enforced at engine level? | ✅ Yes — max 2 pushes/day, cooldown logic |
| UX10 | Complete audit trail for every AI decision? | ✅ Yes — `agent_decisions` table logs all |
| UX11 | Vietnamese-first copy? All AI-generated text in Vietnamese? | ✅ Yes — templates are Vietnamese. LLM prompts are Vietnamese. |
| UX12 | Tested at 320px width? CIC text fits on small screens? | ✅ Pending — must be verified during Week 9-10 visual QA |

---

## 13. Integration Points with Existing PRD

### 13.1 Mapping to `09-product-requirements-document.md`

| Main PRD Section | AI Spec Section | Integration Detail |
|---|---|---|
| **Section 1 — Executive Summary** | Section 1, 2.3 | Add "AI-native ServiceOS" to one-line. Mention 7 agents. |
| **Section 3 — Product Vision** | Section 2.3 | Add Section 3.4 "The AI Promise." |
| **Section 5.1 M5 — Recommendation** | Section 4.2, 4.3, 4.4, 4.5 | Expand from 1 formula → 4 P0 agents with full specs. |
| **Section 6.2 — Home Screen** | Section 5 | Add CIC card position above hero recommendation. |
| **Section 10 — Notification System** | Section 6 | Add push decision engine diagram. Add anti-spam rules table. |
| **Section 11 — Non-Functional** | — | Add AI inference latency SLA: <50ms real-time, <1s batch. |
| **Section 15 — Success Metrics** | Section 10 | Add AI health metrics table. |
| **Section 16 — Implementation Plan** | Section 9 | Add AI milestones to each week block. |
| **Section 20 — Appendix** | Section 16 | Add AI Glossary entries. |

### 13.2 Screen Integration Points

| Screen (from PRD) | AI Surface | Agent |
|---|---|---|
| Home (C1) | CIC card above hero recommendation | Agent 1, 2, 4, 6 |
| Home (C1) | Merchant ranking order | Agent 2 |
| Map (C2) | Pin ranking order | Agent 2 |
| Booking Active (C4) | Bay assignment display | Agent 3 |
| Booking Active (C4) | ETA updates | Agent 3 |
| Queue Board (M1) | Bay auto-assignment (color change) | Agent 3 |
| Queue Board (M1) | Quality score display | Agent 2 |
| Slot Management (M2) | Discount suggestion card (P2) | Agent 7 |
| Push Notification (all) | Timing + content | Agent 1, 4 |

### 13.3 Backend Service Integration

| Backend Service (from `05-engineering-plan.md`) | AI Responsibility |
|---|---|
| **Intelligence Worker (Celery)** | Hosts Agent 1, 2, 4 batch scoring cycles. Pulls data from Streams A, B, C. Pushes results to CIC generator and Push Decision Engine. |
| **Notification Worker** | Consumes push queue from Push Decision Engine. Delivers via FCM/Zalo. Tracks delivery and engagement. |
| **Main API (FastAPI)** | Hosts Agent 3 dispatch algorithm (in booking endpoint). Serves CIC content to mobile. Admin API for `scoring_config` tuning. |
| **Database (Supabase PostgreSQL)** | `scoring_config` table. `agent_decisions` table. ML training data schemas. |
| **Redis Cloud** | Pub/sub for real-time agent output distribution (CIC refresh, push queue). |

---

## 14. LLM Strategy — When & Why

### 14.1 LLM Decision Framework

LLM is used **only** when ALL three conditions are met:

1. The task involves **unstructured natural language** (text understanding or generation)
2. The task is **not latency-sensitive** (batch or async, not real-time)
3. The task **cannot be accomplished** with a simpler approach (template, regex, ML classifier)

### 14.2 Legitimate LLM Use Cases (P4 Only)

| # | Use Case | Problem Solved | Phase | Model | Cost Est. |
|---|---|---|---|---|---|
| L1 | **Complaint NLP Analysis** | Ops reads 50+ complaints/week manually. LLM extracts: category, severity, sentiment, suggested resolution. Ops only reviews + approves. | P4 | GPT-4o-mini | ~$0.001/complaint |
| L2 | **Personalized Push Copy** | Template text is generic. LLM generates personalized copy: "Anh Tuan, xe Vios cua anh da 8 ngay chua rua sau con mua tuan truoc..." — within template constraint. | P4 | GPT-4o-mini | ~$0.001/push |
| L3 | **Merchant Onboarding Q&A** | Merchant asks "Tôi nên đặt giá bao nhiêu cho dịch vụ này?" — LLM answers from market data + catalog. | P4 | Claude Haiku | ~$0.005/conversation |
| L4 | **SOP Checklist Adaptation** | Merchants have different bay layouts. LLM customizes SOP: "Bay 1 của bạn ở ngoài trời, thêm bước che nắng." | P4 | Claude Haiku | ~$0.01/customization |
| L5 | **Weekly Ops Report Generation** | Ops receives a prose summary: metrics, trends, anomalies, recommendations — generated from structured data. | P4 | GPT-4o-mini | ~$0.05/report |

**Total P4 LLM cost estimate:** ~$50-100/month for all 5 use cases at P4 scale.

### 14.3 Where LLM Is Explicitly Rejected

| Rejected Use Case | Why Rejected | Alternative |
|---|---|---|
| **Conversational Booking Agent** | Increases interaction (4+ turns vs 1 tap). Latency 500ms-2s breaks instant UX. Hallucination risk for prices/times/addresses. | CIC card with 1-tap CTA (Section 5) |
| **LLM for Recommendation Logic** | Collaborative filtering + content-based ML is faster, cheaper, deterministic. LLM hallucinates recommendations. | Agent 6 Hybrid Recommender (Section 4.7) |
| **LLM for Pricing** | Pricing is constrained numerical optimization. LLM is not designed for this. | Agent 7 Contextual Bandit (Section 4.8) |
| **LLM for Dispatch** | Dispatch is deterministic resource allocation. LLM is stochastic — same input, different output. Unacceptable. | Agent 3 Algorithm (Section 4.4) |
| **LLM for Photo Analysis** | Privacy: photos cannot leave Vietnam. Cost: $0.01-0.03/image. Latency: 2-5s. | Agent 5 On-Premise CV (Section 4.6) |
| **LLM Chatbot for Merchant** | Merchant hands are wet. Outdoors. Noisy. They need glance-based interaction, not text chat. | Ambient dashboard mode (PRD Section 7.2) |

---

## 15. Anti-AI-Washing Safeguards

The business proposal (`07-business-proposal-en.md:296`) warns: "If AI is only a chatbot or recommendation veneer → AI washing." These safeguards ensure TrueCare never crosses that line.

### 15.1 Five-Point AI Moat Test

Every AI feature must pass all 5 criteria. If any fails → not AI moat → AI washing → reject or redesign.

| # | Criterion | Definition | Verification Method |
|---|---|---|---|
| 1 | **Workflow Intervention** | AI intervenes at an action-level decision point in a core workflow. Not just displaying information. | Can you name the specific workflow step where AI changes the outcome? Booking dispatch, not "shows recommendations." |
| 2 | **Data Exhaust Loop** | Each transaction produces data that feeds back into model retraining, making the AI better over time. | Does the model have a retrain pipeline? Is new labeled data accumulated from each action? |
| 3 | **Proprietary Data** | AI uses data that only Tasco/VETC has access to — not public, not purchasable. | Can a competitor replicate this with publicly available data? If yes → not a moat. |
| 4 | **Measurable Impact** | AI produces a quantifiable KPI improvement >10% vs the non-AI baseline. | Can you measure the delta? A/B test vs rule-based or random baseline. |
| 5 | **Replicability Barrier** | Competitor would need 2+ years and $30M+ to replicate this AI capability. | What's the data accumulation period? What proprietary assets are required? |

### 15.2 Per-Agent Moat Validation

| Agent | #1 Workflow | #2 Data Loop | #3 Proprietary | #4 Impact | #5 Barrier | All 5? |
|---|---|---|---|---|---|---|
| 1 — Care Timing | ✅ Push trigger | ✅ Booked→retrain | ✅ VETC route | ✅ +30-50% | ✅ 2-3 years | ✅ |
| 2 — Quality Score | ✅ Ranking | ✅ Complaint→retrain | ✅ Service outcome | ✅ -40% defect | ✅ 2-3 years | ✅ |
| 3 — Slot Dispatch | ✅ Bay assign | ✅ Duration→retrain | ✅ Merchant perf | ✅ -80% overbook | ✅ 12-18 months | ✅ |
| 4 — Demand Shaping | ✅ Push target | ✅ Convert→retrain | ✅ Route+merchant | ✅ +15-40% | ✅ 18-24 months | ✅ |
| 5 — Photo Anomaly | ✅ QA flag | ✅ Label→retrain | ✅ Photo pairs | ✅ -70% review | ✅ 24 months | ✅ |
| 6 — Cross-Sell | ✅ CRM trigger | ✅ Purchase→retrain | ✅ User history | ✅ +10-25pp | ✅ 24 months | ✅ |
| 7 — Dynamic Pricing | ✅ Price suggest | ✅ Fill→retrain | ✅ Fill series | ✅ +8-15% | ✅ 18-24 months | ✅ |

**Verdict: 7/7 agents pass. Zero AI washing in TrueCare.**

### 15.3 Anti-Pattern Watchlist

| Anti-Pattern | Why It's AI Washing | TrueCare's Position |
|---|---|---|
| "AI-powered search" | Search is a solved problem. Adding LLM adds latency and hallucination risk. | AI recommends before user searches. Search is fallback browsing on Map screen. No AI in search. |
| "AI chatbot assistant" | Increases interaction, adds latency, unreliable for booking-critical data. | CIC card — proactive, 1-tap, no conversation. |
| "AI-generated insights dashboard" | If insights are just averaged metrics, it's SQL + charts, not AI. | AI Health Dashboard is for ops, not end users. Shows model performance, not vanity metrics. |
| "AI personalization" with just name insertion | "Dear {name}" is mail merge, not AI. | L1-L4 personalization: individual route patterns, timing prediction, behavioral adaptation. |
| "AI that learns from you" with no retrain pipeline | Claiming ML without actual model retraining. | Explicit retrain cadences per agent. Labeled data pipeline. Model versioning. |

---

## 16. Glossary

| Term | Definition |
|---|---|
| **AI-Native** | AI is the operating infrastructure, not a feature bolted on. AI intervenes in core workflows, not just the presentation layer. |
| **AI Washing** | Claiming AI without meeting the 5-point moat test. Chatbot veneer. Recommendation carousel. "Powered by AI" badges on SQL queries. |
| **Proactive Intelligence** | System initiates action based on prediction. User confirms with one tap. Opposite of reactive (user searches, browses, asks). |
| **Agent** | An AI component that makes a specific action-level decision in a core workflow. 7 agents in TrueCare. |
| **CIC (Contextual Intelligence Card)** | The only visible AI surface on the consumer app. A short text card on Home that appears when AI has a high-confidence recommendation. |
| **Silent AI Action** | An AI decision with zero user-visible UI. User experiences the result without knowing AI was involved. |
| **Data Flywheel** | The compounding loop: more transactions → more data → better AI → better UX → more transactions. |
| **Data Exhaust** | Data generated as a byproduct of normal operations that feeds back into AI training. |
| **Idempotency** | A system property where duplicate requests produce exactly one business result. Critical for payment and booking state transitions. |
| **Outbox Pattern** | Events written to database before publishing to message queue. A sweeper catches missed events. |
| **Dead Letter Queue** | A holding queue for failed tasks after all retries exhausted, enabling inspection and manual recovery. |
| **Significant-Change GPS** | Battery-efficient location mode waking GPS only on meaningful movement (~500m). |
| **RLS (Row-Level Security)** | PostgreSQL feature restricting row access per policy, enforced at database level. |
| **FCM** | Firebase Cloud Messaging — push notification delivery for Android and iOS. |

---

## Document Control

| Field | Value |
|---|---|
| **Document ID** | AI-TRUECARE-SERVICEOS-20260426 |
| **Version** | 1.0 |
| **Status** | Planning COMPLETE. Integrates with PRD v2.0 (including Section 8: VETC Loyalty Ecosystem Integration). |
| **Author** | AI/Product Team |
| **Source** | `business-proposal/07-business-proposal-en.md` Section 15 (Data Moat & AI Moat Blueprint) |
| **Integrates With** | `09-product-requirements-document.md` v2.0 (including Section 8: VETC Loyalty Ecosystem Integration) |
| **Last Updated** | 2026-04-26 |
| **Next Review** | After P0 pilot data validates flywheel assumptions. |

---

> "TrueCare is an AI-native ServiceOS — not because it has AI features, but because AI is the operating system. Seven agents, three data streams, one compounding moat. The user never sees the AI. They only feel that the product knows what they need before they ask."
