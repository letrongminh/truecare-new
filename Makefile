SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
PYTHON ?= python3
VENV := .venv
VENV_PY := $(VENV)/bin/python
VENV_MARKER := $(VENV)/.installed
LOCAL_DATABASE_URL := postgresql+asyncpg://truecare:truecare@127.0.0.1:55432/truecare
LOCAL_DATABASE_URL_SYNC := postgresql://truecare:truecare@127.0.0.1:55432/truecare

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

## supabase-readiness.check — verify Supabase DB extensions, roles, Realtime, and Storage assumptions
supabase-readiness.check:
	@scripts/infra/supabase-readiness-check.sh

## secret-leak.check — scan tracked files for high-risk secret material
secret-leak.check:
	@scripts/infra/secret-leak-check.sh

## route-test-matrix.check — verify route manifest and test matrix stay in lock-step
route-test-matrix.check:
	@$(PYTHON) scripts/checks/route_test_matrix_check.py

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
