#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=ap-southeast-1}"
: "${EC2_INSTANCE_ID:?EC2_INSTANCE_ID is required}"
: "${ECR_API_REPOSITORY:=truecare-new-api}"
: "${ECR_OPS_WEB_REPOSITORY:=truecare-new-ops-web}"

command -v aws >/dev/null 2>&1 || {
  echo 'aws cli is required' >&2
  exit 1
}

aws sts get-caller-identity >/dev/null

state="$(aws ec2 describe-instances \
  --region "$AWS_REGION" \
  --instance-ids "$EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)"
if [[ "$state" != "running" ]]; then
  printf 'EC2 instance %s must be running; got %s\n' "$EC2_INSTANCE_ID" "$state" >&2
  exit 1
fi

ping="$(aws ssm describe-instance-information \
  --region "$AWS_REGION" \
  --filters "Key=InstanceIds,Values=$EC2_INSTANCE_ID" \
  --query 'InstanceInformationList[0].PingStatus' \
  --output text)"
if [[ "$ping" != "Online" ]]; then
  printf 'SSM PingStatus must be Online; got %s\n' "$ping" >&2
  exit 1
fi

sgs="$(aws ec2 describe-instances \
  --region "$AWS_REGION" \
  --instance-ids "$EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' \
  --output text)"
for sg in $sgs; do
  ingress_count="$(aws ec2 describe-security-groups \
    --region "$AWS_REGION" \
    --group-ids "$sg" \
    --query 'length(SecurityGroups[0].IpPermissions)' \
    --output text)"
  if [[ "$ingress_count" != "0" ]]; then
    printf 'security group %s has inbound rule count %s; expected 0\n' "$sg" "$ingress_count" >&2
    exit 1
  fi
done

aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$ECR_API_REPOSITORY" >/dev/null
aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$ECR_OPS_WEB_REPOSITORY" >/dev/null

if [[ -n "${CLOUDFLARE_TUNNEL_ID:-}" ]] && command -v cloudflared >/dev/null 2>&1; then
  cloudflared tunnel info "$CLOUDFLARE_TUNNEL_ID" >/dev/null
fi

echo ok
