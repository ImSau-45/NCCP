from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from backend.services.tf_predictor import TFPredictor

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard_metrics():
    predictor = TFPredictor()
    prediction = predictor.predict_failure_risk({"recent_failures": 3, "success_rate": 0.82})
    metrics = {
        "active_repos": 12,
        "success_rate": 86.1,
        "deployment_health": "green",
        "failure_risk_score": prediction.get("failure_risk"),
        "recommendations": [
            "Use parallel test stages",
            "Cache Docker layers",
            "Use feature branches for staging deployments",
        ],
    }
    return jsonify(metrics)
