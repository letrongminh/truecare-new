# Deployment Prerequisites v1

This document locks the minimum infrastructure baseline required before port implementation starts.

## Decisions

| Area | Decision |
| --- | --- |
| AWS services | EC2 only for P0 runtime |
| App runtime | Single EC2 instance running Docker Compose |
| AWS region | `ap-southeast-1` |
| EC2 size | Amazon Linux 2023 ARM64, `t4g.medium`, 30 GB encrypted root volume |
| Public ingress | Cloudflare Tunnel to Caddy on EC2 |
| Admin/deploy access | SSH to EC2, preferably through Cloudflare Access SSH or a fixed operator IP allowlist |
| Database | Supabase Postgres in Singapore |
| Realtime | Supabase Realtime private Broadcast |
| Object storage | Supabase Storage private buckets |
| CI/CD | GitHub Actions static checks; deploy is SSH-based and builds directly on EC2 |
| Repo | `letrongminh/truecare-new` |

The legacy TrueCare repository remains a source reference only. Do not pull the old EKS/k3s/Argo/Helm topology into P0.

## Explicitly Out Of P0

Do not introduce these AWS services for P0 unless a later review explicitly approves the added operational cost:

- ECR
- SSM Session Manager / SSM SendCommand
- SSM Parameter Store
- CloudWatch Logs
- ALB / ACM
- RDS
- S3
- EKS / ECS
- IAM OIDC deploy role for GitHub Actions

EC2 security groups, key pairs, Elastic IP, and the EC2 root volume are considered part of the EC2 baseline, not separate application services.

## Required Operator Accounts

- AWS account with permission to create and manage one EC2 instance and its security group.
- Cloudflare account for `truecare-new.noboil.dev` or another approved hostname.
- Supabase project in Singapore.
- GitHub repository with Actions enabled.
- Expo account for later EAS Build and EAS Update setup.
- Sentry or compatible DSN for API, worker, mobile, and Ops web.

## Required Local Tools

Run:

```bash
make infra-prereqs.check
```

Required CLIs:

- `docker`
- `node`
- `pnpm`
- `uv`
- `psql`
- `supabase`
- `jq`
- `curl`
- `git`
- `ssh`

Optional but expected soon:

- `aws` for EC2 provisioning and security group audit
- `gh` for GitHub repo/admin work
- `eas` for mobile release setup

## EC2 Setup Gates

- EC2 instance is in `ap-southeast-1`.
- Docker Engine and Docker Compose plugin are installed.
- Repo is cloned at `/opt/truecare-new`.
- EC2-local `/opt/truecare-new/.env` exists and is never committed.
- Public app traffic reaches the instance through Cloudflare Tunnel.
- No public inbound `80` or `443` rules are open on EC2.
- SSH is limited to Cloudflare Access SSH or a fixed operator IP allowlist.

## Supabase Setup Gates

See `docs/infra/supabase-readiness-v1.md`.

## CI/CD Setup Gates

- Pull requests run static checks and `make secret-leak.check`.
- Deploy is deliberately not AWS-managed in P0.
- Deploy command SSHes to EC2, pulls `origin/main`, and runs:
  ```bash
  docker compose --env-file .env -f infra/compose/compose.staging.yml up -d --build
  ```
- Rollback uses git history on EC2:
  ```bash
  git checkout <previous-good-sha>
  docker compose --env-file .env -f infra/compose/compose.staging.yml up -d --build
  ```

## Ready-To-Implement Definition

Port implementation can start when these commands pass from an operator machine:

```bash
make infra-prereqs.check
make secret-leak.check
make supabase-readiness.check
make ec2-readiness.check
make deploy-smoke
```
