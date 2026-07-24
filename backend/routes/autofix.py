"""
Phases 13, 15, 16, 17 — Auto-Fix HTTP routes.

- POST /api/autofix/receive-failure       (Phase 13, X-Hifi-Key auth)
- POST /api/autofix/webhook/pull-request  (Phase 17, GitHub webhook)
- GET  /api/autofix/projects/<pid>/runs   (Phase 16 list)
- GET  /api/autofix/runs/<rid>            (Phase 16 detail)
- GET  /api/autofix/admin/runs            (Phase 16 admin)
- GET  /api/autofix/admin/stats           (Phase 16 admin stat tile)
"""
from __future__ import annotations

import logging
import os
import threading

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.db import db
from backend.models import (
    AiUsageLog,
    AutoFixAttempt,
    AutoFixRun,
    Project,
    User,
    UserProfile,
)
from backend.services.autofix_service import (
    diagnose_and_fix,
    fetch_failure_log_from_github,
)

autofix_bp = Blueprint("autofix", __name__)
logger = logging.getLogger(__name__)


def _hifi_api_key() -> str:
    return os.environ.get("HIFI_API_KEY", "")


# ---------------------------------------------------------------------------
# Phase 13 — receive-failure
# ---------------------------------------------------------------------------
@autofix_bp.route("/receive-failure", methods=["POST"])
def receive_failure():
    provided = request.headers.get("X-Hifi-Key", "")
    expected = _hifi_api_key()
    if not expected or provided != expected:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    repo = (data.get("repo") or "").strip()
    branch = (data.get("branch") or "").strip()
    commit = (data.get("commit") or "").strip()
    if not (repo and branch and commit) or "/" not in repo:
        return jsonify({"error": "repo, branch, commit are required"}), 400

    owner, repo_name = repo.split("/", 1)
    project = Project.query.filter_by(repo_owner=owner, repo_name=repo_name).first()
    if not project:
        return jsonify({"error": "Project not found for repo"}), 404

    # Fetch failure log using owner's token
    profile = UserProfile.query.filter_by(user_id=project.created_by).first()
    token = profile.github_access_token if profile else None
    failure_log = ""
    if token:
        try:
            from backend.services.github_service import GitHubService
            failure_log = fetch_failure_log_from_github(GitHubService(token), owner, repo_name, commit)
        except Exception:
            logger.exception("Failed to fetch failure log")

    # Log AI usage marker
    try:
        db.session.add(AiUsageLog(
            user_id=project.created_by,
            project_id=project.id,
            task_type="simulation_diagnosis",
            success=True,
        ))
    except Exception:
        db.session.rollback()

    run = AutoFixRun(
        project_id=project.id,
        trigger_branch=branch,
        trigger_commit_sha=commit,
        failure_log=failure_log,
        failure_summary=_first_error_line(failure_log),
        status="received",
        attempt_count=0,
    )
    db.session.add(run)
    db.session.commit()

    # Trigger AI in background — do not block caller
    app = current_app._get_current_object()
    threading.Thread(target=diagnose_and_fix, args=(app, run.id), daemon=True).start()

    return jsonify({"success": True, "run_id": run.id}), 202


def _first_error_line(log_text: str) -> str:
    if not log_text:
        return "CI failure (no log captured)"
    for line in log_text.splitlines():
        s = line.strip()
        low = s.lower()
        if any(k in low for k in ("error", "failed", "exception", "traceback")):
            return s[:240]
    return log_text.strip().splitlines()[-1][:240] if log_text.strip() else "CI failure"


# ---------------------------------------------------------------------------
# Phase 17 — GitHub webhook handler for auto-fix branch events
# ---------------------------------------------------------------------------
@autofix_bp.route("/webhook/pull-request", methods=["POST"])
def handle_pull_request_event():
    event = request.headers.get("X-GitHub-Event", "")
    payload = request.get_json(silent=True) or {}

    if event == "pull_request":
        pr = payload.get("pull_request") or {}
        head_ref = (pr.get("head") or {}).get("ref", "")
        if not head_ref.startswith("auto-fix/"):
            return jsonify({"ignored": True}), 200
        action = payload.get("action")
        pr_url = pr.get("html_url")
        attempt = AutoFixAttempt.query.filter_by(pr_url=pr_url).first()
        if action == "closed" and attempt:
            if pr.get("merged"):
                attempt.pr_status = "merged"
                run = AutoFixRun.query.get(attempt.autofix_run_id)
                if run:
                    run.status = "pr_opened"  # success (kept for schema)
                db.session.commit()
                _bg_notify(attempt.autofix_run_id, "fix_merged")
            else:
                attempt.pr_status = "closed"
                db.session.commit()
        return jsonify({"ok": True}), 200

    if event == "workflow_run":
        wr = payload.get("workflow_run") or {}
        head_branch = wr.get("head_branch", "")
        conclusion = wr.get("conclusion")
        if not head_branch.startswith("auto-fix/"):
            return jsonify({"ignored": True}), 200
        # Find attempt via branch name → PR URL association
        attempts = AutoFixAttempt.query.filter(AutoFixAttempt.pr_url.isnot(None)).all()
        target_attempt = None
        for a in attempts:
            if a.pr_url and head_branch in (a.pr_url or ""):
                target_attempt = a
                break
        if not target_attempt:
            # fallback: latest attempt whose parent run's branch is a prefix
            base = head_branch.split("-")[0]
            target_attempt = (AutoFixAttempt.query
                              .join(AutoFixRun, AutoFixAttempt.autofix_run_id == AutoFixRun.id)
                              .filter(AutoFixRun.trigger_branch == base)
                              .order_by(AutoFixAttempt.id.desc()).first())
        if not target_attempt:
            return jsonify({"ignored": True}), 200
        run = AutoFixRun.query.get(target_attempt.autofix_run_id)
        if not run:
            return jsonify({"ignored": True}), 200

        if conclusion == "success":
            target_attempt.pr_status = "open"
            db.session.commit()
            return jsonify({"ok": True}), 200

        if conclusion == "failure":
            target_attempt.pr_status = "ci_still_failing"
            db.session.commit()
            if run.attempt_count >= 3:
                run.status = "max_retries_reached"
                db.session.commit()
                _bg_notify(run.id, "max_retries_reached")
                return jsonify({"ok": True, "max_retries": True}), 200
            # Re-trigger with previous context
            prev = {
                "diagnosis": target_attempt.diagnosis,
                "diff": target_attempt.proposed_diff,
                "attempt_number": target_attempt.attempt_number,
            }
            # Refresh failure log from the auto-fix branch's failing run
            try:
                profile = UserProfile.query.filter_by(user_id=Project.query.get(run.project_id).created_by).first()
                token = profile.github_access_token if profile else None
                if token:
                    from backend.services.github_service import GitHubService
                    project = Project.query.get(run.project_id)
                    new_log = fetch_failure_log_from_github(
                        GitHubService(token), project.repo_owner, project.repo_name, wr.get("head_sha", "")
                    )
                    if new_log:
                        run.failure_log = new_log
                        db.session.commit()
            except Exception:
                pass
            app = current_app._get_current_object()
            threading.Thread(target=diagnose_and_fix, args=(app, run.id, prev), daemon=True).start()
            return jsonify({"ok": True, "retry_scheduled": True}), 200

    return jsonify({"ignored": True}), 200


def _bg_notify(run_id: int, event: str) -> None:
    try:
        from backend.services.notify_service import notify_owner
        app = current_app._get_current_object()

        def _run():
            with app.app_context():
                notify_owner(run_id, event)

        threading.Thread(target=_run, daemon=True).start()
    except Exception:
        logger.exception("Failed to schedule notification")


# ---------------------------------------------------------------------------
# Phase 16 — Read endpoints for dashboard
# ---------------------------------------------------------------------------
@autofix_bp.route("/projects/<int:project_id>/runs", methods=["GET"])
@jwt_required()
def list_project_runs(project_id):
    user_id = int(get_jwt_identity())
    project = Project.query.filter_by(id=project_id, created_by=user_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    runs = (AutoFixRun.query.filter_by(project_id=project_id)
            .order_by(AutoFixRun.created_date.desc()).all())
    return jsonify({"runs": [r.to_dict() for r in runs]})


@autofix_bp.route("/runs/<int:run_id>", methods=["GET"])
@jwt_required()
def get_run(run_id):
    user_id = int(get_jwt_identity())
    run = AutoFixRun.query.get(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    project = Project.query.get(run.project_id)
    if not project or project.created_by != user_id:
        # allow admin
        user = User.query.get(user_id)
        if not user or (user.role or "") != "admin":
            return jsonify({"error": "Not authorized"}), 403
    return jsonify({"run": run.to_dict(include_attempts=True)})


def _is_admin(user_id) -> bool:
    user = User.query.get(user_id)
    return bool(user and (user.role or "") == "admin")


@autofix_bp.route("/admin/runs", methods=["GET"])
@jwt_required()
def admin_recent_runs():
    user_id = int(get_jwt_identity())
    if not _is_admin(user_id):
        return jsonify({"error": "Admin only"}), 403
    runs = AutoFixRun.query.order_by(AutoFixRun.created_date.desc()).limit(20).all()
    out = []
    for r in runs:
        project = Project.query.get(r.project_id)
        latest = r.attempts.order_by(AutoFixAttempt.attempt_number.desc()).first()
        out.append({
            **r.to_dict(),
            "project_name": project.repo_name if project else None,
            "repo": f"{project.repo_owner}/{project.repo_name}" if project else None,
            "confidence": latest.confidence if latest else None,
        })
    return jsonify({"runs": out})


@autofix_bp.route("/admin/stats", methods=["GET"])
@jwt_required()
def admin_stats():
    user_id = int(get_jwt_identity())
    if not _is_admin(user_id):
        return jsonify({"error": "Admin only"}), 403
    total = AutoFixRun.query.count()
    success = AutoFixRun.query.filter_by(status="pr_opened").count()
    failed = AutoFixRun.query.filter(AutoFixRun.status.in_(("fix_failed", "max_retries_reached"))).count()
    denom = success + failed
    rate = (success / denom * 100.0) if denom else 0.0
    return jsonify({
        "total_runs": total,
        "success": success,
        "failed": failed,
        "success_rate": round(rate, 1),
    })
