from flask import current_app

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - depends on runtime packaging availability
    BackgroundScheduler = None


def sync_repositories(app):
    with app.app_context():
        app.logger.info("Running scheduled repository sync")


def configure_scheduler(app):
    if app.extensions.get("scheduler_started"):
        return None

    if BackgroundScheduler is None:
        app.extensions["scheduler_started"] = True
        app.logger.warning("APScheduler is unavailable; continuing without background scheduler")
        return None

    try:
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            func=sync_repositories,
            trigger="interval",
            minutes=10,
            id="repo-sync",
            args=[app]
        )
        scheduler.start()
        app.extensions["scheduler_started"] = True
        app.logger.info("Scheduler configured for Pipeline.sh")
    except Exception as exc:
        app.logger.exception("Scheduler configuration failed: %s", exc)
        return None

    return scheduler
