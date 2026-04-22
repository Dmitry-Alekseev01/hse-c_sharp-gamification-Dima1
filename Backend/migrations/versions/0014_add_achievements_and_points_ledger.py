"""add achievements and points ledger

Revision ID: 0014_achievements_ledger
Revises: 0013_add_ai_gamification_jobs
Create Date: 2026-04-21 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_achievements_ledger"
down_revision = "0013_add_ai_gamification_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "achievement_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reward", sa.String(length=255), nullable=True),
        sa.Column("criteria_type", sa.String(length=50), nullable=False),
        sa.Column("threshold_value", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_achievement_definitions_code", "achievement_definitions", ["code"])
    op.create_index("ix_achievement_definitions_criteria_type", "achievement_definitions", ["criteria_type"])

    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("source_event", sa.String(length=120), nullable=True),
        sa.Column("earned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievement_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement_user_achievement"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])
    op.create_index("ix_user_achievements_achievement_id", "user_achievements", ["achievement_id"])

    op.create_table(
        "points_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_points_ledger_user_id", "points_ledger", ["user_id"])
    op.create_index("ix_points_ledger_reason_code", "points_ledger", ["reason_code"])
    op.create_index("ix_points_ledger_source_type", "points_ledger", ["source_type"])
    op.create_index("ix_points_ledger_source_id", "points_ledger", ["source_id"])
    op.create_index("ix_points_ledger_idempotency_key", "points_ledger", ["idempotency_key"])
    op.create_index("ix_points_ledger_created_at", "points_ledger", ["created_at"])

    achievement_definitions = sa.table(
        "achievement_definitions",
        sa.column("code", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("reward", sa.String),
        sa.column("criteria_type", sa.String),
        sa.column("threshold_value", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        achievement_definitions,
        [
            {
                "code": "first_steps",
                "title": "First Steps",
                "description": "Complete your first test attempt.",
                "reward": "Unlock your first achievement badge.",
                "criteria_type": "completed_attempts",
                "threshold_value": 1,
                "is_active": True,
            },
            {
                "code": "focused_three",
                "title": "3-Day Streak",
                "description": "Stay active for 3 consecutive days.",
                "reward": "Showcase consistency in your profile.",
                "criteria_type": "streak_days",
                "threshold_value": 3,
                "is_active": True,
            },
            {
                "code": "focused_week",
                "title": "7-Day Streak",
                "description": "Stay active for 7 consecutive days.",
                "reward": "Highlight long-running learning momentum.",
                "criteria_type": "streak_days",
                "threshold_value": 7,
                "is_active": True,
            },
            {
                "code": "century_points",
                "title": "100 Points",
                "description": "Earn at least 100 total points.",
                "reward": "Prove solid progress in the course.",
                "criteria_type": "total_points",
                "threshold_value": 100,
                "is_active": True,
            },
            {
                "code": "test_marathon",
                "title": "5 Completed Tests",
                "description": "Finish 5 test attempts.",
                "reward": "Unlock marathon learner status.",
                "criteria_type": "completed_attempts",
                "threshold_value": 5,
                "is_active": True,
            },
        ],
    )


def downgrade():
    op.drop_index("ix_points_ledger_created_at", table_name="points_ledger")
    op.drop_index("ix_points_ledger_idempotency_key", table_name="points_ledger")
    op.drop_index("ix_points_ledger_source_id", table_name="points_ledger")
    op.drop_index("ix_points_ledger_source_type", table_name="points_ledger")
    op.drop_index("ix_points_ledger_reason_code", table_name="points_ledger")
    op.drop_index("ix_points_ledger_user_id", table_name="points_ledger")
    op.drop_table("points_ledger")

    op.drop_index("ix_user_achievements_achievement_id", table_name="user_achievements")
    op.drop_index("ix_user_achievements_user_id", table_name="user_achievements")
    op.drop_table("user_achievements")

    op.drop_index("ix_achievement_definitions_criteria_type", table_name="achievement_definitions")
    op.drop_index("ix_achievement_definitions_code", table_name="achievement_definitions")
    op.drop_table("achievement_definitions")
