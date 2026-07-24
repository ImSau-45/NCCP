from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import User, Pipeline, WorkflowLog, ErrorReport, Repository
from backend.db import db
from backend.services.ai_service import AIService

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.route("/trigger", methods=["POST"])
@jwt_required()
def trigger_pipeline():
    data = request.get_json() or {}
    repo_id = data.get("repository_id")
    branch = data.get("branch", "main")
    stage = data.get("stage", "development")

    pipeline = Pipeline(
        repository_id=repo_id,
        name=f"CI/CD - {branch}",
        status="running",
        stage=stage,
        branch=branch,
    )
    db.session.add(pipeline)
    db.session.commit()
    return jsonify({"pipeline": {"id": pipeline.id, "status": pipeline.status, "stage": pipeline.stage}}), 201


@pipeline_bp.route("/<int:pipeline_id>/logs", methods=["GET"])
@jwt_required()
def fetch_logs(pipeline_id):
    logs = WorkflowLog.query.filter_by(pipeline_id=pipeline_id).order_by(WorkflowLog.timestamp.asc()).all()
    result = [{"step_name": log.step_name, "status": log.status, "message": log.message, "timestamp": log.timestamp.isoformat()} for log in logs]
    return jsonify({"logs": result})


@pipeline_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_pipeline():
    data = request.get_json() or {}
    log_text = data.get("log_text", "")
    ai = AIService()
    report = ai.analyze_logs(log_text)
    return jsonify({"report": report})


@pipeline_bp.route("/history", methods=["GET"])
@jwt_required()
def pipeline_history():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    pipelines = Pipeline.query.join(Repository, Pipeline.repository_id == Repository.id).filter(Repository.user_id == user_id).order_by(Pipeline.triggered_at.desc()).limit(20).all()
    return jsonify({"pipelines": [{"id": p.id, "status": p.status, "stage": p.stage, "branch": p.branch, "triggered_at": p.triggered_at.isoformat() if p.triggered_at else None} for p in pipelines]})

