import json
import logging
from typing import Dict, List, Optional

import yaml

from backend.models import Repository, User
from backend.services.cache_service import CacheService
from backend.services.github_service import GitHubService

logger = logging.getLogger(__name__)


class WorkflowEngineError(Exception):
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []


def detect_tech_stack(repo: dict) -> Dict[str, bool]:
    """Return lightweight tech stack flags for a repository payload."""
    allowed_keys = ["python", "flask", "django", "fastapi", "node", "react", "vite", "docker"]

    name = str(repo.get("name", "")).lower()
    description = str(repo.get("description", "")).lower()
    has_dockerfile = any(token in description for token in ["dockerfile", "docker compose"])

    flags = {tech: False for tech in allowed_keys}
    if "python" in name or "py" in description or has_dockerfile:
        flags["python"] = True
    if "flask" in description or "flask_" in name:
        flags["flask"] = True
    if "django" in description or "django_" in name:
        flags["django"] = True
    if "fastapi" in description or "fastapi_" in name:
        flags["fastapi"] = True
    if "node" in name or "npm" in description:
        flags["node"] = True
    if "react" in name or "react_" in name:
        flags["react"] = True
    if "vite" in description or "vite_" in name:
        flags["vite"] = True
    if has_dockerfile:
        flags["docker"] = True

    return flags


def validate_yaml(yaml_str: str) -> List[str]:
    """Return syntax errors for workflow YAML content."""
    errors = []
    try:
        yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        errors.append(str(exc))
    return errors


def _cache_key(repo_id: int) -> str:
    return f"workflow_analysis:{repo_id}"


class WorkflowEngine:
    """High-level workflow orchestration for repository analysis and workflow generation."""

    def __init__(self, current_user: Optional[User], github_service: Optional[GitHubService] = None):
        self.user = current_user
        self.github = github_service or GitHubService("")
        self.cache = CacheService()

    def get_available_templates(self) -> List[str]:
        return list(GitHubService.get_templates().keys())

    def analyze_repository(self, repo_id: int) -> dict:
        cached = self.cache.get(_cache_key(repo_id))
        if cached:
            logger.info("Cache hit for repository analysis repo_id=%s", repo_id)
            value = cached.decode("utf-8") if isinstance(cached, bytes) else cached
            return json.loads(value)

        repo = Repository.query.get(repo_id)
        if not repo:
            raise WorkflowEngineError(f"Repository {repo_id} not found")

        repo_data = self.github.get_repository(repo.full_name)
        if not repo_data:
            raise WorkflowEngineError("Failed to fetch repository from GitHub")

        tech_stack = detect_tech_stack(repo_data)
        result = {
            "repository_id": repo_id,
            "repo_name": repo.name,
            "detected": tech_stack,
            "github_url": repo_data.get("html_url"),
        }

        self.cache.set(_cache_key(repo_id), json.dumps(result), expire=600)
        logger.info("Analyzed repository_id=%s – stack=%s", repo_id, tech_stack)
        return result

    def generate_workflow(self, repo_id: int, workflow_name: str, stack: str, branch: Optional[str] = None) -> dict:
        repo = Repository.query.get(repo_id)
        if not repo:
            raise WorkflowEngineError(f"Repository {repo_id} not found")

        if stack not in self.get_available_templates():
            raise WorkflowEngineError("Unsupported workflow stack", errors=[f"Supported stacks: {', '.join(self.get_available_templates())}"])

        target_branch = branch or repo.default_branch or "main"
        yaml_content = GitHubService.generate_workflow_template(stack, workflow_name, target_branch)
        validation_errors = validate_yaml(yaml_content)
        if validation_errors:
            raise WorkflowEngineError("Generated workflow is invalid", errors=validation_errors)

        return {"yaml": yaml_content, "branch": target_branch}

    def commit_workflow(self, repo_id: int, workflow_name: str, stack: str, commit_message: str, branch: Optional[str] = None) -> dict:
        repo = Repository.query.get(repo_id)
        if not repo:
            raise WorkflowEngineError(f"Repository {repo_id} not found")

        target_branch = branch or repo.default_branch or "main"
        generated = self.generate_workflow(repo_id, workflow_name, stack, target_branch)
        response = self.github.commit_workflow_file(
            repo_full_name=repo.full_name,
            branch=target_branch,
            file_path="pipeline.yml",
            commit_message=commit_message,
            yaml_content=generated["yaml"],
            author_name=self.user.name if self.user else "Pipeline.sh",
            author_email=self.user.email if self.user else "pipeline@example.com",
        )

        if not response or response.get("error") or not response.get("html_url"):
            raise WorkflowEngineError("Failed to commit workflow to GitHub", errors=[response.get("error", "GitHub commit returned an empty response")])

        self.cache.delete(_cache_key(repo_id))
        logger.info("Committed workflow for repository_id=%s to %s@%s", repo_id, repo.full_name, target_branch)
        return {"github_url": response.get("html_url", "")}
