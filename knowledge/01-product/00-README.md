# TrueCare — Intelligence-Led Car-Care Network for Tasco

## How to navigate this project

| File | Purpose | When to read |
|------|---------|-------------|
| **01-challenge-and-context.md** | **Consolidated source of truth:** business challenge, market context, strategy, scope, operating model, agent logic, slot hold, payment, complaints, failure modes, data model | Start here. This replaces the old split between challenge, strategy, and operations. |
| **05-engineering-plan.md** | Historical engineering source. **Currently absent from this worktree.** Until restored, use `09-product-requirements-document.md` Sections 15-18 and 21 for API/data/NFR/timeline decisions, then rerun engineering review. | Restore before implementation if engineering detail is needed. |
| **06-design-spec.md** | Screen specs (21 P0 app screens), ServiceOS UX model, interaction states, design tokens, navigation, accessibility, wireframes | **Source of truth for design.** Read before building any UI. |
| **business-proposal/07-business-proposal-en.md** | Funded business baseline, IC framing, lean rollout, economics, phase gates | **Source of truth for business baseline.** Read before scope or implementation decisions. |
| **business-proposal/07-business-proposal.md** | Vietnamese long-form strategy and ambition appendix | Reference only. Use for narrative depth and upside ambition, not P0 scope. |
| **09-product-requirements-document.md** | Product requirements, MVP flows, functional requirements, data model, integration gates | **Source of truth for product requirements.** |
| **10-ai-native-serviceos-spec.md** | AI-native ServiceOS architecture, agents, data flywheel, AI UX standards | **Source of truth for AI planning.** |
| **11-truecare-loyalty-ecosystem-prd.md** | Historical loyalty PRD. The current P0-Final PRD Section 8 is QR-first payment plus VETC Loyalty deferral; funded VETC-native loyalty behavior remains in `business-proposal/07-business-proposal-en.md` §10.9 until restored to the product spec. | Reference for VETC-native follow-up gate. |
| **TODOS.md** | Deferred work items with priority, effort, and context | Check before starting new work. |

## Canonical implementation baseline

The canonical funded baseline is `business-proposal/07-business-proposal-en.md`.

- **P0 Evidence Pilot:** 12-20 merchants, 300-800 invited VETC users.
- **Product scope:** 5 productized modules plus 4 human-operated workflows.
- **Implementation path:** business baseline (`business-proposal/07-business-proposal-en.md`) → consolidated source of truth (`01-challenge-and-context.md`) → product PRD (`09-product-requirements-document.md`, including the P0-Final caveat and Section 20.4 Route Moat Gate) → engineering source restoration or PRD Sections 15-18/21 fallback → design (`06-design-spec.md`) → execution (`TODOS.md`).
- **Vietnamese long-form:** `business-proposal/07-business-proposal.md` is an ambition appendix. Any higher scale targets in that file require explicit reconciliation with the English baseline before implementation.

## Key artifacts

- `office_hours_artifacts/wash3000-office-hours-sketch.png` — Original visual sketch of "Copilot Front, WashOS Core" approach
- **`screen-artifacts/TrueCare-screen-specs.html`** — **Product-safe MVP screen sketch: 21 P0 app screens, 3 P1 ops references, fallback onboarding, ServiceOS journey design, Goong.IO in-app navigation, dual-device ping, VETC Wallet + Loyalty states.** This is the definitive UI reference for development.
- `~/.gstack/projects/TASCO/designs/wireframes-20260416/wash3000-all-screens.html` — Earlier wireframe draft (superseded by screen-specs.html above)

## Review status

| Review | Status | Date |
|--------|--------|------|
| Office Hours | DONE | 2026-04-15 |
| CEO Review (Scope Expansion) | DONE | 2026-04-16 |
| Eng Review | DONE | 2026-04-16 |
| Outside Voice (Codex GPT-5.4) | DONE | 2026-04-16 |
| Design Review + ServiceOS UX Hardening (3→9/10) | DONE | 2026-04-27 |
| Design Outside Voices | DONE | 2026-04-16 |
| Lean P0 Baseline Alignment | DONE | 2026-04-25 |
| Eng Review (Lean P0 canonical plan) | DONE | 2026-04-25 |
| CEO Review (VETC-native Loyalty Ecosystem) | DONE | 2026-04-27 |
| Business Proposal Reconciliation (EN ↔ VN ↔ PRD) | DONE | 2026-04-27 |

## One-line summary

**TrueCare is an intelligence-led car-care network that uses VETC route data from 4M+ users to predict when drivers need car care and route them to the right merchant at the right time. Car wash is the entry point. Route Intelligence is the moat.**
