SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

## help — list available targets
help:
	@grep -hE '^## [a-zA-Z0-9_.-]+\s—' $(MAKEFILE_LIST) | sed 's/^## //' | column -t -s'—'

## infra-prereqs.check — verify minimum local tooling for fast porting
infra-prereqs.check:
	@scripts/infra/infra-prereqs-check.sh

## supabase-readiness.check — verify Supabase DB extensions, roles, Realtime, and Storage assumptions
supabase-readiness.check:
	@scripts/infra/supabase-readiness-check.sh

## secret-leak.check — scan tracked files for high-risk secret material
secret-leak.check:
	@scripts/infra/secret-leak-check.sh
