from datetime import datetime
from backend.db import db
import json


# ---------------------------------------------------------------------------
# Phase 2 enums (stored as strings)
# ---------------------------------------------------------------------------
PROJECT_STATUSES = (
    "pending_analysis",
    "analyzed",
    "awaiting_approval",
    "generating_yaml",
    "pr_created",
    "pr_merged",
    "failed",
)

STEP_KEYS = ("lint", "test", "build", "docker_build", "deploy")

PR_STATUSES = ("draft", "open", "merged", "closed")

SIM_ERROR_TYPES = ("syntax_error", "missing_import", "failing_test")

SIM_STATUSES = ("running", "failed_as_expected", "ai_fixed", "error")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    github_id = db.Column(db.String(64), unique=True, nullable=True)
    google_id = db.Column(db.String(128), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    role = db.Column(db.String(32), default="developer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile = db.relationship("UserProfile", uselist=False, backref="user", cascade="all, delete-orphan")


class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    github_connected = db.Column(db.Boolean, default=False, nullable=False)
    github_access_token = db.Column(db.String(512), nullable=True)
    github_login = db.Column(db.String(128), nullable=True)
    notification_email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Repository(db.Model):
    __tablename__ = "repositories"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    github_repo_id = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(256), nullable=False)
    visibility = db.Column(db.String(32), default="public")
    default_branch = db.Column(db.String(128), nullable=False, default="main")
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    webhook_installed = db.Column(db.Boolean, default=False)
    last_synced = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User", backref="repositories")


class Pipeline(db.Model):
    __tablename__ = "pipelines"
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(64), nullable=False, default="pending")
    stage = db.Column(db.String(64), default="development")
    branch = db.Column(db.String(128), default="main")
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    repository = db.relationship("Repository", backref="pipelines")


class WorkflowTemplate(db.Model):
    __tablename__ = "workflow_templates"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    template_yaml = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Deployment(db.Model):
    __tablename__ = "deployments"
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"), nullable=False)
    environment = db.Column(db.String(64), default="staging")
    status = db.Column(db.String(64), default="pending")
    deployed_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    server_id = db.Column(db.Integer, db.ForeignKey("deployment_servers.id"), nullable=True)
    pipeline = db.relationship("Pipeline", backref="deployments")
    server = db.relationship("DeploymentServer", backref="deployments")


class WorkflowLog(db.Model):
    __tablename__ = "workflow_logs"
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"), nullable=False)
    step_name = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(64), nullable=False)
    message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    pipeline = db.relationship("Pipeline", backref="workflow_logs")


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    body = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    user = db.relationship("User", backref="notifications")


class Analytics(db.Model):
    __tablename__ = "analytics"
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False)
    event_type = db.Column(db.String(128), nullable=False)
    metric = db.Column(db.String(128), nullable=True)
    value = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    repository = db.relationship("Repository", backref="analytics")


class ErrorReport(db.Model):
    __tablename__ = "error_reports"
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(64), default="warning")
    resolved = db.Column(db.Boolean, default=False)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    pipeline = db.relationship("Pipeline", backref="error_reports")


class AIPrediction(db.Model):
    __tablename__ = "ai_predictions"
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"), nullable=False)
    prediction_type = db.Column(db.String(128), nullable=False)
    confidence = db.Column(db.Float, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pipeline = db.relationship("Pipeline", backref="ai_predictions")


class CloudDeployment(db.Model):
    __tablename__ = "cloud_deployments"
    id = db.Column(db.Integer, primary_key=True)
    deployment_id = db.Column(db.Integer, db.ForeignKey("deployments.id"), nullable=False)
    aws_instance_id = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(64), default="pending")
    logs_url = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deployment = db.relationship("Deployment", backref="cloud_deployments")


# ---------------------------------------------------------------------------
# Phase 2 models
# ---------------------------------------------------------------------------

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    repo_url = db.Column(db.String(512), nullable=False)
    repo_owner = db.Column(db.String(256), nullable=True)
    repo_name = db.Column(db.String(256), nullable=True)
    default_branch = db.Column(db.String(128), nullable=True, default="main")
    status = db.Column(db.String(64), nullable=False, default="pending_analysis")
    # detected_stack stored as JSON string: {language, framework, package_manager, has_dockerfile, has_tests}
    _detected_stack = db.Column("detected_stack", db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship("User", backref="projects")
    steps = db.relationship("AutomationStep", backref="project", cascade="all, delete-orphan", lazy="dynamic")
    workflows = db.relationship("GeneratedWorkflow", backref="project", cascade="all, delete-orphan", lazy="dynamic")
    simulations = db.relationship("SimulationRun", backref="project", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def detected_stack(self):
        if self._detected_stack:
            try:
                return json.loads(self._detected_stack)
            except Exception:
                return {}
        return {}

    @detected_stack.setter
    def detected_stack(self, value):
        self._detected_stack = json.dumps(value) if value is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "default_branch": self.default_branch,
            "status": self.status,
            "detected_stack": self.detected_stack,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AutomationStep(db.Model):
    __tablename__ = "automation_steps"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    step_key = db.Column(db.String(64), nullable=False)   # lint|test|build|docker_build|deploy
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False)       # per-repo plain-English reasoning
    recommended = db.Column(db.Boolean, default=False, nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    yaml_snippet_preview = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "step_key": self.step_key,
            "title": self.title,
            "description": self.description,
            "recommended": self.recommended,
            "approved": self.approved,
            "yaml_snippet_preview": self.yaml_snippet_preview,
        }


class GeneratedWorkflow(db.Model):
    __tablename__ = "generated_workflows"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    filename = db.Column(db.String(256), nullable=False, default=".github/workflows/ci.yml")
    yaml_content = db.Column(db.Text, nullable=False)
    pr_url = db.Column(db.String(512), nullable=True)
    pr_number = db.Column(db.Integer, nullable=True)
    pr_status = db.Column(db.String(32), nullable=False, default="draft")  # draft|open|merged|closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "filename": self.filename,
            "yaml_content": self.yaml_content,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "pr_status": self.pr_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SimulationRun(db.Model):
    __tablename__ = "simulation_runs"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    injected_error_type = db.Column(db.String(64), nullable=False)  # syntax_error|missing_import|failing_test
    injected_file = db.Column(db.String(512), nullable=False)
    injected_diff = db.Column(db.Text, nullable=False)
    pipeline_log = db.Column(db.Text, nullable=True)   # simulated CI output
    ai_diagnosis = db.Column(db.Text, nullable=True)
    ai_fix_diff = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="running")  # running|failed_as_expected|ai_fixed|error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "injected_error_type": self.injected_error_type,
            "injected_file": self.injected_file,
            "injected_diff": self.injected_diff,
            "pipeline_log": self.pipeline_log,
            "ai_diagnosis": self.ai_diagnosis,
            "ai_fix_diff": self.ai_fix_diff,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Legacy models (kept for backward compat)
# ---------------------------------------------------------------------------

class DeploymentServer(db.Model):
    __tablename__ = "deployment_servers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    hostname = db.Column(db.String(256), nullable=False)
    ssh_user = db.Column(db.String(64), nullable=False)
    ssh_key_path = db.Column(db.String(512), nullable=True)
    region = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 11 — Auto-Fix models
# ---------------------------------------------------------------------------
AUTOFIX_STATUSES = (
    "received",
    "diagnosing",
    "fix_generated",
    "pr_opened",
    "fix_failed",
    "max_retries_reached",
)

AUTOFIX_PR_STATUSES = ("open", "merged", "closed", "ci_still_failing")


class AutoFixRun(db.Model):
    __tablename__ = "autofix_runs"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    trigger_branch = db.Column(db.String(256), nullable=False)
    trigger_commit_sha = db.Column(db.String(64), nullable=False)
    failure_log = db.Column(db.Text, nullable=True)
    failure_summary = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(64), nullable=False, default="received")
    pr_url = db.Column(db.String(512), nullable=True)
    pr_number = db.Column(db.Integer, nullable=True)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship("Project", backref=db.backref("autofix_runs", cascade="all, delete-orphan", lazy="dynamic"))
    attempts = db.relationship("AutoFixAttempt", backref="run", cascade="all, delete-orphan", lazy="dynamic",
                               order_by="AutoFixAttempt.attempt_number")

    def to_dict(self, include_attempts=False):
        d = {
            "id": self.id,
            "project_id": self.project_id,
            "trigger_branch": self.trigger_branch,
            "trigger_commit_sha": self.trigger_commit_sha,
            "failure_log": self.failure_log,
            "failure_summary": self.failure_summary,
            "status": self.status,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "attempt_count": self.attempt_count,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
        }
        if include_attempts:
            d["attempts"] = [a.to_dict() for a in self.attempts.all()]
        return d


class AutoFixAttempt(db.Model):
    __tablename__ = "autofix_attempts"
    id = db.Column(db.Integer, primary_key=True)
    autofix_run_id = db.Column(db.Integer, db.ForeignKey("autofix_runs.id"), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    diagnosis = db.Column(db.Text, nullable=True)
    proposed_diff = db.Column(db.Text, nullable=True)
    _files_changed = db.Column("files_changed", db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    pr_url = db.Column(db.String(512), nullable=True)
    pr_status = db.Column(db.String(32), nullable=True, default="open")
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def files_changed(self):
        if self._files_changed:
            try:
                return json.loads(self._files_changed)
            except Exception:
                return []
        return []

    @files_changed.setter
    def files_changed(self, value):
        self._files_changed = json.dumps(value) if value is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "autofix_run_id": self.autofix_run_id,
            "attempt_number": self.attempt_number,
            "diagnosis": self.diagnosis,
            "proposed_diff": self.proposed_diff,
            "files_changed": self.files_changed,
            "confidence": self.confidence,
            "pr_url": self.pr_url,
            "pr_status": self.pr_status,
            "created_date": self.created_date.isoformat() if self.created_date else None,
        }


class AiUsageLog(db.Model):
    __tablename__ = "ai_usage_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    task_type = db.Column(db.String(64), nullable=False)   # e.g. simulation_diagnosis, autofix_diagnosis
    model = db.Column(db.String(128), nullable=True)
    tokens_used = db.Column(db.Integer, nullable=True)
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_type": self.task_type,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "success": self.success,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
