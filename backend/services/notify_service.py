"""
Phase 15 — Owner notifications via Gmail (SMTP fallback).

Uses standard SMTP with a Gmail App Password when GMAIL_USER / GMAIL_APP_PASSWORD
are configured; otherwise falls back to writing a Notification record so nothing
is lost.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

from backend.db import db
from backend.models import AutoFixRun, Notification, Project, User, UserProfile

logger = logging.getLogger(__name__)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _resolve_recipient(project: Project) -> tuple[str | None, User | None]:
    user = User.query.get(project.created_by)
    if not user:
        return None, None
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    email = (profile.notification_email if profile and profile.notification_email else user.email)
    return email, user


def _send_via_gmail(to: str, subject: str, body: str) -> bool:
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    if not (gmail_user and gmail_pass and to):
        return False
    try:
        msg = EmailMessage()
        msg["From"] = gmail_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(gmail_user, gmail_pass)
            s.send_message(msg)
        return True
    except Exception as exc:
        logger.error("Gmail send failed: %s", exc)
        return False


def notify_owner(autofix_run_id: int, event_type: str) -> None:
    run: AutoFixRun | None = AutoFixRun.query.get(autofix_run_id)
    if not run:
        logger.warning("notify_owner: run %s not found", autofix_run_id)
        return
    project: Project | None = Project.query.get(run.project_id)
    if not project:
        return

    to, user = _resolve_recipient(project)
    repo_name = f"{project.repo_owner}/{project.repo_name}"
    branch = run.trigger_branch
    summary = run.failure_summary or "CI failure"
    dashboard_link = f"{FRONTEND_URL}/projects/{project.id}/autofix/{run.id}"

    latest_attempt = run.attempts.order_by(None).order_by(None).all()
    latest_diagnosis = latest_attempt[-1].diagnosis if latest_attempt else ""
    latest_conf = latest_attempt[-1].confidence if latest_attempt else 0.0

    if event_type == "fix_generated":
        subject = f"HiFi Auto-Fix: PR opened for {repo_name}"
        body = (
            f"A push to {branch} triggered a CI failure. HiFi's AI diagnosed a "
            f"{summary!r} and opened a fix PR.\n\n"
            f"Review and merge: {run.pr_url or dashboard_link}\n"
            f"Confidence: {latest_conf:.2f}\n\n"
            f"Dashboard: {dashboard_link}\n"
        )
    elif event_type == "fix_failed":
        subject = f"HiFi Auto-Fix: Could not auto-resolve error in {repo_name}"
        body = (
            f"A CI failure was detected on {branch} but the AI couldn't confidently "
            f"propose a fix.\n\n"
            f"Failure summary: {summary}\n"
            f"CI log: {dashboard_link}\n\n"
            "Manual review needed.\n"
        )
    elif event_type == "max_retries_reached":
        subject = f"HiFi Auto-Fix: Stopped after 3 attempts on {repo_name}"
        body = (
            "The AI tried 3 fix attempts but CI is still failing.\n\n"
            f"Last diagnosis: {latest_diagnosis or 'n/a'}\n\n"
            f"Please review manually: {dashboard_link}\n"
        )
    elif event_type == "fix_merged":
        subject = f"HiFi Auto-Fix: PR merged for {repo_name}"
        body = (
            f"Your auto-fix PR for {repo_name} was merged.\n\n"
            f"Diagnosis: {latest_diagnosis or 'n/a'}\n"
            f"Dashboard: {dashboard_link}\n"
        )
    else:
        subject = f"HiFi Auto-Fix event: {event_type} — {repo_name}"
        body = f"Event: {event_type}\nDashboard: {dashboard_link}"

    sent = _send_via_gmail(to, subject, body) if to else False

    # Always record an in-app notification too
    try:
        if user:
            note = Notification(user_id=user.id, title=subject, body=body)
            db.session.add(note)
            db.session.commit()
    except Exception:
        db.session.rollback()

    logger.info("notify_owner event=%s run=%s sent=%s", event_type, autofix_run_id, sent)
