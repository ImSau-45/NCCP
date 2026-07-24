from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.services.deployment_service import DeploymentService


deploy_bp = Blueprint("deploy", __name__)


@deploy_bp.route("/aws", methods=["POST"])
@jwt_required()
def deploy_aws():
    data = request.get_json() or {}
    repo_full_name = data.get("repository")
    branch = data.get("branch", "main")
    environment = data.get("environment", "staging")

    deploy_service = DeploymentService()
    result = deploy_service.deploy_to_ec2(repo_full_name, branch, environment)
    return jsonify({"deployment": result})
