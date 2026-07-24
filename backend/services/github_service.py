import base64
import logging

import requests
import yaml

logger = logging.getLogger(__name__)


class GitHubService:
    BASE = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, url: str, params: dict = None):
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            if resp.status_code == 403:
                logger.warning("GitHub 403 on %s — rate limit or permissions", url)
            return resp
        except requests.RequestException as exc:
            logger.error("GitHub request failed: %s", exc)
            return None

    def list_user_repositories(self):
        resp = self._get(f"{self.BASE}/user/repos", params={"per_page": 100, "sort": "updated"})
        return resp.json() if resp and resp.ok else []

    def get_repository(self, full_name: str):
        resp = self._get(f"{self.BASE}/repos/{full_name}")
        return resp.json() if resp and resp.ok else None

    def get_repo_tree(self, owner: str, repo: str, branch: str) -> dict | None:
        """Fetch the full recursive file tree for a repo branch."""
        resp = self._get(
            f"{self.BASE}/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )
        if not resp or not resp.ok:
            logger.warning("get_repo_tree failed for %s/%s@%s: %s",
                           owner, repo, branch, resp.status_code if resp else "no response")
            return None
        return resp.json()

    def get_file_content(self, owner: str, repo: str, path: str, branch: str) -> str | None:
        """Fetch and decode a single file's text content."""
        resp = self._get(
            f"{self.BASE}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch},
        )
        if not resp or not resp.ok:
            return None
        data = resp.json()
        if isinstance(data, dict) and data.get("encoding") == "base64":
            try:
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception:
                return None
        return None

    def commit_workflow_file(self, repo_full_name: str, branch: str, file_path: str, commit_message: str, yaml_content: str, author_name: str, author_email: str):
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        content = base64.b64encode(yaml_content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_message,
            "content": content,
            "branch": branch,
            "committer": {"name": author_name, "email": author_email},
            "author": {"name": author_name, "email": author_email},
        }

        existing = requests.get(url, headers=self.headers, params={"ref": branch})
        if existing.ok:
            payload["sha"] = existing.json().get("sha")

        resp = requests.put(url, headers=self.headers, json=payload)
        return resp.json() if resp.ok else {"error": resp.text}

    @staticmethod
    def get_templates():
        return {
            "python": {
                "name": "pipeline-sh-ci",
                "on": ["push", "pull_request"],
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {"uses": "actions/checkout@v4"},
                            {"name": "Set up Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
                            {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
                            {"name": "Run tests", "run": "pytest"},
                        ],
                    }
                },
            },
            "flask": {
                "name": "pipeline-sh-ci",
                "on": ["push", "pull_request"],
                "jobs": {
                    "ci": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {"uses": "actions/checkout@v4"},
                            {"name": "Set up Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
                            {"name": "Install requirements", "run": "pip install -r requirements.txt"},
                            {"name": "Run lint", "run": "flake8 ."},
                            {"name": "Run tests", "run": "pytest"},
                        ],
                    }
                },
            },
            "docker": {
                "name": "pipeline-sh-ci",
                "on": ["push"],
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {"uses": "actions/checkout@v4"},
                            {"name": "Build Docker image", "run": "docker build -t pipeline-sh-app ."},
                            {"name": "Push artifact", "run": "echo 'Docker image built'"},
                        ],
                    }
                },
            },
            "ai": {
                "name": "pipeline-sh-ci",
                "on": ["push"],
                "jobs": {
                    "train": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {"uses": "actions/checkout@v4"},
                            {"name": "Set up Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
                            {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
                            {"name": "Run model training", "run": "python backend/services/tf_predictor.py"},
                        ],
                    }
                },
            },
        }

    @staticmethod
    def generate_workflow_template(project_type: str, workflow_name: str, branch: str):
        templates = GitHubService.get_templates()
        payload = templates.get(project_type, templates["python"])
        payload = dict(payload)
        payload["name"] = workflow_name
        payload["on"] = ["push", "pull_request"] if project_type != "docker" else ["push"]
        return yaml.dump(payload, sort_keys=False)

    def create_branch(self, owner: str, repo: str, new_branch: str, base_branch: str) -> dict:
        """Create a new git branch in the repository pointing to the base branch's latest commit."""
        # 1. Get SHA of base branch
        ref_url = f"{self.BASE}/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
        resp = self._get(ref_url)
        if not resp or not resp.ok:
            logger.error("Failed to fetch base branch ref: %s", resp.text if resp else "No response")
            return {"error": resp.text if resp else "Could not fetch base branch reference"}

        sha = resp.json().get("object", {}).get("sha")
        if not sha:
            return {"error": "Could not find commit SHA for base branch"}

        # 2. Create the new ref
        create_url = f"{self.BASE}/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{new_branch}",
            "sha": sha
        }

        # Check if the branch already exists to avoid 422 error
        check_url = f"{self.BASE}/repos/{owner}/{repo}/git/ref/heads/{new_branch}"
        check_resp = self._get(check_url)
        if check_resp and check_resp.ok:
            logger.info("Branch %s already exists in %s/%s", new_branch, owner, repo)
            return {"ref": f"refs/heads/{new_branch}", "sha": sha, "already_exists": True}

        post_resp = requests.post(create_url, headers=self.headers, json=payload, timeout=15)
        if post_resp.ok:
            logger.info("Successfully created branch %s in %s/%s", new_branch, owner, repo)
            return post_resp.json()
        else:
            logger.error("Failed to create branch: %s", post_resp.text)
            return {"error": post_resp.text}

    def create_pull_request(self, owner: str, repo: str, title: str, head_branch: str, base_branch: str, body: str) -> dict:
        """Open a new Pull Request on GitHub."""
        url = f"{self.BASE}/repos/{owner}/{repo}/pulls"
        payload = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body
        }
        resp = requests.post(url, headers=self.headers, json=payload, timeout=15)
        if resp.ok:
            logger.info("Successfully created PR for %s/%s: %s", owner, repo, resp.json().get("html_url"))
            return resp.json()
        else:
            logger.error("Failed to create PR: %s", resp.text)
            return {"error": resp.text}

