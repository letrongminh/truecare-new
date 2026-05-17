# Deployment Prerequisites v1

This document locks the infrastructure baseline required before port implementation starts.

## Decisions

| Area | Decision |
| --- | --- |
| App runtime | AWS EC2 single instance running Docker Compose |
| AWS region | `ap-southeast-1` |
| EC2 size | Amazon Linux 2023 ARM64, `t4g.medium`, 30 GB encrypted gp3 |
| Public ingress | Cloudflare Tunnel, no inbound EC2 security group rules |
| Database | Supabase Postgres in Singapore |
| Realtime | Supabase Realtime private Broadcast |
| Object storage | Supabase Storage private buckets |
| CI/CD | GitHub Actions OIDC to AWS, ECR image push, SSM deploy |
| Repo | `letrongminh/truecare-new` |

The legacy TrueCare repository remains a source reference only. Do not pull the old EKS/k3s/Argo/Helm topology into P0.

## Required Operator Accounts

- AWS account with permission to manage EC2, ECR, IAM OIDC roles, SSM, CloudWatch Logs, and SSM Parameter Store.
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
- `aws`
- `gh`
- `psql`
- `eas`
- `supabase`
- `jq`
- `curl`

Node must be an active even-numbered LTS/current major supported by the chosen Expo SDK. Pin the final version in the app workspace with `.nvmrc` or Volta before frontend implementation begins.

## AWS Setup Gates

- EC2 instance is in `ap-southeast-1`.
- Instance profile includes `AmazonSSMManagedInstanceCore`.
- Security group has no inbound rules.
- ECR repositories exist:
  - `truecare-new-api`
  - `truecare-new-ops-web`
- GitHub Actions role trusts only `repo:letrongminh/truecare-new:*`.
- Runtime secrets live under `/truecare-new/staging/*` in SSM Parameter Store SecureString.
- EC2 can pull ECR images and read required SSM parameters.

## Cloudflare Setup Gates

- Public hostname defaults to `truecare-new.noboil.dev`.
- Tunnel token is stored server-side only.
- Tunnel routes public HTTPS traffic to Caddy on the EC2 Compose network.
- Cloudflare WAF must not block `/healthz`, `/readyz`, `/metrics`, `/v1/*`, or Realtime fallback polling routes.

## Supabase Setup Gates

See `docs/infra/supabase-readiness-v1.md`.

## CI/CD Setup Gates

- `make secret-leak.check` runs on every pull request.
- `deploy-staging` workflow uses GitHub OIDC, not static AWS keys.
- Images are tagged with immutable git SHA tags.
- Deploy uses SSM SendCommand to run `docker compose pull && docker compose up -d` on EC2.
- Rollback command accepts a previous git SHA image tag.

## Ready-To-Implement Definition

Port implementation can start when these commands pass from an operator machine:

```bash
make infra-prereqs.check
make secret-leak.check
make supabase-readiness.check
make ec2-readiness.check
make deploy-smoke
```
