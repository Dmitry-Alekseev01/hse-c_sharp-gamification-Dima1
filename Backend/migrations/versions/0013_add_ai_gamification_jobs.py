"""add ai gamification jobs

Revision ID: 0013_add_ai_gamification_jobs
Revises: 0012_drop_unused_mvs
Create Date: 2026-04-15 16:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_add_ai_gamification_jobs"
down_revision = "0012_drop_unused_mvs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_gamification_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("source_snapshot", sa.Text(), nullable=True),
        sa.Column("target_level", sa.String(length=30), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False, server_default=sa.text("'ru'")),
        sa.Column("style", sa.String(length=30), nullable=True),
        sa.Column("tone", sa.String(length=30), nullable=True),
        sa.Column("constraints_json", sa.JSON(), nullable=True),
        sa.Column("draft_json", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("provider", sa.String(length=120), nullable=True),
        sa.Column("usage_json", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("applied_target_type", sa.String(length=30), nullable=True),
        sa.Column("applied_target_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_ai_gamification_jobs_created_by_user_id", "ai_gamification_jobs", ["created_by_user_id"])
    op.create_index("ix_ai_gamification_jobs_source_id", "ai_gamification_jobs", ["source_id"])
    op.create_index("ix_ai_gamification_jobs_source_type", "ai_gamification_jobs", ["source_type"])
    op.create_index("ix_ai_gamification_jobs_status", "ai_gamification_jobs", ["status"])


def downgrade():
    op.drop_index("ix_ai_gamification_jobs_status", table_name="ai_gamification_jobs")
    op.drop_index("ix_ai_gamification_jobs_source_type", table_name="ai_gamification_jobs")
    op.drop_index("ix_ai_gamification_jobs_source_id", table_name="ai_gamification_jobs")
    op.drop_index("ix_ai_gamification_jobs_created_by_user_id", table_name="ai_gamification_jobs")
    op.drop_table("ai_gamification_jobs")

