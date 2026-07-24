"""Phase 11 — autofix_runs, autofix_attempts, ai_usage_logs

Revision ID: a1b2c3d4e5f6
Revises: 4d4215a87fae
Create Date: 2026-07-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "4d4215a87fae"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "autofix_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("trigger_branch", sa.String(256), nullable=False),
        sa.Column("trigger_commit_sha", sa.String(64), nullable=False),
        sa.Column("failure_log", sa.Text(), nullable=True),
        sa.Column("failure_summary", sa.String(512), nullable=True),
        sa.Column("status", sa.String(64), nullable=False, server_default="received"),
        sa.Column("pr_url", sa.String(512), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_date", sa.DateTime(), nullable=True),
        sa.Column("updated_date", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_autofix_runs_project", "autofix_runs", ["project_id"])

    op.create_table(
        "autofix_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("autofix_run_id", sa.Integer(), sa.ForeignKey("autofix_runs.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("proposed_diff", sa.Text(), nullable=True),
        sa.Column("files_changed", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("pr_url", sa.String(512), nullable=True),
        sa.Column("pr_status", sa.String(32), nullable=True, server_default="open"),
        sa.Column("created_date", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_autofix_attempts_run", "autofix_attempts", ["autofix_run_id"])

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("ai_usage_logs")
    op.drop_index("ix_autofix_attempts_run", table_name="autofix_attempts")
    op.drop_table("autofix_attempts")
    op.drop_index("ix_autofix_runs_project", table_name="autofix_runs")
    op.drop_table("autofix_runs")
