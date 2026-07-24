import json
import logging
import time

logger = logging.getLogger(__name__)


def _set_status(app, project_id: int, status: str, error: str = None):
    """Update project status inside an app context."""
    with app.app_context():
        from backend.db import db
        from backend.models import Project
        p = Project.query.get(project_id)
        if p:
            p.status = status
            if error is not None:
                p.error_message = error
            db.session.commit()


def _save_stack_and_steps(app, project_id: int, stack: dict, steps: list):
    """Persist detected_stack and AutomationStep records."""
    with app.app_context():
        from backend.db import db
        from backend.models import AutomationStep, Project
        p = Project.query.get(project_id)
        if not p:
            return
        p.detected_stack = stack
        p.status = "analyzed"
        # Remove any previous steps (re-analysis)
        AutomationStep.query.filter_by(project_id=project_id).delete()
        for s in steps:
            db.session.add(AutomationStep(
                project_id=project_id,
                step_key=s["step_key"],
                title=s["title"],
                description=s["description"],
                recommended=s["recommended"],
                approved=False,
                yaml_snippet_preview=s.get("yaml_snippet_preview"),
            ))
        p.status = "awaiting_approval"
        db.session.commit()


# Signal files that indicate a recognisable tech stack
_SIGNAL_FILES = {
    "package.json", "requirements.txt", "pyproject.toml", "setup.py",
    "pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "Gemfile",
}


def analyze_repo(app, project_id: int, github_token: str):
    """
    Background function: fetch repo tree, detect stack from real files,
    generate AutomationStep records with per-repo reasoning.
    Updates Project.status at each stage so the frontend can poll progress.
    """
    from backend.services.github_service import GitHubService

    try:
        with app.app_context():
            from backend.models import Project
            project = Project.query.get(project_id)
            if not project:
                return
            owner = project.repo_owner
            repo = project.repo_name
            branch = project.default_branch or "main"

        gh = GitHubService(github_token)

        # ── Stage 1: Reading repo tree ──────────────────────────────────────
        _set_status(app, project_id, "pending_analysis")
        logger.info("[analyze] %s/%s — fetching tree", owner, repo)
        time.sleep(0.5)  # let frontend see pending_analysis state

        tree_data = gh.get_repo_tree(owner, repo, branch)
        if tree_data is None:
            # None means a network/auth error from _get()
            _set_status(app, project_id, "failed",
                        "Could not fetch repository tree. Check token permissions.")
            return

        # Rate-limit check: GitHub returns {message: "API rate limit exceeded..."}
        if isinstance(tree_data, dict) and "message" in tree_data and "rate limit" in tree_data["message"].lower():
            _set_status(app, project_id, "failed",
                        "GitHub API rate limit exceeded. Please wait a few minutes and try again.")
            return

        tree_items = tree_data.get("tree", [])
        truncated = tree_data.get("truncated", False)

        if not tree_items:
            _set_status(app, project_id, "failed",
                        "Repository appears to be empty — no files found.")
            return

        filenames = {item["path"] for item in tree_items if item.get("type") == "blob"}

        # ── Stage 2: Detecting tech stack ───────────────────────────────────
        _set_status(app, project_id, "analyzed")
        logger.info("[analyze] %s/%s — detecting stack (%d files%s)",
                    owner, repo, len(filenames), ", truncated" if truncated else "")
        time.sleep(0.5)  # let frontend see analyzed state

        # Empty repo: no recognisable signal files
        if not (_SIGNAL_FILES & filenames):
            _set_status(app, project_id, "failed",
                        "No recognised project files found (package.json, requirements.txt, "
                        "pom.xml, go.mod, Gemfile, etc.). Add a dependency manifest and re-analyse.")
            return

        stack, file_contents = _detect_stack(gh, owner, repo, branch, filenames)

        if truncated:
            # Surface truncation as a warning in the first step description later
            stack["_truncated"] = True

        # ── Stage 3: Generating step suggestions ────────────────────────────
        logger.info("[analyze] %s/%s — generating steps, stack=%s", owner, repo, stack)
        time.sleep(0.3)

        steps = _generate_steps(stack, file_contents, filenames, owner, repo)

        # ── Persist ─────────────────────────────────────────────────────────
        _save_stack_and_steps(app, project_id, stack, steps)
        logger.info("[analyze] %s/%s — done, %d steps generated", owner, repo, len(steps))

    except Exception as exc:
        logger.exception("[analyze] project_id=%s failed: %s", project_id, exc)
        _set_status(app, project_id, "failed", str(exc))


# ── Stack detection ──────────────────────────────────────────────────────────

def _detect_stack(gh, owner: str, repo: str, branch: str, filenames: set) -> tuple[dict, dict]:
    """
    Read key signal files and return (stack_dict, file_contents_dict).
    stack_dict keys: language, framework, package_manager, has_dockerfile,
                     has_tests, has_ci, node_version, python_version,
                     test_framework, lint_config
    """
    contents = {}
    stack = {
        "language": None,
        "framework": None,
        "package_manager": None,
        "has_dockerfile": False,
        "has_tests": False,
        "has_ci": False,
        "node_version": None,
        "python_version": None,
        "test_framework": None,
        "lint_config": None,
    }

    # ── Existing CI ──────────────────────────────────────────────────────────
    ci_files = [f for f in filenames if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))]
    if ci_files:
        stack["has_ci"] = True

    # ── Dockerfile ───────────────────────────────────────────────────────────
    if "Dockerfile" in filenames or "dockerfile" in filenames:
        stack["has_dockerfile"] = True

    # ── Node / JavaScript / TypeScript ───────────────────────────────────────
    if "package.json" in filenames:
        raw = gh.get_file_content(owner, repo, "package.json", branch)
        if raw:
            contents["package.json"] = raw
            try:
                pkg = json.loads(raw)
            except Exception:
                pkg = {}

            stack["language"] = "javascript"
            stack["package_manager"] = "npm"

            # Detect yarn / pnpm
            if "yarn.lock" in filenames:
                stack["package_manager"] = "yarn"
            elif "pnpm-lock.yaml" in filenames:
                stack["package_manager"] = "pnpm"

            # Node version from engines field
            engines = pkg.get("engines", {})
            if engines.get("node"):
                stack["node_version"] = engines["node"]

            # TypeScript
            if "tsconfig.json" in filenames or "typescript" in pkg.get("devDependencies", {}):
                stack["language"] = "typescript"

            # Framework detection from dependencies
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                stack["framework"] = "nextjs"
            elif "react" in deps:
                stack["framework"] = "react"
            elif "vue" in deps:
                stack["framework"] = "vue"
            elif "express" in deps:
                stack["framework"] = "express"
            elif "fastify" in deps:
                stack["framework"] = "fastify"
            elif "@nestjs/core" in deps:
                stack["framework"] = "nestjs"

            # Test framework
            scripts = pkg.get("scripts", {})
            if "jest" in deps or "jest" in scripts.get("test", ""):
                stack["test_framework"] = "jest"
                stack["has_tests"] = True
            elif "vitest" in deps:
                stack["test_framework"] = "vitest"
                stack["has_tests"] = True
            elif "mocha" in deps:
                stack["test_framework"] = "mocha"
                stack["has_tests"] = True
            elif scripts.get("test") and scripts["test"] not in ("echo \"Error: no test specified\" && exit 1", ""):
                stack["has_tests"] = True

    # ── Python ───────────────────────────────────────────────────────────────
    elif "requirements.txt" in filenames or "pyproject.toml" in filenames or "setup.py" in filenames:
        stack["language"] = "python"
        stack["package_manager"] = "pip"

        if "pyproject.toml" in filenames:
            raw = gh.get_file_content(owner, repo, "pyproject.toml", branch)
            if raw:
                contents["pyproject.toml"] = raw
                if "poetry" in raw:
                    stack["package_manager"] = "poetry"
                if "pytest" in raw:
                    stack["test_framework"] = "pytest"
                    stack["has_tests"] = True
                # Python version
                import re
                m = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', raw)
                if m:
                    stack["python_version"] = m.group(1)

        if "requirements.txt" in filenames:
            raw = gh.get_file_content(owner, repo, "requirements.txt", branch)
            if raw:
                contents["requirements.txt"] = raw
                lower = raw.lower()
                if "django" in lower:
                    stack["framework"] = "django"
                elif "flask" in lower:
                    stack["framework"] = "flask"
                elif "fastapi" in lower:
                    stack["framework"] = "fastapi"
                if "pytest" in lower:
                    stack["test_framework"] = "pytest"
                    stack["has_tests"] = True

        # Check for test directories
        if any(f.startswith("tests/") or f.startswith("test/") for f in filenames):
            stack["has_tests"] = True
            if not stack["test_framework"]:
                stack["test_framework"] = "pytest"

    # ── Java ─────────────────────────────────────────────────────────────────
    elif "pom.xml" in filenames:
        stack["language"] = "java"
        stack["package_manager"] = "maven"
        stack["framework"] = "spring" if any("spring" in f for f in filenames) else None
        stack["has_tests"] = any(f.startswith("src/test/") for f in filenames)
        if stack["has_tests"]:
            stack["test_framework"] = "junit"

    elif "build.gradle" in filenames or "build.gradle.kts" in filenames:
        stack["language"] = "java"
        stack["package_manager"] = "gradle"
        stack["has_tests"] = any(f.startswith("src/test/") for f in filenames)
        if stack["has_tests"]:
            stack["test_framework"] = "junit"

    # ── Go ───────────────────────────────────────────────────────────────────
    elif "go.mod" in filenames:
        stack["language"] = "go"
        stack["package_manager"] = "go modules"
        stack["has_tests"] = any(f.endswith("_test.go") for f in filenames)
        if stack["has_tests"]:
            stack["test_framework"] = "go test"

    # ── Ruby ─────────────────────────────────────────────────────────────────
    elif "Gemfile" in filenames:
        stack["language"] = "ruby"
        stack["package_manager"] = "bundler"
        raw = gh.get_file_content(owner, repo, "Gemfile", branch)
        if raw:
            contents["Gemfile"] = raw
            if "rails" in raw.lower():
                stack["framework"] = "rails"
            if "rspec" in raw.lower():
                stack["test_framework"] = "rspec"
                stack["has_tests"] = True

    # ── Lint config detection ─────────────────────────────────────────────────
    lint_files = {
        ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
        ".flake8", "setup.cfg", ".pylintrc", "golangci.yml", ".golangci.yml",
        "rubocop.yml", ".rubocop.yml",
    }
    found_lint = lint_files & filenames
    if found_lint:
        stack["lint_config"] = next(iter(found_lint))

    return stack, contents


# ── Step generation ──────────────────────────────────────────────────────────

def _generate_steps(stack: dict, file_contents: dict, filenames: set, owner: str, repo: str) -> list:
    """
    Return a list of step dicts with per-repo reasoning in description.
    """
    steps = []
    lang = stack.get("language") or "unknown"
    framework = stack.get("framework")
    pm = stack.get("package_manager") or "pip"
    tf = stack.get("test_framework")
    has_tests = stack.get("has_tests", False)
    has_dockerfile = stack.get("has_dockerfile", False)
    has_ci = stack.get("has_ci", False)
    lint_config = stack.get("lint_config")
    node_ver = stack.get("node_version")
    py_ver = stack.get("python_version")

    # ── Lint step ────────────────────────────────────────────────────────────
    if lint_config:
        if lang in ("javascript", "typescript"):
            steps.append({
                "step_key": "lint",
                "title": "Lint with ESLint",
                "description": (
                    f"Found {lint_config} in {owner}/{repo} — ESLint is already configured. "
                    f"Adding a lint step using `{pm} run lint` on every PR will catch style and "
                    f"correctness issues before they reach main."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {pm} run lint",
            })
        elif lang == "python":
            tool = "flake8" if ".flake8" in lint_config else "pylint"
            steps.append({
                "step_key": "lint",
                "title": f"Lint with {tool}",
                "description": (
                    f"Found {lint_config} in {owner}/{repo} — {tool} is configured. "
                    f"Running `{tool} .` on every push will enforce the project's existing "
                    f"style rules and catch common Python errors early."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {tool} .",
            })
        elif lang == "go":
            steps.append({
                "step_key": "lint",
                "title": "Lint with golangci-lint",
                "description": (
                    f"Found {lint_config} in {owner}/{repo}. Running golangci-lint on every PR "
                    f"will enforce the project's Go linting rules."
                ),
                "recommended": True,
                "yaml_snippet_preview": "- uses: golangci/golangci-lint-action@v4",
            })
    elif lang in ("javascript", "typescript"):
        # Suggest lint even without config
        steps.append({
            "step_key": "lint",
            "title": "Lint with ESLint",
            "description": (
                f"No ESLint config found yet in {owner}/{repo}, but adding one is strongly "
                f"recommended for {lang} projects. This step will run `{pm} run lint` once "
                f"you add an .eslintrc file."
            ),
            "recommended": False,
            "yaml_snippet_preview": f"- run: {pm} run lint",
        })

    # ── Test step ────────────────────────────────────────────────────────────
    if has_tests and tf:
        if tf == "jest":
            install_cmd = f"{pm} ci" if pm == "npm" else f"{pm} install"
            steps.append({
                "step_key": "test",
                "title": "Run Jest tests",
                "description": (
                    f"Found Jest in {owner}/{repo}'s package.json. Running `{pm} test` on every "
                    f"push and PR ensures regressions are caught before merge."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {install_cmd}\n      - run: {pm} test",
            })
        elif tf == "vitest":
            steps.append({
                "step_key": "test",
                "title": "Run Vitest tests",
                "description": (
                    f"Found Vitest in {owner}/{repo}'s package.json. Running `{pm} run test` "
                    f"on every push will validate your Vite-based test suite."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {pm} run test",
            })
        elif tf == "pytest":
            install_cmd = "pip install -r requirements.txt" if "requirements.txt" in filenames else "pip install -e ."
            if pm == "poetry":
                install_cmd = "poetry install"
            steps.append({
                "step_key": "test",
                "title": "Run pytest",
                "description": (
                    f"Found pytest in {owner}/{repo}'s "
                    f"{'requirements.txt' if 'requirements.txt' in filenames else 'pyproject.toml'}. "
                    f"Running `pytest` on every push and PR will catch regressions in your "
                    f"{framework or 'Python'} application."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {install_cmd}\n      - run: pytest",
            })
        elif tf == "go test":
            steps.append({
                "step_key": "test",
                "title": "Run Go tests",
                "description": (
                    f"Found *_test.go files in {owner}/{repo}. Running `go test ./...` on every "
                    f"push will validate all Go packages."
                ),
                "recommended": True,
                "yaml_snippet_preview": "- run: go test ./...",
            })
        elif tf == "junit":
            cmd = "mvn test" if pm == "maven" else "gradle test"
            steps.append({
                "step_key": "test",
                "title": f"Run JUnit tests ({pm})",
                "description": (
                    f"Found test sources under src/test/ in {owner}/{repo}. Running `{cmd}` "
                    f"on every push will execute the JUnit test suite."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {cmd}",
            })
        elif tf in ("mocha", "rspec"):
            steps.append({
                "step_key": "test",
                "title": f"Run {tf} tests",
                "description": (
                    f"Found {tf} in {owner}/{repo}. Running tests on every push will catch "
                    f"regressions early."
                ),
                "recommended": True,
            })

    # ── Build step ───────────────────────────────────────────────────────────
    if lang in ("javascript", "typescript"):
        pkg_json = file_contents.get("package.json", "{}")
        try:
            pkg = json.loads(pkg_json)
        except Exception:
            pkg = {}
        scripts = pkg.get("scripts", {})
        if scripts.get("build"):
            install_cmd = f"{pm} ci" if pm == "npm" else f"{pm} install"
            steps.append({
                "step_key": "build",
                "title": f"Build ({pm} run build)",
                "description": (
                    f"Found a `build` script in {owner}/{repo}'s package.json "
                    f"(`{scripts['build']}`). Running the build step on every push confirms "
                    f"the {framework or lang} app compiles without errors."
                ),
                "recommended": True,
                "yaml_snippet_preview": f"- run: {install_cmd}\n      - run: {pm} run build",
            })
    elif lang == "java":
        cmd = "mvn package -DskipTests" if pm == "maven" else "gradle build -x test"
        steps.append({
            "step_key": "build",
            "title": f"Build with {pm}",
            "description": (
                f"Detected a {pm} project in {owner}/{repo}. Running `{cmd}` on every push "
                f"verifies the project compiles and packages correctly."
            ),
            "recommended": True,
            "yaml_snippet_preview": f"- run: {cmd}",
        })
    elif lang == "go":
        steps.append({
            "step_key": "build",
            "title": "Build Go binary",
            "description": (
                f"Detected a Go module in {owner}/{repo} (go.mod present). Running `go build ./...` "
                f"on every push confirms the project compiles cleanly."
            ),
            "recommended": True,
            "yaml_snippet_preview": "- run: go build ./...",
        })

    # ── Docker build step ────────────────────────────────────────────────────
    if has_dockerfile:
        steps.append({
            "step_key": "docker_build",
            "title": "Build Docker image",
            "description": (
                f"Found a Dockerfile in {owner}/{repo}. Building the Docker image on every push "
                f"catches container configuration errors early and ensures the image builds "
                f"successfully before any deployment."
            ),
            "recommended": True,
            "yaml_snippet_preview": f"- run: docker build -t {repo.lower()} .",
        })

    # ── Deploy step (suggested, not recommended by default) ──────────────────
    steps.append({
        "step_key": "deploy",
        "title": "Deploy to staging",
        "description": (
            f"Optional: add an automated deploy step for {owner}/{repo} that triggers on pushes "
            f"to the default branch. Configure your target environment (AWS, Heroku, Fly.io, etc.) "
            f"to enable this step."
        ),
        "recommended": False,
        "yaml_snippet_preview": None,
    })

    # ── Deploy step always gets a yaml_snippet_preview ──────────────────────
    # (already appended above — patch it in place)
    for s in steps:
        if s["step_key"] == "deploy" and not s.get("yaml_snippet_preview"):
            env_hint = "AWS_REGION" if lang in ("python", "java") else "FLY_API_TOKEN"
            s["yaml_snippet_preview"] = (
                f"- name: Deploy\n"
                f"  env:\n"
                f"    {env_hint}: ${{{{ secrets.{env_hint} }}}}\n"
                f"  run: echo 'Add your deploy command here'"
            )

    # ── Warn if CI already exists ─────────────────────────────────────────────
    if has_ci:
        if steps:
            steps[0]["description"] = (
                f"⚠️ Note: {owner}/{repo} already has GitHub Actions workflows in "
                f".github/workflows/. The steps below will create an additional workflow — "
                f"review for overlap before merging. " + steps[0]["description"]
            )

    # ── Warn if tree was truncated ────────────────────────────────────────────
    if stack.get("_truncated") and steps:
        steps[0]["description"] = (
            f"⚠️ Note: {owner}/{repo} has a very large file tree — GitHub returned a truncated "
            f"listing. Stack detection is based on the files that were visible. "
            + steps[0]["description"]
        )

    return steps
