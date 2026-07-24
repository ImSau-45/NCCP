"""
Builds a complete GitHub Actions workflow YAML from approved AutomationStep records
and the project's detected_stack. No external dependencies — pure string/dict assembly.
"""
import yaml


def build_workflow(project, approved_steps: list) -> str:
    """
    Return a GitHub Actions YAML string for the given project and approved steps.
    `approved_steps` is a list of AutomationStep ORM objects.
    """
    stack = project.detected_stack or {}
    lang = stack.get("language") or "python"
    pm = stack.get("package_manager") or "pip"
    node_ver = stack.get("node_version") or "20"
    py_ver = stack.get("python_version") or "3.11"
    branch = project.default_branch or "main"

    step_keys = {s.step_key for s in approved_steps}

    # ── Workflow skeleton ────────────────────────────────────────────────────
    workflow = {
        "name": f"HiFi CI — {project.repo_name}",
        "on": {
            "push": {"branches": [branch]},
            "pull_request": {"branches": [branch]},
        },
        "jobs": {
            "ci": {
                "runs-on": "ubuntu-latest",
                "steps": [],
            }
        },
    }

    steps = workflow["jobs"]["ci"]["steps"]

    # Checkout is always first
    steps.append({"uses": "actions/checkout@v4"})

    # ── Language setup ───────────────────────────────────────────────────────
    if lang in ("javascript", "typescript"):
        steps.append({
            "name": "Set up Node.js",
            "uses": "actions/setup-node@v4",
            "with": {"node-version": node_ver, "cache": pm if pm in ("npm", "yarn", "pnpm") else "npm"},
        })
        install_cmd = _node_install_cmd(pm)
        steps.append({"name": "Install dependencies", "run": install_cmd})

    elif lang == "python":
        steps.append({
            "name": "Set up Python",
            "uses": "actions/setup-python@v5",
            "with": {"python-version": py_ver},
        })
        if pm == "poetry":
            steps.append({"name": "Install Poetry", "run": "pip install poetry"})
            steps.append({"name": "Install dependencies", "run": "poetry install"})
        else:
            req_file = "requirements.txt"
            steps.append({"name": "Install dependencies", "run": f"pip install -r {req_file}"})

    elif lang == "java":
        if pm == "maven":
            steps.append({"name": "Set up Java", "uses": "actions/setup-java@v4",
                          "with": {"java-version": "17", "distribution": "temurin"}})
        else:
            steps.append({"name": "Set up Java", "uses": "actions/setup-java@v4",
                          "with": {"java-version": "17", "distribution": "temurin"}})

    elif lang == "go":
        steps.append({"name": "Set up Go", "uses": "actions/setup-go@v5",
                      "with": {"go-version": "stable"}})

    elif lang == "ruby":
        steps.append({"name": "Set up Ruby", "uses": "ruby/setup-ruby@v1",
                      "with": {"bundler-cache": True}})

    # ── Lint ─────────────────────────────────────────────────────────────────
    if "lint" in step_keys:
        lint_cfg = stack.get("lint_config")
        if lang in ("javascript", "typescript"):
            steps.append({"name": "Lint", "run": f"{pm} run lint"})
        elif lang == "python":
            tool = "flake8" if lint_cfg and ".flake8" in lint_cfg else "pylint"
            steps.append({"name": "Lint", "run": f"{tool} ."})
        elif lang == "go":
            steps.append({"name": "Lint", "uses": "golangci/golangci-lint-action@v4"})
        elif lang == "ruby":
            steps.append({"name": "Lint", "run": "bundle exec rubocop"})

    # ── Test ─────────────────────────────────────────────────────────────────
    if "test" in step_keys:
        tf = stack.get("test_framework")
        if tf == "pytest" or (lang == "python" and not tf):
            steps.append({"name": "Test", "run": "pytest"})
        elif tf in ("jest", "vitest", "mocha"):
            steps.append({"name": "Test", "run": f"{pm} test"})
        elif tf == "go test":
            steps.append({"name": "Test", "run": "go test ./..."})
        elif tf == "junit":
            cmd = "mvn test" if pm == "maven" else "gradle test"
            steps.append({"name": "Test", "run": cmd})
        elif tf == "rspec":
            steps.append({"name": "Test", "run": "bundle exec rspec"})
        else:
            steps.append({"name": "Test", "run": f"{pm} test"})

    # ── Build ────────────────────────────────────────────────────────────────
    if "build" in step_keys:
        if lang in ("javascript", "typescript"):
            steps.append({"name": "Build", "run": f"{pm} run build"})
        elif lang == "java":
            cmd = "mvn package -DskipTests" if pm == "maven" else "gradle build -x test"
            steps.append({"name": "Build", "run": cmd})
        elif lang == "go":
            steps.append({"name": "Build", "run": "go build ./..."})

    # ── Docker build ─────────────────────────────────────────────────────────
    if "docker_build" in step_keys:
        steps.append({
            "name": "Build Docker image",
            "run": f"docker build -t {project.repo_name.lower()} .",
        })

    # ── Deploy ───────────────────────────────────────────────────────────────
    if "deploy" in step_keys:
        env_key = "AWS_REGION" if lang in ("python", "java") else "FLY_API_TOKEN"
        steps.append({
            "name": "Deploy",
            "if": f"github.ref == 'refs/heads/{branch}'",
            "env": {env_key: f"${{{{ secrets.{env_key} }}}}"},
            "run": "echo 'Add your deploy command here'",
        })


    # ── Phase 12 — Failure notification to HiFi auto-fix backend ─────────────
    steps.append({
        "name": "Notify HiFi on failure",
        "if": "failure()",
        "env": {
            "HIFI_URL": "${{ secrets.HIFI_URL }}",
            "HIFI_API_KEY": "${{ secrets.HIFI_API_KEY }}",
        },
        "run": (
            'if [ -z "$HIFI_URL" ] || [ -z "$HIFI_API_KEY" ]; then '
            'echo "HIFI_URL / HIFI_API_KEY secrets not set; skipping auto-fix notify"; exit 0; fi\n'
            'curl -sS -X POST "$HIFI_URL/api/autofix/receive-failure" '
            '-H "Content-Type: application/json" '
            '-H "X-Hifi-Key: $HIFI_API_KEY" '
            '-d "{\"repo\":\"${{ github.repository }}\",'
            '\"branch\":\"${{ github.ref_name }}\",'
            '\"commit\":\"${{ github.sha }}\"}" || true'
        ),
    })

    return yaml.dump(workflow, sort_keys=False, allow_unicode=True, default_flow_style=False)


def _node_install_cmd(pm: str) -> str:
    if pm == "yarn":
        return "yarn install --frozen-lockfile"
    if pm == "pnpm":
        return "pnpm install --frozen-lockfile"
    return "npm ci"
