# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Context

This repo is the TrueCare / Wash3000 project for Tasco: an intelligence-led car-care network that uses VETC route context to recommend car-care actions and route users to merchants.

Read project sources in this order before making product or architecture decisions:

1. `07-business-proposal-en.md` - canonical funded business baseline.
2. `01-challenge-and-context.md` - consolidated source of truth for business challenge, strategy, roadmap, operations, slot hold, payment, complaints, failure modes, and service catalog.
3. `09-product-requirements-document.md` - canonical P0-Final product spec, with caveats. It currently validates a standalone GPS/QR booking loop and does not validate the funded VETC route-intelligence moat until Section 20.4 passes.
4. `09-product-requirements-document.md` Section 8 — current QR-first payment architecture and VETC Loyalty deferral. Do not treat it as an active P0 Loyalty source; funded VETC-native loyalty behavior remains in `business-proposal/07-business-proposal-en.md` §10.9 until restored to the PRD.
5. `05-engineering-plan.md` - historical engineering source, currently absent from this worktree. Until restored, use PRD Sections 15-18 and 21 for API/data/NFR/timeline decisions and rerun engineering review.
6. `06-design-spec.md` - source of truth for UI, navigation, states, and tokens.
7. `10-ai-native-serviceos-spec.md` - source of truth for AI-native ServiceOS planning.
8. `TODOS.md` - current execution backlog.

`00-README.md` explains how the documents fit together. `CLAUDE.md` is synced with this file for consistent cross-agent collaboration (Codex + Claude).

## Current Repo Shape

- `mobile/` is the active Expo React Native app.
- `mobile/app/` uses Expo Router with a root layout and tab routes.
- `mobile/src/design/` contains the app theme and design tokens.
- `mobile/src/i18n/` contains `react-i18next` setup and `vi`/`en` locale JSON.
- `mobile/src/types/models.ts` contains temporary shared domain types until OpenAPI generation exists.
- `mobile/src/services/api.ts` is the API entry point placeholder.
- Root `src/design/` mirrors design tokens/reference material; be careful to update the active mobile copy when changing app UI.
- `screen-artifacts/`, `slide/`, `output/`, and `tmp/` are generated/reference artifacts unless a task explicitly targets them.
- Current worktree note: many `mobile/` files may be deleted. Treat PRD screen-manifest file paths as planned target routes unless the files are restored and verified.

The design docs mention `office_hours_artifacts/wash3000-screen-specs.html`; the checked-in local screen artifact currently appears as `screen-artifacts/TrueCare-screen-specs.html`.

## Product Scope

Keep the P0 pilot bounded unless the user explicitly asks to expand scope.

Canonical P0 baseline:

- 12-20 merchants.
- 300-800 invited VETC users.
- One primary route-dense cluster in Hanoi or HCMC.
- 12-week build window, gated by 7 pre-code stage gates (G1–G7).
- Productized modules: catalog/SOP, booking, payment ledger, evidence, recommendation/growth.
- Human-operated workflows: merchant admissions, merchant daily summary/payout export, control-tower reporting/SLA/network health, complaint/refund review.
- Funded baseline inherits VETC Loyalty (no separate TrueCare currency): profile, point redemption, campaign earn, reconciliation. Current P0-Final intentionally defers those flows and must not be reported as validating the VETC-native moat until the Route Moat Gate passes.

Do not silently add P1/P2 product scope such as self-serve merchant onboarding, full Next.js Control Tower, automated refunds, full analytics, native VETC embedding, TrueCare-native loyalty currency/streaks/membership, or an 8-agent AI system. For the funded baseline, P0 loyalty means inheriting VETC Loyalty for profile, earn/burn, redemption, campaign, and reconciliation flows. For current P0-Final, those flows are explicitly deferred in PRD Section 8.

## Mobile Stack

The mobile app uses:

- Expo `~54`.
- React Native `0.81`.
- React `19`.
- Expo Router `~5`.
- TypeScript strict mode.
- `@expo/vector-icons` / Ionicons.
- `i18next` and `react-i18next`.

Important routes:

- `mobile/app/_layout.tsx` - root layout, theme provider, splash handling, stack.
- `mobile/app/(tabs)/_layout.tsx` - bottom tabs.
- `mobile/app/(tabs)/index.tsx` - Home.
- `mobile/app/(tabs)/map.tsx` - Map placeholder.
- `mobile/app/(tabs)/bookings.tsx` - Bookings placeholder.
- `mobile/app/(tabs)/profile.tsx` - Profile and language switch.

Use the `@/*` TypeScript aliases from `mobile/tsconfig.json` for source imports.

## Commands

Run mobile commands from `mobile/`:

```bash
npm install
npm run start
npm run android
npm run ios
npm run web
npm run lint
```

`npm test` is declared, but Jest is not wired yet in `package.json` or a Jest config. If adding tests, add the required Jest / React Native Testing Library setup before relying on `npm test`.

There is no root package manager configuration at the moment.

## UI And Design Rules

- Follow `06-design-spec.md` before building or changing screens.
- Consumer navigation is Home, Map, Bookings, Profile.
- The intended app is a role-based single binary; merchant flows are planned but not yet implemented.
- Use `useTheme()` and tokens from `mobile/src/design/`. Do not introduce hardcoded colors, spacing, radius, shadows, or font sizes for new UI.
- Keep the three-tier token model: primitive, semantic, component.
- Use Ionicons or the existing icon system for app UI. Do not use emoji as design elements.
- Use Vietnamese-first UX copy, with English fallback.
- Externalize new user-facing strings into both locale files: `mobile/src/i18n/locales/vi.json` and `mobile/src/i18n/locales/en.json`.
- Existing placeholder screens still contain some hardcoded text; clean that up when touching those screens.
- Preserve responsive/mobile ergonomics: safe areas, stable tab height, no overlapping text, and accessible tap targets.

## Domain Rules

- Booking slot holds are expected to last 30 minutes; see `mobile/src/constants/app.ts`.
- Booking status, bay status, payment method, merchant tier, and domain models live in `mobile/src/types/models.ts`.
- Backend contracts should eventually come from OpenAPI. Do not let mobile-only types drift far from `01-challenge-and-context.md`, the current PRD API/data sections, or a restored `05-engineering-plan.md`.
- Planned backend stack is Python/FastAPI, Supabase/PostgreSQL/Auth/RLS, Redis, S3-compatible evidence storage, FCM, and workers. Do not create a different backend stack without explicit approval.
- External services such as VETC, GoongIO, weather, VETC Wallet, push, and Supabase should be consumed through standard APIs/providers, not rebuilt.

## Data And Security

Treat these as sensitive:

- VETC identity references.
- Phone numbers.
- License plates.
- Route/location history.
- Booking/payment data.
- Before/after service photos.

Do not commit secrets or real credentials. Use environment variables for configuration. `EXPO_PUBLIC_API_URL` is currently the mobile public API base URL hook.

## Working Practices

- Check `git status --short` before editing and avoid overwriting user changes.
- Keep changes scoped to the requested task and the active P0 baseline.
- Prefer editing existing patterns over introducing new abstractions.
- For app work, update types, copy, tokens, and tests together when the behavior crosses those boundaries.
- For docs work, keep the business baseline consistent with `07-business-proposal-en.md`.
- Avoid editing `.expo/`, `node_modules/`, generated native `ios/` or `android/`, and generated artifacts unless explicitly requested.

## Verification

For mobile code changes:

1. Run `npm run lint` from `mobile/`.
2. If tests are added or configured, run `npm test` from `mobile/`.
3. For UI changes, run the Expo app on the relevant target and visually check the changed screens.

For docs-only changes, no app build is required unless the docs include generated artifacts.
