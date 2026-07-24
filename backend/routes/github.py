from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services.github_service import GitHubService
from backend.models import Repository, User
from backend.db import db


github_bp = Blueprint("github", __name__)


@github_bp.route("/repos", methods=["GET"])
@jwt_required()
def list_repositories():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    token = request.headers.get("X-GitHub-Token")
    github = GitHubService(token)
    repos = github.list_user_repositories()
    # store available repos in local user repo cache
    result = []
    for item in repos:
        result.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "full_name": item.get("full_name"),
            "private": item.get("private"),
            "default_branch": item.get("default_branch"),
        })
    return jsonify({"repositories": result})


@github_bp.route("/connect", methods=["POST"])
@jwt_required()
def connect_repository():
    data = request.get_json() or {}
    token = request.headers.get("X-GitHub-Token")
    repo_full_name = data.get("full_name")
    if not repo_full_name:
        return jsonify({"error": "Repository full_name is required"}), 400
    github = GitHubService(token)
    repo_data = github.get_repository(repo_full_name)
    if not repo_data:
        return jsonify({"error": "Repository not found"}), 404
    user_id = get_jwt_identity()
    local_repo = Repository.query.filter_by(github_repo_id=str(repo_data.get("id")), user_id=user_id).first()
    if not local_repo:
        local_repo = Repository(
            user_id=user_id,
            github_repo_id=str(repo_data.get("id")),
            name=repo_data.get("name"),
            full_name=repo_data.get("full_name"),
            visibility="private" if repo_data.get("private") else "public",
            default_branch=repo_data.get("default_branch", "main"),
            webhook_installed=False,
        )
        db.session.add(local_repo)
        db.session.commit()
    return jsonify({"repository": {
        "id": local_repo.id,
        "name": local_repo.name,
        "full_name": local_repo.full_name,
        "visibility": local_repo.visibility,
        "default_branch": local_repo.default_branch,
    }})


@github_bp.route("/generate-workflow", methods=["POST"])
@jwt_required()
def generate_workflow():
    data = request.get_json() or {}
    project_type = data.get("project_type", "python")
    branch = data.get("branch", "main")
    workflow_name = data.get("workflow_name", "pipeline-sh-ci")

    template = GitHubService.generate_workflow_template(project_type, workflow_name, branch)
    return jsonify({"workflow": template})


@github_bp.route("/webhook", methods=["POST"])
def github_webhook():
    payload = request.get_json() or {}
    event = request.headers.get("X-GitHub-Event")
    # Real webhook validation can be added here
    return jsonify({"event": event, "received": True}), 200
