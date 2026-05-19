# TrueCare New

This folder is the porting knowledge root for the TrueCare project.

Start here:

- `knowledge/00-porting/` contains the current porting plan and test matrix.
- `knowledge/01-product/` contains product, PRD, design, MVP, and ServiceOS source material.
- `knowledge/02-business/` contains the retained business proposal context.
- `knowledge/INDEX.md` records every copied artifact, original source path, destination path, and purpose.
- `INFRA.md` is the single minimal infrastructure plan for local porting with Supabase.
- `apps/api` contains the FastAPI backend, implemented auth/marketplace/phase 2-3/merchant admission/local route-closure routes, and local RLS/audit/correctness gates.
- `apps/mobile` contains the Expo Router shell with auth/profile and basic merchant onboarding data wiring.
- `apps/ops-web` contains the Vite React Ops shell with admissions mutation wiring and read surfaces for commission, complaints, network health, growth/eKYC, and audit.
- `packages/api-client` contains the generated TypeScript API client.
- `docs/migration-map-v1.md` maps the 37 legacy schema tables into the Python port.
- `docs/local-e2e-runbook.md` describes local-only API/Ops/Mobile verification.
- `docs/e2e-verification-prerequisites.md` lists local, runner, Supabase, and production-like E2E prerequisites.
- `Makefile` exposes readiness gates and local scaffold commands.

All retained source documents were copied, not moved.

Useful commands:

Python-backed checks install and run through the repo-local `.venv`; do not install Python packages globally for this port.

```bash
make venv
make infra-prereqs.check
make secret-leak.check
make route-test-matrix.check
make mobile.route-files.check
make ops.route-files.check
make migration.dry-run
make seed.plan.check
make shadow-read.check
make db.up
make db.migrate
make api.test
make api.integration
make api.openapi
make client.generate
make worker.once
make local.e2e.prereqs
make local.qa.fixtures
make local.qa.smoke
pnpm -r typecheck
```

Run local apps with `make local.api`, `make local.ops`, and `make local.mobile`; verify running API/Ops endpoints with `make local.app.check`.
