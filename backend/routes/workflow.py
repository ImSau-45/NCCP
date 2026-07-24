import logging
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.models import User
from backend.services.github_service import GitHubService
from backend.services.workflow_engine import WorkflowEngine, WorkflowEngineError

workflow_bp = Blueprint("workflow", __name__)
logger = logging.getLogger(__name__)


def _json_error(message: str, status_code: int = 400, errors: Optional[list] = None):
    payload = {"success": False, "message": message, "data": None}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status_code


def _build_engine() -> WorkflowEngine:
    token = request.headers.get("X-GitHub-Token")
    if not token:
        raise ValueError("X-GitHub-Token header is required")

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        raise LookupError("Authenticated user not found")

    return WorkflowEngine(current_user=user, github_service=GitHubService(token))


@workflow_bp.route("/templates", methods=["GET"])
@jwt_required()
def list_templates():
    """Return available workflow templates."""
    try:
        engine = _build_engine()
    except (LookupError, ValueError) as exc:
        return _json_error(str(exc), 401)

    return jsonify({
        "success": True,
        "message": "Available workflow templates",
        "data": {"templates": engine.get_available_templates()},
    })


@workflow_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_repository():
    """Analyze a repository and detect the detected tech stack."""
    data = request.get_json() or {}
    repo_id = data.get("repository_id")
    if not repo_id:
        return _json_error("repository_id is required", 400)

    try:
        engine = _build_engine()
        result = engine.analyze_repository(repo_id)
    except WorkflowEngineError as exc:
        return _json_error(str(exc), 404 if "not found" in str(exc).lower() else 422, exc.errors)
    except (LookupError, ValueError) as exc:
        return _json_error(str(exc), 401)
    except Exception as exc:
        logger.exception("Workflow analysis failed for repository_id=%s", repo_id)
        return _json_error("Workflow analysis failed", 500)

    return jsonify({
        "success": True,
        "message": "Repository analyzed successfully",
        "data": result,
    })


@workflow_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_workflow():
    """Generate a workflow YAML for a repository."""
    data = request.get_json() or {}
    repo_id = data.get("repository_id")
    stack = data.get("stack", "python")
    workflow_name = data.get("workflow_name", "CI/CD Pipeline")

    if not repo_id:
        return _json_error("repository_id is required", 400)

    try:
        engine = _build_engine()
        result = engine.generate_workflow(repo_id=repo_id, workflow_name=workflow_name, stack=stack)
    except WorkflowEngineError as exc:
        return _json_error(str(exc), 422, exc.errors)
    except (LookupError, ValueError) as exc:
        return _json_error(str(exc), 401)
    except Exception as exc:
        logger.exception("Workflow generation failed for repository_id=%s", repo_id)
        return _json_error("Workflow generation failed", 500)

    return jsonify({
        "success": True,
        "message": f"Generated {stack} workflow template",
        "data": result,
    })


@workflow_bp.route("/preview", methods=["POST"])
@jwt_required()
def preview_workflow():
    """Preview the generated workflow without committing."""
    data = request.get_json() or {}
    repo_id = data.get("repository_id")
    stack = data.get("stack", "python")
    workflow_name = data.get("workflow_name", "CI/CD Pipeline")

    if not repo_id:
        return _json_error("repository_id is required", 400)

    try:
        engine = _build_engine()
        result = engine.generate_workflow(repo_id=repo_id, workflow_name=workflow_name, stack=stack)
    except WorkflowEngineError as exc:
        return _json_error(str(exc), 422, exc.errors)
    except (LookupError, ValueError) as exc:
        return _json_error(str(exc), 401)
    except Exception as exc:
        logger.exception("Workflow preview failed for repository_id=%s", repo_id)
        return _json_error("Workflow preview failed", 500)

    return jsonify({
        "success": True,
        "message": "Workflow preview generated",
        "data": result,
    })


@workflow_bp.route("/commit", methods=["POST"])
@jwt_required()
def commit_workflow():
    """Commit the generated workflow to the repository."""
    data = request.get_json() or {}
    repo_id = data.get("repository_id")
    stack = data.get("stack", "python")
    workflow_name = data.get("workflow_name", "CI/CD Pipeline")
    commit_message = data.get("commit_message", "Add CI/CD workflow via Pipeline.sh")

    if not repo_id:
        return _json_error("repository_id is required", 400)

    try:
        engine = _build_engine()
        result = engine.commit_workflow(
            repo_id=repo_id,
            workflow_name=workflow_name,
            stack=stack,
            commit_message=commit_message,
        )
    except WorkflowEngineError as exc:
        return _json_error(str(exc), 422 if exc.errors else 404, exc.errors)
    except (LookupError, ValueError) as exc:
        return _json_error(str(exc), 401)
    except Exception as exc:
        logger.exception("Workflow commit failed for repository_id=%s", repo_id)
        return _json_error("Workflow commit failed", 500)

    return jsonify({
        "success": True,
        "message": "Workflow committed successfully",
        "data": result,
    })
