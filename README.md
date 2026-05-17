# TrueCare New

This folder is the porting knowledge root for the TrueCare project.

Start here:

- `knowledge/00-porting/` contains the current porting plan and test matrix.
- `knowledge/01-product/` contains product, PRD, design, MVP, and ServiceOS source material.
- `knowledge/02-business/` contains the retained business proposal context.
- `knowledge/INDEX.md` records every copied artifact, original source path, destination path, and purpose.
- `INFRA.md` is the single AWS EC2 + Supabase infrastructure plan that unblocks implementation.
- `Makefile` exposes readiness gates: `infra-prereqs.check`, `supabase-readiness.check`, `ec2-readiness.check`, `deploy-smoke`, and `secret-leak.check`.
- `infra/compose/compose.staging.yml` is the P0 EC2 Docker Compose runtime contract.

All retained source documents were copied, not moved.
