import logging
import os

import requests
from flask import Blueprint, current_app, jsonify, redirect, request, url_for
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from backend.db import db
from backend.models import User, UserProfile

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


def _user_payload(user: User) -> dict:
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "github_connected": profile.github_connected if profile else False,
        "github_login": profile.github_login if profile else None,
        "notification_email": profile.notification_email if profile else user.email,
    }


def _ensure_profile(user: User) -> UserProfile:
    if not user.profile:
        profile = UserProfile(
            user_id=user.id,
            github_connected=False,
            notification_email=user.email,
        )
        db.session.add(profile)
        db.session.commit()
    return user.profile


def _get_user(user_id_str) -> User | None:
    try:
        return User.query.get(int(user_id_str))
    except (TypeError, ValueError):
        return None


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists"}), 409

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        name=name or email.split("@")[0],
        role="developer",
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(UserProfile(user_id=user.id, github_connected=False, notification_email=email))
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": _user_payload(user)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    _ensure_profile(user)
    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": _user_payload(user)})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = _get_user(get_jwt_identity())
    if not user:
        return jsonify({"error": "User not found"}), 404
    _ensure_profile(user)
    return jsonify({"user": _user_payload(user)})


@auth_bp.route("/google", methods=["POST"])
def google_signin():
    data = request.get_json() or {}
    id_token_str = data.get("id_token")
    if not id_token_str:
        return jsonify({"error": "id_token is required"}), 400

    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": id_token_str},
        timeout=10,
    )
    if not resp.ok:
        return jsonify({"error": "Invalid Google token"}), 401

    info = resp.json()
    google_id = info.get("sub")
    email = info.get("email", "").lower()
    name = info.get("name", "")
    avatar_url = info.get("picture", "")

    if not google_id or not email:
        return jsonify({"error": "Google token missing required fields"}), 400

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
            user.avatar_url = avatar_url or user.avatar_url
        else:
            user = User(email=email, google_id=google_id, name=name, avatar_url=avatar_url, role="developer")
            db.session.add(user)
            db.session.flush()
    else:
        user.avatar_url = avatar_url or user.avatar_url

    _ensure_profile(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": _user_payload(user)})


@auth_bp.route("/github/login/url")
@jwt_required()
def github_login_url():
    client_id = current_app.config.get("GITHUB_CLIENT_ID", "")
    if not client_id:
        return jsonify({"error": "GitHub OAuth is not configured. Add GITHUB_CLIENT_ID to .env"}), 503
    backend_url = current_app.config.get("BACKEND_URL") or "http://localhost:5000"
    redirect_uri = f"{backend_url.rstrip('/')}/api/auth/github/callback"
    state = get_jwt_identity()
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}&scope=repo,read:org,workflow&redirect_uri={redirect_uri}&state={state}"
    )
    return jsonify({"url": url})


@auth_bp.route("/github/login")
@jwt_required()
def github_login():
    client_id = current_app.config["GITHUB_CLIENT_ID"]
    backend_url = current_app.config.get("BACKEND_URL") or "http://localhost:5000"
    redirect_uri = f"{backend_url.rstrip('/')}/api/auth/github/callback"
    state = get_jwt_identity()  # already a string
    return redirect(
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}&scope=repo,read:org,workflow&redirect_uri={redirect_uri}&state={state}"
    )


@auth_bp.route("/github/callback")
def github_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    client_id = current_app.config["GITHUB_CLIENT_ID"]
    client_secret = current_app.config["GITHUB_CLIENT_SECRET"]

    token_resp = requests.post(
        "https://github.com/login/oauth/access_token",
        json={"client_id": client_id, "client_secret": client_secret, "code": code},
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return jsonify({"error": "GitHub OAuth failed — no access token returned"}), 400

    gh_user = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    ).json()

    github_id = str(gh_user.get("id"))
    github_login_name = gh_user.get("login")

    user = _get_user(state) if state else None
    if not user:
        user = User.query.filter_by(github_id=github_id).first()
        if not user:
            email = gh_user.get("email") or f"{github_id}@github.invalid"
            user = User(email=email, github_id=github_id, name=gh_user.get("name"), role="developer")
            db.session.add(user)
            db.session.flush()

    user.github_id = github_id
    profile = _ensure_profile(user)
    profile.github_connected = True
    profile.github_access_token = access_token
    profile.github_login = github_login_name
    db.session.commit()

    jwt_token = create_access_token(identity=str(user.id))
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return redirect(f"{frontend_url}/auth/github/success?token={jwt_token}")


@auth_bp.route("/profile", methods=["PATCH"])
@jwt_required()
def update_profile():
    user = _get_user(get_jwt_identity())
    if not user:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() or {}
    profile = _ensure_profile(user)

    if "notification_email" in data:
        profile.notification_email = data["notification_email"]
    if "name" in data:
        user.name = data["name"]

    db.session.commit()
    return jsonify({"user": _user_payload(user)})


@auth_bp.route("/github/disconnect", methods=["POST"])
@jwt_required()
def disconnect_github():
    user = _get_user(get_jwt_identity())
    if not user:
        return jsonify({"error": "Not found"}), 404

    profile = _ensure_profile(user)
    profile.github_connected = False
    profile.github_access_token = None
    profile.github_login = None
    user.github_id = None
    db.session.commit()
    return jsonify({"message": "GitHub disconnected", "user": _user_payload(user)})
