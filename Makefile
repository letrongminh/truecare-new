SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

## help — list available targets
help:
	@grep -hE '^## [a-zA-Z0-9_.-]+\s—' $(MAKEFILE_LIST) | sed 's/^## //' | column -t -s'—'

## infra-prereqs.check — verify local tooling, Docker daemon, git remote, and optional cloud auth
infra-prereqs.check:
	@scripts/infra/infra-prereqs-check.sh

## supabase-readiness.check — verify Supabase DB extensions, roles, Realtime, and Storage assumptions
supabase-readiness.check:
	@scripts/infra/supabase-readiness-check.sh

## ec2-readiness.check — verify AWS EC2, SSM, ECR, security group, and optional Cloudflare tunnel state
ec2-readiness.check:
	@scripts/infra/ec2-readiness-check.sh

## deploy-smoke — build placeholder images, push to ECR, deploy via SSM, and verify public health
deploy-smoke:
	@scripts/infra/deploy-smoke.sh

## secret-leak.check — scan tracked files for high-risk secret material
secret-leak.check:
	@scripts/infra/secret-leak-check.sh
