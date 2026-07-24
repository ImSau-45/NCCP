import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "hifi_pipeline_secret_change_me")
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///hifi_local.db")
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"connect_args": {"check_same_thread": False}}
        if _db_url.startswith("sqlite")
        else {}
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "hifi_jwt_secret_change_me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
    GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "secret")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL = int(os.environ.get("REDIS_CACHE_TTL", 300))

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "pipeline-sh-artifacts")
    AWS_EC2_KEY_NAME = os.environ.get("AWS_EC2_KEY_NAME", "pipeline-sh-ec2-key")
    AWS_SSH_USER = os.environ.get("AWS_SSH_USER", "ubuntu")

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
