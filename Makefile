SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
PYTHON ?= python3
VENV := .venv
VENV_PY := $(VENV)/bin/python
VENV_MARKER := $(VENV)/.installed
LOCAL_DATABASE_URL := postgresql+asyncpg://truecare:truecare@127.0.0.1:55432/truecare
LOCAL_DATABASE_URL_SYNC := postgresql://truecare:truecare@127.0.0.1:55432/truecare
LOCAL_JWT_PRIVATE_JWK := $(CURDIR)/.local-jwt-signing-private.jwk.json
LOCAL_QA_ARTIFACT := $(CURDIR)/.local-e2e.json
LOCAL_API_BASE_URL ?= http://127.0.0.1:8000
LOCAL_API_HOST ?= 127.0.0.1
LOCAL_API_PORT ?= 8000
LOCAL_OPS_HOST ?= 127.0.0.1
LOCAL_OPS_PORT ?= 5173
LOCAL_OPS_URL ?= http://$(LOCAL_OPS_HOST):$(LOCAL_OPS_PORT)
LOCAL_MOBILE_STATUS_URL ?=

## help — list available targets
help:
	@grep -hE '^## [a-zA-Z0-9_.-]+\s—' $(MAKEFILE_LIST) | sed 's/^## //' | column -t -s'—'

## venv — create local Python venv and install API packages
venv: $(VENV_MARKER)

$(VENV_MARKER): apps/api/requirements.txt
	@$(PYTHON) -m venv $(VENV)
	@$(VENV_PY) -m pip install --upgrade pip
	@$(VENV_PY) -m pip install -r apps/api/requirements.txt
	@touch $(VENV_MARKER)

## infra-prereqs.check — verify minimum local tooling for fast porting
infra-prereqs.check:
	@scripts/infra/infra-prereqs-check.sh

## supabase-readiness.check — verify Supabase DB extensions, roles, Realtime, and Storage assumptions through .venv
supabase-readiness.check: venv
	@$(VENV_PY) scripts/infra/supabase_readiness_check.py

## secret-leak.check — scan tracked files for high-risk secret material
secret-leak.check:
	@scripts/infra/secret-leak-check.sh

## route-test-matrix.check — verify route manifest and test matrix stay in lock-step
route-test-matrix.check:
	@$(PYTHON) scripts/checks/route_test_matrix_check.py

## mobile.route-files.check — verify mandatory Expo Router files exist
mobile.route-files.check:
	@$(PYTHON) scripts/checks/mobile_route_files_check.py

## ops.route-files.check — verify mandatory Ops web route files exist
ops.route-files.check:
	@$(PYTHON) scripts/checks/ops_route_files_check.py

## migration.dry-run — verify the legacy-to-new migration dry-run plan
migration.dry-run:
	@$(PYTHON) scripts/migration/migration_dry_run.py

## seed.plan.check — verify deterministic baseline seed manifest
seed.plan.check:
	@$(PYTHON) scripts/migration/seed_baseline.py

## shadow-read.check — verify shadow-read comparison query coverage
shadow-read.check:
	@$(PYTHON) scripts/migration/shadow_read_compare.py

## api.test — run FastAPI foundation tests through the local venv
api.test: venv
	@cd apps/api && ../../$(VENV_PY) -m pytest -m "not integration"

## api.openapi — export FastAPI OpenAPI JSON for generated clients
api.openapi: venv
	@mkdir -p packages/api-client
	@cd apps/api && PYTHONPATH=. ../../$(VENV_PY) -m scripts.export_openapi > ../../packages/api-client/openapi.json

## client.generate — generate TypeScript API client from OpenAPI
client.generate: api.openapi
	@node scripts/codegen/generate-api-client.mjs packages/api-client/openapi.json packages/api-client/src/index.ts

## db.up — start local Postgres for backend integration tests
db.up:
	@docker start truecare-new-postgres >/dev/null 2>&1 || docker run --name truecare-new-postgres -e POSTGRES_USER=truecare -e POSTGRES_PASSWORD=truecare -e POSTGRES_DB=truecare -p 55432:5432 -d postgres:16 >/dev/null
	@$(MAKE) db.wait

## db.wait — wait for the local Postgres container to accept SQLAlchemy connections
db.wait: venv
	@DATABASE_URL_DIRECT="$(LOCAL_DATABASE_URL)" $(VENV_PY) scripts/checks/wait_for_db.py

## db.down — stop and remove the local Postgres container
db.down:
	@docker rm -f truecare-new-postgres >/dev/null 2>&1 || true

## db.migrate — apply Alembic migrations to local or configured Postgres
db.migrate: venv
	@cd apps/api && DATABASE_URL_DIRECT="$${DATABASE_URL_DIRECT:-$(LOCAL_DATABASE_URL)}" ../../$(VENV_PY) -m alembic upgrade head

## api.integration — run backend integration tests against local or configured Postgres
api.integration: venv
	@cd apps/api && DATABASE_URL_DIRECT="$${DATABASE_URL_DIRECT:-$(LOCAL_DATABASE_URL)}" ../../$(VENV_PY) -m pytest -m integration

## worker.once — run the worker skeleton once
worker.once: venv
	@cd apps/api && DATABASE_URL_DIRECT="$${DATABASE_URL_DIRECT:-$(LOCAL_DATABASE_URL)}" ../../$(VENV_PY) -m app.jobs.worker --once

## local.jwt — create a stable local-only JWT signing key for API, fixtures, and smoke
local.jwt: venv
	@$(VENV_PY) scripts/local/ensure_jwt_key.py --out "$(LOCAL_JWT_PRIVATE_JWK)"

## local.qa.fixtures — seed deterministic local personas and QA rows into Docker Postgres
local.qa.fixtures: db.up db.migrate local.jwt
	@DATABASE_URL_DIRECT="$${DATABASE_URL_DIRECT:-$(LOCAL_DATABASE_URL)}" JWT_SIGNING_PRIVATE_JWK="$(LOCAL_JWT_PRIVATE_JWK)" $(VENV_PY) scripts/local/qa_fixtures.py --out "$(LOCAL_QA_ARTIFACT)"

## local.qa.smoke — run local in-process API smoke against deterministic QA fixtures
local.qa.smoke: local.qa.fixtures
	@DATABASE_URL_DIRECT="$${DATABASE_URL_DIRECT:-$(LOCAL_DATABASE_URL)}" JWT_SIGNING_PRIVATE_JWK="$(LOCAL_JWT_PRIVATE_JWK)" $(VENV_PY) scripts/local/qa_smoke.py --artifact "$(LOCAL_QA_ARTIFACT)"

## local.api — run FastAPI locally with the same JWT key and Postgres as local QA
local.api: db.up db.migrate local.jwt
	@cd apps/api && DATABASE_URL_DIRECT="$${DATABASE_URL_DIRECT:-$(LOCAL_DATABASE_URL)}" JWT_SIGNING_PRIVATE_JWK="$(LOCAL_JWT_PRIVATE_JWK)" PUBLIC_API_BASE_URL="$(LOCAL_API_BASE_URL)" ../../$(VENV_PY) -m uvicorn app.main:app --reload --host "$(LOCAL_API_HOST)" --port "$(LOCAL_API_PORT)"

## local.ops — run Ops web locally against local.api
local.ops:
	@VITE_API_BASE_URL="$(LOCAL_API_BASE_URL)" pnpm --filter @truecare/ops-web dev --host "$(LOCAL_OPS_HOST)" --port "$(LOCAL_OPS_PORT)"

## local.mobile — run Expo mobile locally against local.api
local.mobile:
	@EXPO_PUBLIC_API_BASE_URL="$(LOCAL_API_BASE_URL)" pnpm --filter @truecare/mobile dev

## local.e2e.prereqs — verify required and optional local E2E tooling
local.e2e.prereqs:
	@$(PYTHON) scripts/local/e2e_prereqs_check.py

## local.e2e.gates — run the required local API/static/typecheck verification gates
local.e2e.gates:
	@$(MAKE) infra-prereqs.check
	@$(MAKE) secret-leak.check
	@$(MAKE) route-test-matrix.check mobile.route-files.check ops.route-files.check
	@$(MAKE) db.up db.migrate
	@$(MAKE) local.qa.fixtures
	@$(MAKE) local.qa.smoke
	@$(MAKE) api.test
	@$(MAKE) api.integration
	@$(MAKE) worker.once
	@$(MAKE) client.generate
	@pnpm -r typecheck
	@$(MAKE) local.qa.fixtures

## local.app.check — verify running local API and Ops web with seeded QA tokens
local.app.check:
	@$(PYTHON) scripts/local/app_health_check.py --artifact "$(LOCAL_QA_ARTIFACT)" --api-base-url "$(LOCAL_API_BASE_URL)" --ops-url "$(LOCAL_OPS_URL)" $(if $(LOCAL_MOBILE_STATUS_URL),--mobile-status-url "$(LOCAL_MOBILE_STATUS_URL)",)

## local.mobile.maestro — run the local mobile Maestro smoke when Maestro and a device are ready
local.mobile.maestro:
	@command -v maestro >/dev/null 2>&1 || { printf 'maestro CLI is required for this gate; install it before marking mobile E2E done\n' >&2; exit 1; }
	@maestro test tools/maestro/flows/p0-mobile-smoke.yaml

## local.ops.playwright — run Ops Playwright smoke against a running local Ops web
local.ops.playwright:
	@test -d node_modules/@playwright/test || { printf 'project-local @playwright/test is required; install it before marking Ops Playwright done\n' >&2; exit 1; }
	@pnpm exec playwright test apps/ops-web/tests/p0-ops.spec.ts
