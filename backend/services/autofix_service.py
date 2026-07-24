"""
Phase 14 — Auto-Fix core service.

Given an AutoFixRun that has captured a failing CI log, this module:

  1. Identifies the source files most likely related to the failure
  2. Fetches their current content from GitHub at the failing commit
  3. Asks an LLM for a diagnosis + unified diff fix
  4. Applies the fix on a new branch `auto-fix/{trigger_branch}-{ts}`
  5. Opens a Pull Request against the trigger branch
  6. Records the attempt and triggers owner notifications
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from datetime import datetime
from typing import Optional

import requests

from backend.db import db
from backend.models import (
    AiUsageLog,
    AutoFixAttempt,
    AutoFixRun,
    Project,
    UserProfile,
)
from backend.services.ai_service import AIService
from backend.services.github_service import GitHubService

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
CONFIDENCE_THRESHOLD = 0.6

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FILE_HINT_RE = re.compile(
    r"([A-Za-z0-9_\-./]+\.(?:py|js|jsx|ts|tsx|java|go|rb|rs|php|c|cpp|h|css|html|yml|yaml|json))(?::(\d+))?"
)


def _extract_candidate_files(log_text: str, tree_paths: list[str], limit: int = 5) -> list[str]:
    """Parse CI log for filenames/paths and cross-check against the repo tree."""
    if not log_text or not tree_paths:
        return []
    matches = []
    for m in _FILE_HINT_RE.finditer(log_text):
        path = m.group(1).lstrip("./")
        matches.append(path)

    seen = set()
    result = []
    tree_set = set(tree_paths)
    # Exact matches first
    for p in matches:
        if p in tree_set and p not in seen:
            seen.add(p)
            result.append(p)
            if len(result) >= limit:
                return result
    # Then basename matches
    basename_map: dict[str, str] = {}
    for tp in tree_paths:
        basename_map.setdefault(tp.rsplit("/", 1)[-1], tp)
    for p in matches:
        base = p.rsplit("/", 1)[-1]
        target = basename_map.get(base)
        if target and target not in seen:
            seen.add(target)
            result.append(target)
            if len(result) >= limit:
                return result
    return result


def _summarize_failure(log_text: str) -> str:
    """Grab the first meaningful error line as a one-line summary."""
    if not log_text:
        return "Unknown CI failure"
    for line in log_text.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if any(kw in low for kw in ("error", "failed", "exception", "traceback")):
            return stripped[:240]
    return log_text.strip().splitlines()[-1][:240] if log_text.strip() else "Unknown failure"


def _get_token_for_project(project: Project) -> Optional[str]:
    profile = UserProfile.query.filter_by(user_id=project.created_by).first()
    return profile.github_access_token if profile else None


def _apply_diff_to_content(original: str, diff_text: str) -> Optional[str]:
    """
    Best-effort unified diff applier. Supports simple hunks; when the diff cannot
    be applied cleanly, returns None so caller can fall back.
    """
    if not diff_text:
        return None
    lines = original.splitlines()
    out: list[str] = []
    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    src_idx = 0
    diff_lines = diff_text.splitlines()
    i = 0
    # Skip file headers
    while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
        i += 1
    if i >= len(diff_lines):
        return None
    while i < len(diff_lines):
        m = hunk_re.match(diff_lines[i])
        if not m:
            i += 1
            continue
        old_start = int(m.group(1))
        # Copy unchanged lines up to hunk
        while src_idx < old_start - 1 and src_idx < len(lines):
            out.append(lines[src_idx])
            src_idx += 1
        i += 1
        while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
            dl = diff_lines[i]
            if dl.startswith("+") and not dl.startswith("+++"):
                out.append(dl[1:])
            elif dl.startswith("-") and not dl.startswith("---"):
                if src_idx < len(lines):
                    src_idx += 1  # skip removed line
            elif dl.startswith(" "):
                if src_idx < len(lines):
                    out.append(lines[src_idx])
                    src_idx += 1
            i += 1
    # tail
    while src_idx < len(lines):
        out.append(lines[src_idx])
        src_idx += 1
    return "\n".join(out) + ("\n" if original.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def diagnose_and_fix(app, run_id: int, previous_context: Optional[dict] = None) -> None:
    """Entry-point run in a background thread."""
    with app.app_context():
        try:
            _diagnose_and_fix_inner(run_id, previous_context)
        except Exception as exc:
            logger.exception("Auto-fix run %s crashed: %s", run_id, exc)
            run = AutoFixRun.query.get(run_id)
            if run:
                run.status = "fix_failed"
                db.session.commit()
                try:
                    from backend.services.notify_service import notify_owner
                    notify_owner(run.id, "fix_failed")
                except Exception:
                    pass


def _diagnose_and_fix_inner(run_id: int, previous_context: Optional[dict]) -> None:
    run: AutoFixRun = AutoFixRun.query.get(run_id)
    if not run:
        logger.error("AutoFixRun %s not found", run_id)
        return

    project: Project = Project.query.get(run.project_id)
    if not project:
        run.status = "fix_failed"
        db.session.commit()
        return

    token = _get_token_for_project(project)
    if not token:
        logger.warning("No GitHub token for project %s owner; cannot auto-fix", project.id)
        run.status = "fix_failed"
        db.session.commit()
        return

    if run.attempt_count >= MAX_ATTEMPTS:
        run.status = "max_retries_reached"
        db.session.commit()
        _safe_notify(run.id, "max_retries_reached")
        return

    run.status = "diagnosing"
    db.session.commit()

    gh = GitHubService(token)
    owner, repo = project.repo_owner, project.repo_name
    sha = run.trigger_commit_sha

    tree_data = gh.get_repo_tree(owner, repo, sha) or gh.get_repo_tree(owner, repo, run.trigger_branch)
    tree_paths = []
    if tree_data and "tree" in tree_data:
        tree_paths = [t["path"] for t in tree_data["tree"] if t.get("type") == "blob"]

    candidates = _extract_candidate_files(run.failure_log or "", tree_paths)
    file_contents: dict[str, str] = {}
    for path in candidates:
        content = gh.get_file_content(owner, repo, path, sha)
        if content is not None:
            file_contents[path] = content

    ai_result = _call_llm_for_fix(
        failure_log=run.failure_log or "",
        files=file_contents,
        previous_context=previous_context,
        project_id=project.id,
        user_id=project.created_by,
    )

    confidence = float(ai_result.get("confidence") or 0)
    diagnosis = ai_result.get("diagnosis") or ""
    diff_text = ai_result.get("diff") or ""
    files_changed = ai_result.get("files_changed") or list(file_contents.keys())

    # Guard rail: infra / dependency-level or low-confidence => fix_failed
    if (
        confidence < CONFIDENCE_THRESHOLD
        or not diff_text
        or not files_changed
    ):
        run.status = "fix_failed"
        # still record the attempt so the UI shows what the AI thought
        attempt = AutoFixAttempt(
            autofix_run_id=run.id,
            attempt_number=run.attempt_count + 1,
            diagnosis=diagnosis or "AI could not confidently propose a fix.",
            proposed_diff=diff_text or "",
            confidence=confidence,
            pr_status=None,
        )
        attempt.files_changed = files_changed
        db.session.add(attempt)
        run.attempt_count += 1
        db.session.commit()
        _safe_notify(run.id, "fix_failed")
        return

    # Build the fix branch and apply the diff
    branch_name = f"auto-fix/{run.trigger_branch}-{int(time.time())}"
    branch_resp = gh.create_branch(owner, repo, branch_name, run.trigger_branch)
    if isinstance(branch_resp, dict) and "error" in branch_resp:
        logger.error("Auto-fix: failed to create branch %s: %s", branch_name, branch_resp["error"])
        run.status = "fix_failed"
        db.session.commit()
        _safe_notify(run.id, "fix_failed")
        return

    for path in files_changed:
        original = file_contents.get(path) or gh.get_file_content(owner, repo, path, sha) or ""
        patched = _apply_diff_to_content(original, diff_text)
        if patched is None or patched == original:
            # Fallback: skip files we cannot patch cleanly
            logger.warning("Auto-fix could not apply diff to %s; skipping", path)
            continue
        commit_msg = f"fix: {_short(diagnosis, 60)}"
        _put_file(gh, owner, repo, path, branch_name, patched, commit_msg)

    # Open PR
    failure_summary = run.failure_summary or _summarize_failure(run.failure_log or "")
    pr_title = f"🤖 Auto-Fix: {failure_summary[:120]}"
    pr_body = (
        f"## What broke\n{failure_summary}\n\n"
        f"## AI diagnosis\n{diagnosis}\n\n"
        f"## Files changed\n" + "\n".join(f"- `{p}`" for p in files_changed) + "\n\n"
        f"## Confidence: {confidence:.2f}\n\n"
        "---\n"
        "> This PR was generated by HiFi's AI auto-fix agent. "
        "Review the diff before merging."
    )
    pr_resp = gh.create_pull_request(owner, repo, pr_title, branch_name, run.trigger_branch, pr_body)
    if isinstance(pr_resp, dict) and "error" in pr_resp:
        logger.error("Auto-fix: PR creation failed: %s", pr_resp["error"])
        run.status = "fix_failed"
        db.session.commit()
        _safe_notify(run.id, "fix_failed")
        return

    attempt = AutoFixAttempt(
        autofix_run_id=run.id,
        attempt_number=run.attempt_count + 1,
        diagnosis=diagnosis,
        proposed_diff=diff_text,
        confidence=confidence,
        pr_url=pr_resp.get("html_url"),
        pr_status="open",
    )
    attempt.files_changed = files_changed
    db.session.add(attempt)

    run.attempt_count += 1
    run.status = "pr_opened"
    run.pr_url = pr_resp.get("html_url")
    run.pr_number = pr_resp.get("number")
    if not run.failure_summary:
        run.failure_summary = failure_summary
    db.session.commit()

    _safe_notify(run.id, "fix_generated")


def _short(text: str, n: int) -> str:
    text = (text or "").splitlines()[0] if text else ""
    return text[:n]


def _put_file(gh: GitHubService, owner: str, repo: str, path: str, branch: str, content: str, message: str) -> None:
    url = f"{gh.BASE}/repos/{owner}/{repo}/contents/{path}"
    existing = requests.get(url, headers=gh.headers, params={"ref": branch}, timeout=15)
    sha = existing.json().get("sha") if existing.ok else None
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=gh.headers, json=payload, timeout=20)
    if not resp.ok:
        logger.error("Auto-fix: PUT %s failed: %s", path, resp.text[:200])


def _call_llm_for_fix(
    failure_log: str,
    files: dict[str, str],
    previous_context: Optional[dict],
    project_id: int,
    user_id: int,
) -> dict:
    ai = AIService()
    system = (
        "You are a CI/CD auto-fix agent. You receive a CI failure log and the "
        "relevant source files. Your job is to: (1) identify the exact bug, "
        "(2) propose a minimal fix as a unified diff. Do not rewrite entire files "
        "— fix only what's broken. Dependency/version conflicts or missing packages "
        "are infra-level; for those return confidence: 0 and no diff. "
        'Return ONLY JSON: {"diagnosis": string, "diff": string, '
        '"files_changed": array, "confidence": number between 0 and 1}.'
    )
    files_blob = "\n\n".join(f"### FILE: {p}\n```\n{c}\n```" for p, c in files.items()) or "(no files fetched)"
    prev_blob = ""
    if previous_context:
        prev_blob = (
            "\n\nYour previous fix did not resolve the issue.\n"
            f"Previous diagnosis: {previous_context.get('diagnosis', '')}\n"
            f"Previous diff:\n{previous_context.get('diff', '')}\n"
            "Try a different approach.\n"
        )
    user = f"CI FAILURE LOG (last 200 lines):\n```\n{failure_log[-8000:]}\n```\n\nFILES:\n{files_blob}{prev_blob}"

    success = True
    text = ""
    try:
        if not ai.client:
            raise RuntimeError("AI client not configured")
        resp = ai.client.chat.completions.create(
            model=ai.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=1500,
            temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
    except Exception as exc:
        logger.error("Auto-fix LLM call failed: %s", exc)
        success = False
        text = ""

    # Log usage
    try:
        log = AiUsageLog(
            user_id=user_id,
            project_id=project_id,
            task_type="autofix_diagnosis",
            model=ai.model,
            success=success,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Extract JSON from response
    parsed = _extract_json(text)
    if not parsed:
        return {"diagnosis": "AI response was not parseable JSON.", "diff": "", "files_changed": [], "confidence": 0}
    return {
        "diagnosis": str(parsed.get("diagnosis", ""))[:4000],
        "diff": str(parsed.get("diff", "")),
        "files_changed": list(parsed.get("files_changed") or []),
        "confidence": float(parsed.get("confidence") or 0),
    }


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    text = text.strip()
    # Strip markdown fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        # Try to find outermost { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _safe_notify(run_id: int, event_type: str) -> None:
    try:
        from backend.services.notify_service import notify_owner
        notify_owner(run_id, event_type)
    except Exception:
        logger.exception("notify_owner failed for run %s", run_id)


def fetch_failure_log_from_github(gh: GitHubService, owner: str, repo: str, commit_sha: str) -> str:
    """Phase 13 — fetch the failing run's logs for a specific commit."""
    try:
        runs_resp = requests.get(
            f"{gh.BASE}/repos/{owner}/{repo}/actions/runs",
            headers=gh.headers, params={"head_sha": commit_sha}, timeout=20,
        )
        if not runs_resp.ok:
            return ""
        runs = runs_resp.json().get("workflow_runs", [])
        failed = next((r for r in runs if r.get("conclusion") == "failure"), None) or (runs[0] if runs else None)
        if not failed:
            return ""
        run_id = failed["id"]
        logs_resp = requests.get(
            f"{gh.BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/logs",
            headers=gh.headers, timeout=30, allow_redirects=True,
        )
        if not logs_resp.ok:
            return ""
        # logs endpoint returns a zip; try to decode as text best-effort
        content = logs_resp.content
        try:
            import io, zipfile
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                collected = []
                for name in zf.namelist():
                    if name.endswith(".txt"):
                        collected.append(zf.read(name).decode("utf-8", errors="replace"))
                text = "\n".join(collected)
        except Exception:
            text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[-200:])
    except Exception as exc:
        logger.warning("fetch_failure_log_from_github failed: %s", exc)
        return ""
