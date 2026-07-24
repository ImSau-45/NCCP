import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

from backend.config import Config
from backend.db import db
from backend.routes.analytics import analytics_bp
from backend.routes.auth import auth_bp
from backend.routes.autofix import autofix_bp
from backend.routes.deploy import deploy_bp
from backend.routes.github import github_bp
from backend.routes.pipeline import pipeline_bp
from backend.routes.projects import projects_bp
from backend.routes.workflow import workflow_bp
from backend.tasks import configure_scheduler


def create_app(test_config: dict = None):
    load_dotenv()
    app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )
    app.logger.setLevel(log_level)

    CORS(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://localhost:4173",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ])
    JWTManager(app)
    db.init_app(app)
    Migrate(app, db)

    blueprints = [
        (auth_bp, "/api/auth"),
        (github_bp, "/api/github"),
        (pipeline_bp, "/api/pipelines"),
        (deploy_bp, "/api/deploy"),
        (analytics_bp, "/api/analytics"),
        (workflow_bp, "/api/workflow"),
        (projects_bp, "/api/projects"),
        (autofix_bp, "/api/autofix"),
    ]
    for blueprint, prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=prefix)

    if not app.extensions.get("scheduler_configured"):
        configure_scheduler(app)
        app.extensions["scheduler_configured"] = True

    @app.route("/api/health")
    def health():
        db_status, db_error = "ok", None
        try:
            with app.app_context():
                db.engine.connect().close()
        except Exception as exc:
            db_status, db_error = "unavailable", str(exc)

        redis_status, redis_error = "ok", None
        try:
            from redis import Redis
            Redis.from_url(app.config["REDIS_URL"], decode_responses=True).ping()
        except Exception as exc:
            redis_status, redis_error = "unavailable", str(exc)

        overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
        return jsonify({
            "status": overall,
            "service": "HiFi API",
            "version": "1.0.0",
            "database": {"status": db_status, "error": db_error},
            "redis": {"status": redis_status, "error": redis_error},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def frontend(path):
        # Let API routes 404 normally
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        # For all SPA routes, always serve index.html
        import os as _os
        index = _os.path.join(app.static_folder, "index.html")
        if _os.path.exists(index):
            return app.send_static_file("index.html")
        return jsonify({"error": "Frontend not built. Run: cd frontend && npm run build"}), 503

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
