"""
Phase 4 verification tests:
- analyze_service edge cases (empty repo, rate limit, truncated tree, deploy yaml_snippet)
- GET /api/projects/:id/status endpoint
- POST /api/projects/:id/analyze re-analysis endpoint
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.app import create_app
from backend.db import db as _db
from backend.models import AutomationStep, Project, User, UserProfile


# ── App / DB fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key-32-bytes-long!!!",
    })
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def auth_headers(app, client):
    """Register a user and return JWT headers."""
    client.post("/api/auth/register", json={
        "name": "Phase4 User", "email": "phase4@test.com", "password": "pass1234"
    })
    res = client.post("/api/auth/login", json={
        "email": "phase4@test.com", "password": "pass1234"
    })
    token = res.get_json()["access_token"]

    with app.app_context():
        user = User.query.filter_by(email="phase4@test.com").first()
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        profile.github_access_token = "fake-gh-token"
        profile.github_connected = True
        _db.session.commit()

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def project(app, auth_headers, client):
    """Create a bare project row (no analysis) for endpoint tests."""
    with app.app_context():
        user = User.query.filter_by(email="phase4@test.com").first()
        p = Project(
            created_by=user.id,
            repo_url="https://github.com/test/repo",
            repo_owner="test",
            repo_name="repo",
            default_branch="main",
            status="failed",
            error_message="previous failure",
        )
        _db.session.add(p)
        _db.session.commit()
        pid = p.id
    yield pid
    with app.app_context():
        AutomationStep.query.filter_by(project_id=pid).delete()
        Project.query.filter_by(id=pid).delete()
        _db.session.commit()


# ── Seed helper ───────────────────────────────────────────────────────────────

def _ensure_analyze_user(app):
    """Create the analyze@test.com user if it doesn't exist, return its id."""
    with app.app_context():
        u = User.query.filter_by(email="analyze@test.com").first()
        if not u:
            u = User(name="Analyze User", email="analyze@test.com", password_hash="x")
            _db.session.add(u)
            _db.session.flush()
            _db.session.add(UserProfile(user_id=u.id))
            _db.session.commit()
        return u.id


# ── analyze_service unit tests ────────────────────────────────────────────────

class TestAnalyzeServiceEdgeCases:

    def test_empty_repo_sets_failed(self, app):
        """analyze_repo should set status=failed when tree is empty."""
        from backend.services.analyze_service import analyze_repo

        uid = _ensure_analyze_user(app)
        with app.app_context():
            p = Project(created_by=uid, repo_url="https://github.com/a/b",
                        repo_owner="a", repo_name="b", default_branch="main",
                        status="pending_analysis")
            _db.session.add(p)
            _db.session.commit()
            pid = p.id

        with patch("backend.services.github_service.GitHubService") as MockGH:
            MockGH.return_value.get_repo_tree.return_value = {"tree": [], "truncated": False}
            analyze_repo(app, pid, "token")

        with app.app_context():
            p = Project.query.get(pid)
            assert p.status == "failed"
            assert "empty" in p.error_message.lower()
            _db.session.delete(p)
            _db.session.commit()

    def test_no_signal_files_sets_failed(self, app):
        """analyze_repo should fail when tree has files but none are signal files."""
        from backend.services.analyze_service import analyze_repo

        uid = _ensure_analyze_user(app)
        with app.app_context():
            p = Project(created_by=uid, repo_url="https://github.com/a/c",
                        repo_owner="a", repo_name="c", default_branch="main",
                        status="pending_analysis")
            _db.session.add(p)
            _db.session.commit()
            pid = p.id

        with patch("backend.services.github_service.GitHubService") as MockGH:
            MockGH.return_value.get_repo_tree.return_value = {
                "tree": [{"path": "README.md", "type": "blob"}],
                "truncated": False,
            }
            analyze_repo(app, pid, "token")

        with app.app_context():
            p = Project.query.get(pid)
            assert p.status == "failed"
            assert "recognised" in p.error_message.lower()
            _db.session.delete(p)
            _db.session.commit()

    def test_rate_limit_sets_failed(self, app):
        """analyze_repo should fail with rate-limit message on GitHub rate-limit response."""
        from backend.services.analyze_service import analyze_repo

        uid = _ensure_analyze_user(app)
        with app.app_context():
            p = Project(created_by=uid, repo_url="https://github.com/a/d",
                        repo_owner="a", repo_name="d", default_branch="main",
                        status="pending_analysis")
            _db.session.add(p)
            _db.session.commit()
            pid = p.id

        with patch("backend.services.github_service.GitHubService") as MockGH:
            MockGH.return_value.get_repo_tree.return_value = {
                "message": "API rate limit exceeded for ..."
            }
            analyze_repo(app, pid, "token")

        with app.app_context():
            p = Project.query.get(pid)
            assert p.status == "failed"
            assert "rate limit" in p.error_message.lower()
            _db.session.delete(p)
            _db.session.commit()

    def test_truncated_tree_warning_in_step_description(self, app):
        """Truncated tree flag should prepend a warning to the first step description."""
        from backend.services.analyze_service import analyze_repo

        pkg_json = json.dumps({"dependencies": {"react": "^18"}, "scripts": {"build": "vite build"}})
        uid = _ensure_analyze_user(app)
        with app.app_context():
            p = Project(created_by=uid, repo_url="https://github.com/a/e",
                        repo_owner="a", repo_name="e", default_branch="main",
                        status="pending_analysis")
            _db.session.add(p)
            _db.session.commit()
            pid = p.id

        with patch("backend.services.github_service.GitHubService") as MockGH:
            MockGH.return_value.get_repo_tree.return_value = {
                "tree": [{"path": "package.json", "type": "blob"}],
                "truncated": True,
            }
            MockGH.return_value.get_file_content.return_value = pkg_json
            analyze_repo(app, pid, "token")

        with app.app_context():
            p = Project.query.get(pid)
            assert p.status == "awaiting_approval"
            steps = AutomationStep.query.filter_by(project_id=pid).order_by(AutomationStep.id).all()
            assert steps, "Expected at least one step"
            assert "truncated" in steps[0].description.lower()
            for s in steps:
                _db.session.delete(s)
            _db.session.delete(p)
            _db.session.commit()

    def test_deploy_step_always_has_yaml_snippet(self):
        """_generate_steps must always populate yaml_snippet_preview on the deploy step."""
        from backend.services.analyze_service import _generate_steps

        stack = {
            "language": "python", "framework": "flask", "package_manager": "pip",
            "has_tests": False, "has_dockerfile": False, "has_ci": False,
            "test_framework": None, "lint_config": None,
            "node_version": None, "python_version": None,
        }
        steps = _generate_steps(stack, {}, set(), "owner", "repo")
        deploy = next((s for s in steps if s["step_key"] == "deploy"), None)
        assert deploy is not None
        assert deploy["yaml_snippet_preview"] is not None
        assert len(deploy["yaml_snippet_preview"]) > 0

    def test_intermediate_statuses_committed(self, app):
        """analyze_repo should commit both pending_analysis and analyzed before awaiting_approval."""
        from backend.services.analyze_service import analyze_repo

        statuses_seen = []
        original = __import__(
            "backend.services.analyze_service", fromlist=["_set_status"]
        )._set_status

        def tracking(a, pid, status, error=None):
            statuses_seen.append(status)
            original(a, pid, status, error)

        pkg_json = json.dumps({"dependencies": {"express": "^4"}})
        uid = _ensure_analyze_user(app)
        with app.app_context():
            p = Project(created_by=uid, repo_url="https://github.com/a/f",
                        repo_owner="a", repo_name="f", default_branch="main",
                        status="pending_analysis")
            _db.session.add(p)
            _db.session.commit()
            pid = p.id

        with patch("backend.services.github_service.GitHubService") as MockGH, \
             patch("backend.services.analyze_service._set_status", side_effect=tracking):
            MockGH.return_value.get_repo_tree.return_value = {
                "tree": [{"path": "package.json", "type": "blob"}],
                "truncated": False,
            }
            MockGH.return_value.get_file_content.return_value = pkg_json
            analyze_repo(app, pid, "token")

        assert "pending_analysis" in statuses_seen
        assert "analyzed" in statuses_seen

        with app.app_context():
            AutomationStep.query.filter_by(project_id=pid).delete()
            Project.query.filter_by(id=pid).delete()
            _db.session.commit()


# ── Endpoint tests ────────────────────────────────────────────────────────────

class TestProjectStatusEndpoint:
    def test_get_status_returns_status_and_error(self, client, auth_headers, project):
        res = client.get(f"/api/projects/{project}/status", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "status" in data
        assert "error_message" in data
        assert data["status"] == "failed"
        assert data["error_message"] == "previous failure"

    def test_get_status_404_for_wrong_user(self, client, project):
        client.post("/api/auth/register", json={
            "name": "Other", "email": "other4@test.com", "password": "pass1234"
        })
        res2 = client.post("/api/auth/login", json={
            "email": "other4@test.com", "password": "pass1234"
        })
        token2 = res2.get_json()["access_token"]
        res = client.get(f"/api/projects/{project}/status",
                         headers={"Authorization": f"Bearer {token2}"})
        assert res.status_code == 404


class TestReanalyzeEndpoint:
    def test_reanalyze_starts_analysis(self, client, auth_headers, project, app):
        with patch("backend.routes.projects.threading.Thread") as MockThread:
            MockThread.return_value.start = MagicMock()
            res = client.post(f"/api/projects/{project}/analyze", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["message"] == "Analysis started"
        assert data["project"]["status"] == "pending_analysis"

        with app.app_context():
            p = Project.query.get(project)
            assert p.status == "pending_analysis"
            assert p.error_message is None

    def test_reanalyze_409_when_already_in_progress(self, client, auth_headers, project, app):
        with app.app_context():
            p = Project.query.get(project)
            p.status = "pending_analysis"
            _db.session.commit()
        res = client.post(f"/api/projects/{project}/analyze", headers=auth_headers)
        assert res.status_code == 409

    def test_reanalyze_404_for_wrong_user(self, client, project):
        res2 = client.post("/api/auth/login", json={
            "email": "other4@test.com", "password": "pass1234"
        })
        token2 = res2.get_json()["access_token"]
        res = client.post(f"/api/projects/{project}/analyze",
                          headers={"Authorization": f"Bearer {token2}"})
        assert res.status_code == 404
