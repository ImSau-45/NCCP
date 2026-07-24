#!/usr/bin/env bash
set -e

if [[ -z "$AWS_DEFAULT_REGION" ]]; then
  echo "AWS_DEFAULT_REGION is not set"
  exit 1
fi

echo "Provisioning and deploying Pipeline.sh to AWS EC2..."

INSTANCE_TYPE=${AWS_EC2_INSTANCE_TYPE:-t3.micro}
AMI_ID=${AWS_AMI_ID:-ami-0c94855ba95c71c99}
KEY_NAME=${AWS_EC2_KEY_NAME:-pipeline-sh-key}
SECURITY_GROUP_NAME=${AWS_SECURITY_GROUP_NAME:-pipeline-sh-sg}

SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" --query "SecurityGroups[0].GroupId" --output text || true)
if [[ "$SG_ID" == "None" || -z "$SG_ID" ]]; then
  SG_ID=$(aws ec2 create-security-group --group-name "$SECURITY_GROUP_NAME" --description "Pipeline.sh access" --query "GroupId" --output text)
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 5000 --cidr 0.0.0.0/0
fi

INSTANCE_ID=$(aws ec2 run-instances --image-id "$AMI_ID" --count 1 --instance-type "$INSTANCE_TYPE" --key-name "$KEY_NAME" --security-group-ids "$SG_ID" --query "Instances[0].InstanceId" --output text)

echo "Created EC2 instance: $INSTANCE_ID"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

echo "EC2 instance running at $PUBLIC_IP"

echo "Deployment finished. Add SSH and artifact upload steps as required."
