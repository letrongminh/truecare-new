#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=ap-southeast-1}"
: "${AWS_ACCOUNT_ID:?AWS_ACCOUNT_ID is required}"
: "${EC2_INSTANCE_ID:?EC2_INSTANCE_ID is required}"
: "${ECR_REGISTRY:=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com}"
: "${ECR_API_REPOSITORY:=truecare-new-api}"
: "${ECR_OPS_WEB_REPOSITORY:=truecare-new-ops-web}"
: "${PUBLIC_API_BASE_URL:=https://truecare-new.noboil.dev}"

for bin in aws docker git curl jq; do
  command -v "$bin" >/dev/null 2>&1 || {
    printf '%s is required\n' "$bin" >&2
    exit 1
  }
done

docker info >/dev/null
aws sts get-caller-identity >/dev/null

sha="${GITHUB_SHA:-$(git rev-parse --short=12 HEAD)}"
api_image="${ECR_REGISTRY}/${ECR_API_REPOSITORY}:${sha}"
ops_image="${ECR_REGISTRY}/${ECR_OPS_WEB_REPOSITORY}:${sha}"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null

docker build --platform linux/arm64 -t "$api_image" -f apps/smoke-api/Dockerfile apps/smoke-api
docker build --platform linux/arm64 -t "$ops_image" -f apps/ops-web-placeholder/Dockerfile apps/ops-web-placeholder
docker push "$api_image"
docker push "$ops_image"

commands="$(jq -nc \
  --arg api "$api_image" \
  --arg worker "$api_image" \
  --arg ops "$ops_image" \
  '[
    "set -euo pipefail",
    "cd /opt/truecare-new",
    "aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin " + ($api | split("/")[0]),
    "export TRUECARE_API_IMAGE=" + $api,
    "export TRUECARE_WORKER_IMAGE=" + $worker,
    "export TRUECARE_OPS_WEB_IMAGE=" + $ops,
    "docker compose --env-file .env -f compose.staging.yml pull api worker ops-web",
    "docker compose --env-file .env -f compose.staging.yml up -d",
    "docker compose -f compose.staging.yml ps"
  ]')"
parameters="$(jq -nc --argjson commands "$commands" '{commands: $commands}')"

cmd_id="$(aws ssm send-command \
  --region "$AWS_REGION" \
  --instance-ids "$EC2_INSTANCE_ID" \
  --document-name AWS-RunShellScript \
  --parameters "$parameters" \
  --query 'Command.CommandId' \
  --output text)"

deadline=$((SECONDS + 300))
status="Pending"
while (( SECONDS < deadline )); do
  status="$(aws ssm list-command-invocations \
    --region "$AWS_REGION" \
    --command-id "$cmd_id" \
    --details \
    --query 'CommandInvocations[0].Status' \
    --output text)"
  case "$status" in
    Success) break ;;
    Failed|Cancelled|TimedOut)
      aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$cmd_id" --instance-id "$EC2_INSTANCE_ID"
      exit 1
      ;;
  esac
  sleep 5
done

if [[ "$status" != "Success" ]]; then
  printf 'SSM command %s timed out with status %s\n' "$cmd_id" "$status" >&2
  exit 1
fi

curl -fsS "$PUBLIC_API_BASE_URL/healthz" >/dev/null
curl -fsS "$PUBLIC_API_BASE_URL/readyz" >/dev/null

echo ok
