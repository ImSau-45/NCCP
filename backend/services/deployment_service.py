import os
import boto3
import subprocess
from datetime import datetime


class DeploymentService:
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.ec2 = boto3.client("ec2", region_name=self.region)
        self.s3 = boto3.client("s3", region_name=self.region)

    def deploy_to_ec2(self, repository_full_name: str, branch: str, environment: str):
        instance_id = self._get_or_create_ec2_instance()
        deploy_timestamp = datetime.utcnow().isoformat()
        return {
            "repository": repository_full_name,
            "branch": branch,
            "environment": environment,
            "status": "pending",
            "instance_id": instance_id,
            "started_at": deploy_timestamp,
        }

    def _get_or_create_ec2_instance(self):
        response = self.ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        instances = [i for res in response.get("Reservations", []) for i in res.get("Instances", [])]
        if instances:
            return instances[0]["InstanceId"]

        key_name = os.environ.get("AWS_EC2_KEY_NAME")
        image_id = os.environ.get("AWS_AMI_ID", "ami-0c94855ba95c71c99")
        instance_type = os.environ.get("AWS_EC2_INSTANCE_TYPE", "t3.micro")
        created = self.ec2.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=key_name,
            TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "pipeline-sh-agent"}]}],
        )
        return created["Instances"][0]["InstanceId"]

    def build_docker_image(self, path: str, tag: str = "pipeline-sh-app"):
        subprocess.run(["docker", "build", "-t", tag, path], check=True)
        return tag
