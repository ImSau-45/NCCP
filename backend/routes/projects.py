import logging
import threading

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.db import db
from backend.models import AutomationStep, GeneratedWorkflow, Project, User, UserProfile

projects_bp = Blueprint("projects", __name__)
logger = logging.getLogger(__name__)


def _get_github_token(user_id) -> str | None:
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    profile = UserProfile.query.filter_by(user_id=uid).first()
    return profile.github_access_token if profile else None


def _parse_repo_url(url: str):
    """Extract owner and repo name from a GitHub URL."""
    url = url.strip().rstrip("/")
    # Handle https://github.com/owner/repo and git@github.com:owner/repo
    if "github.com" not in url:
        return None, None
    if url.startswith("git@"):
        path = url.split("github.com:")[-1]
    else:
        path = url.split("github.com/")[-1]
    path = path.replace(".git", "")
    parts = path.strip("/").split("/")
    if len(parts) < 2:
        return None, None
    return parts[0], parts[1]


@projects_bp.route("", methods=["POST"])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    repo_url = (data.get("repo_url") or "").strip()

    if not repo_url:
        return jsonify({"error": "repo_url is required"}), 400

    if "github.com" not in repo_url:
        return jsonify({"error": "Only GitHub repositories are supported"}), 400

    owner, repo_name = _parse_repo_url(repo_url)
    if not owner or not repo_name:
        return jsonify({"error": "Could not parse owner/repo from URL. Use format: https://github.com/owner/repo"}), 400

    token = _get_github_token(user_id)
    if not token:
        return jsonify({"error": "GitHub not connected. Connect GitHub in Settings first."}), 403

    from backend.services.github_service import GitHubService
    gh = GitHubService(token)
    repo_data = gh.get_repository(f"{owner}/{repo_name}")

    if not repo_data or repo_data.get("message") == "Not Found" or "id" not in repo_data:
        return jsonify({"error": "Repo not found or you don't have access"}), 404

    existing = Project.query.filter_by(
        created_by=user_id,
        repo_owner=owner,
        repo_name=repo_name,
    ).first()
    if existing:
        return jsonify({"error": "You already have a project for this repository", "project_id": existing.id}), 409

    project = Project(
        created_by=user_id,
        repo_url=repo_url,
        repo_owner=owner,
        repo_name=repo_name,
        default_branch=repo_data.get("default_branch", "main"),
        status="pending_analysis",
    )
    db.session.add(project)
    db.session.commit()

    # Kick off analysis in background thread immediately
    from backend.services.analyze_service import analyze_repo
    from flask import current_app
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=analyze_repo,
        args=(app, project.id, token),
        daemon=True,
    )
    thread.start()

    logger.info("Created project %s for %s/%s, analysis started", project.id, owner, repo_name)
    return jsonify({"project": project.to_dict()}), 201


@projects_bp.route("", methods=["GET"])
@jwt_required()
def list_projects():
    user_id = int(get_jwt_identity())
    projects = (
        Project.query
        .filter_by(created_by=user_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return jsonify({"projects": [p.to_dict() for p in projects]})


@projects_bp.route("/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id):
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    steps = AutomationStep.query.filter_by(project_id=project_id).order_by(AutomationStep.id).all()
    workflow = GeneratedWorkflow.query.filter_by(project_id=project_id).order_by(GeneratedWorkflow.id.desc()).first()

    return jsonify({
        "project": project.to_dict(),
        "steps": [s.to_dict() for s in steps],
        "workflow": workflow.to_dict() if workflow else None,
    })


@projects_bp.route("/<int:project_id>", methods=["DELETE"])
@jwt_required()
def delete_project(project_id):
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"})


@projects_bp.route("/<int:project_id>/status", methods=["GET"])
@jwt_required()
def get_project_status(project_id):
    """Lightweight polling endpoint — returns only status + error_message."""
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({"status": project.status, "error_message": project.error_message})


@projects_bp.route("/<int:project_id>/analyze", methods=["POST"])
@jwt_required()
def reanalyze_project(project_id):
    """Trigger a fresh analysis for an existing project."""
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if project.status in ("pending_analysis", "analyzed"):
        return jsonify({"error": "Analysis already in progress"}), 409

    token = _get_github_token(user_id)
    if not token:
        return jsonify({"error": "GitHub not connected"}), 403

    project.status = "pending_analysis"
    project.error_message = None
    db.session.commit()

    from backend.services.analyze_service import analyze_repo
    from flask import current_app
    app = current_app._get_current_object()
    threading.Thread(target=analyze_repo, args=(app, project.id, token), daemon=True).start()

    logger.info("Re-analysis triggered for project %s", project_id)
    return jsonify({"message": "Analysis started", "project": project.to_dict()})


@projects_bp.route("/<int:project_id>/steps", methods=["PATCH"])
@jwt_required()
def update_steps(project_id):
    """Bulk approve/reject steps. Body: [{id, approved}, ...]"""
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    if project.status not in ("awaiting_approval", "pr_created"):
        return jsonify({"error": "Project is not awaiting approval"}), 409

    updates = request.get_json() or []
    if not isinstance(updates, list):
        return jsonify({"error": "Expected a list of {id, approved}"}), 400

    ids = [u["id"] for u in updates if "id" in u]
    steps = AutomationStep.query.filter(
        AutomationStep.project_id == project_id,
        AutomationStep.id.in_(ids),
    ).all()
    step_map = {s.id: s for s in steps}

    for u in updates:
        step = step_map.get(u.get("id"))
        if step and "approved" in u:
            step.approved = bool(u["approved"])

    db.session.commit()
    all_steps = AutomationStep.query.filter_by(project_id=project_id).order_by(AutomationStep.id).all()
    return jsonify({"steps": [s.to_dict() for s in all_steps]})


@projects_bp.route("/<int:project_id>/generate", methods=["POST"])
@jwt_required()
def generate_workflow(project_id):
    """Generate YAML from approved steps and save as GeneratedWorkflow."""
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    if project.status not in ("awaiting_approval", "pr_created"):
        return jsonify({"error": "Project is not awaiting approval"}), 409

    approved = AutomationStep.query.filter_by(
        project_id=project_id, approved=True
    ).order_by(AutomationStep.id).all()

    if not approved:
        return jsonify({"error": "No steps approved. Approve at least one step first."}), 400

    project.status = "generating_yaml"
    db.session.commit()

    try:
        from backend.services.workflow_service import build_workflow
        yaml_content = build_workflow(project, approved)
    except Exception as exc:
        logger.exception("Workflow generation failed for project %s", project_id)
        project.status = "awaiting_approval"
        db.session.commit()
        return jsonify({"error": f"YAML generation failed: {exc}"}), 500

    # Delete any previous draft workflow
    GeneratedWorkflow.query.filter_by(project_id=project_id, pr_status="draft").delete()

    workflow = GeneratedWorkflow(
        project_id=project_id,
        filename=".github/workflows/hifi-ci.yml",
        yaml_content=yaml_content,
        pr_status="draft",
    )
    db.session.add(workflow)
    project.status = "awaiting_approval"
    db.session.commit()

    logger.info("Workflow generated for project %s (%d bytes)", project_id, len(yaml_content))
    return jsonify({"workflow": workflow.to_dict()}), 201


def _parse_github_error(error_str_or_dict, default_msg="GitHub operation failed"):
    import json
    if not error_str_or_dict:
        return default_msg
    
    # If it is a dictionary, extract the message
    if isinstance(error_str_or_dict, dict):
        msg = error_str_or_dict.get("message", default_msg)
        if msg == "Not Found":
            return "Write access to this repository was denied by GitHub. Please ensure your connected GitHub account has collaborator or write permissions on this repository."
        return msg
        
    # If it is a string, try to parse it as JSON
    try:
        data = json.loads(error_str_or_dict)
        if isinstance(data, dict):
            msg = data.get("message", "")
            if msg == "Not Found":
                return "Write access to this repository was denied by GitHub. Please ensure your connected GitHub account has collaborator or write permissions on this repository."
            return msg or default_msg
    except Exception:
        pass
        
    if "Not Found" in str(error_str_or_dict):
        return "Write access to this repository was denied by GitHub. Please ensure your connected GitHub account has collaborator or write permissions on this repository."
        
    return str(error_str_or_dict)


@projects_bp.route("/<int:project_id>/publish", methods=["POST"])
@jwt_required()
def publish_workflow(project_id):
    """Publish generated workflow YAML. Method can be 'commit' or 'pr'."""
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # We need the generated workflow in draft status
    workflow = GeneratedWorkflow.query.filter_by(project_id=project_id, pr_status="draft").order_by(GeneratedWorkflow.id.desc()).first()
    if not workflow:
        return jsonify({"error": "No draft workflow found. Generate one first."}), 400

    data = request.get_json() or {}
    method = data.get("method", "pr")  # 'commit' or 'pr'
    commit_message = data.get("commit_message") or "Add CI/CD workflow via Pipeline.sh"
    branch_name = data.get("branch_name") or "hifi-ci-setup"

    token = _get_github_token(user_id)
    if not token:
        return jsonify({"error": "GitHub not connected"}), 403

    from backend.services.github_service import GitHubService
    gh = GitHubService(token)

    owner = project.repo_owner
    repo = project.repo_name
    default_branch = project.default_branch or "main"
    user = User.query.get(user_id)
    author_name = (user.name if user and user.name else None) or (user.email.split("@")[0] if user and user.email else None) or "Pipeline.sh"
    author_email = (user.email if user and user.email else None) or "pipeline@example.com"

    if method == "commit":
        # Commit directly to default branch
        resp = gh.commit_workflow_file(
            repo_full_name=f"{owner}/{repo}",
            branch=default_branch,
            file_path=workflow.filename,
            commit_message=commit_message,
            yaml_content=workflow.yaml_content,
            author_name=author_name,
            author_email=author_email
        )
        if not resp or "error" in resp:
            err_msg = resp.get("error", "GitHub commit returned an empty response") if resp else "Empty response"
            logger.error("GitHub direct commit failed for project %s: %s", project_id, err_msg)
            friendly_err = _parse_github_error(err_msg, "GitHub commit failed")
            return jsonify({"error": friendly_err}), 422

        workflow.pr_status = "merged"
        workflow.pr_url = resp.get("html_url")
        project.status = "pr_merged"
        db.session.commit()

        logger.info("Directly committed workflow for project %s to %s/%s@%s", project_id, owner, repo, default_branch)
        return jsonify({"success": True, "message": "Workflow committed directly to default branch", "workflow": workflow.to_dict()}), 200

    elif method == "pr":
        # Create a new branch
        branch_resp = gh.create_branch(owner, repo, branch_name, default_branch)
        if "error" in branch_resp:
            friendly_err = _parse_github_error(branch_resp["error"], "Failed to create branch")
            return jsonify({"error": friendly_err}), 422

        # Commit to that branch
        commit_resp = gh.commit_workflow_file(
            repo_full_name=f"{owner}/{repo}",
            branch=branch_name,
            file_path=workflow.filename,
            commit_message=commit_message,
            yaml_content=workflow.yaml_content,
            author_name=author_name,
            author_email=author_email
        )
        if not commit_resp or "error" in commit_resp:
            err_msg = commit_resp.get("error", "GitHub commit returned an empty response") if commit_resp else "Empty response"
            logger.error("GitHub PR branch commit failed for project %s: %s", project_id, err_msg)
            friendly_err = _parse_github_error(err_msg, "GitHub commit failed")
            return jsonify({"error": friendly_err}), 422

        # Open a PR
        pr_title = commit_message
        pr_body = (
            "This Pull Request adds an automated CI/CD workflow generated by Pipeline.sh "
            "based on your approved automation steps."
        )
        pr_resp = gh.create_pull_request(owner, repo, pr_title, branch_name, default_branch, pr_body)
        if "error" in pr_resp:
            friendly_err = _parse_github_error(pr_resp["error"], "Failed to open Pull Request")
            return jsonify({"error": friendly_err}), 422

        workflow.pr_status = "open"
        workflow.pr_url = pr_resp.get("html_url")
        workflow.pr_number = pr_resp.get("number")
        project.status = "pr_created"
        db.session.commit()

        logger.info("Created PR for project %s: %s", project_id, workflow.pr_url)
        return jsonify({"success": True, "message": "Pull request created successfully", "workflow": workflow.to_dict()}), 201

    else:
        return jsonify({"error": "Invalid publish method. Expected 'commit' or 'pr'."}), 400

