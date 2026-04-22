"""harden model-schema contract constraints

Revision ID: 0017_contract_hardening
Revises: 0016_add_seasons
Create Date: 2026-04-22 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_contract_hardening"
down_revision = "0016_add_seasons"
branch_labels = None
depends_on = None


def upgrade():
    # Normalize potentially dirty data before adding constraints.
    op.execute(
        """
        UPDATE users
        SET role = 'user'
        WHERE role IS NULL OR role NOT IN ('user', 'teacher', 'admin')
        """
    )
    op.execute(
        """
        UPDATE materials
        SET material_type = 'lesson'
        WHERE material_type IS NULL OR material_type NOT IN ('lesson', 'module', 'article')
        """
    )
    op.execute(
        """
        UPDATE materials
        SET status = 'published'
        WHERE status IS NULL OR status NOT IN ('draft', 'published', 'archived')
        """
    )
    op.execute(
        """
        UPDATE challenges
        SET period_type = 'daily'
        WHERE period_type IS NULL OR period_type NOT IN ('daily', 'weekly')
        """
    )
    op.execute(
        """
        UPDATE challenges
        SET event_type = 'answer_submitted'
        WHERE event_type IS NULL OR event_type NOT IN ('answer_submitted', 'attempt_completed', 'streak_day')
        """
    )
    op.execute(
        """
        UPDATE ai_gamification_jobs
        SET status = 'pending'
        WHERE status IS NULL OR status NOT IN ('pending', 'running', 'completed', 'failed', 'applied')
        """
    )
    op.execute(
        """
        UPDATE ai_gamification_jobs
        SET source_type = 'raw_text'
        WHERE source_type IS NULL OR source_type NOT IN ('material', 'question', 'raw_text')
        """
    )
    op.execute(
        """
        UPDATE ai_gamification_jobs
        SET target_level = NULL
        WHERE target_level IS NOT NULL
          AND target_level NOT IN ('beginner', 'intermediate', 'advanced')
        """
    )
    op.execute(
        """
        UPDATE ai_gamification_jobs
        SET style = NULL
        WHERE style IS NOT NULL
          AND style NOT IN ('quest', 'mission', 'challenge', 'story')
        """
    )
    op.execute(
        """
        UPDATE ai_gamification_jobs
        SET tone = NULL
        WHERE tone IS NOT NULL
          AND tone NOT IN ('neutral', 'friendly', 'energetic')
        """
    )
    op.execute(
        """
        UPDATE ai_gamification_jobs
        SET applied_target_type = NULL
        WHERE applied_target_type IS NOT NULL
          AND applied_target_type NOT IN ('material', 'question')
        """
    )
    op.execute(
        """
        UPDATE answers
        SET answer_payload = '[missing-answer]'
        WHERE answer_payload IS NULL
        """
    )
    op.execute(
        """
        UPDATE answers
        SET created_at = NOW()
        WHERE created_at IS NULL
        """
    )

    op.alter_column("answers", "answer_payload", existing_type=sa.Text(), nullable=False)
    op.alter_column("answers", "created_at", existing_type=sa.DateTime(), nullable=False)

    op.create_check_constraint(
        "ck_users_role_valid",
        "users",
        "role IN ('user', 'teacher', 'admin')",
    )
    op.create_check_constraint(
        "ck_materials_type_valid",
        "materials",
        "material_type IN ('lesson', 'module', 'article')",
    )
    op.create_check_constraint(
        "ck_materials_status_valid",
        "materials",
        "status IN ('draft', 'published', 'archived')",
    )
    op.create_check_constraint(
        "ck_challenges_period_type_valid",
        "challenges",
        "period_type IN ('daily', 'weekly')",
    )
    op.create_check_constraint(
        "ck_challenges_event_type_valid",
        "challenges",
        "event_type IN ('answer_submitted', 'attempt_completed', 'streak_day')",
    )
    op.create_check_constraint(
        "ck_ai_jobs_status_valid",
        "ai_gamification_jobs",
        "status IN ('pending', 'running', 'completed', 'failed', 'applied')",
    )
    op.create_check_constraint(
        "ck_ai_jobs_source_type_valid",
        "ai_gamification_jobs",
        "source_type IN ('material', 'question', 'raw_text')",
    )
    op.create_check_constraint(
        "ck_ai_jobs_target_level_valid",
        "ai_gamification_jobs",
        "target_level IS NULL OR target_level IN ('beginner', 'intermediate', 'advanced')",
    )
    op.create_check_constraint(
        "ck_ai_jobs_style_valid",
        "ai_gamification_jobs",
        "style IS NULL OR style IN ('quest', 'mission', 'challenge', 'story')",
    )
    op.create_check_constraint(
        "ck_ai_jobs_tone_valid",
        "ai_gamification_jobs",
        "tone IS NULL OR tone IN ('neutral', 'friendly', 'energetic')",
    )
    op.create_check_constraint(
        "ck_ai_jobs_applied_target_type_valid",
        "ai_gamification_jobs",
        "applied_target_type IS NULL OR applied_target_type IN ('material', 'question')",
    )


def downgrade():
    op.drop_constraint("ck_ai_jobs_applied_target_type_valid", "ai_gamification_jobs", type_="check")
    op.drop_constraint("ck_ai_jobs_tone_valid", "ai_gamification_jobs", type_="check")
    op.drop_constraint("ck_ai_jobs_style_valid", "ai_gamification_jobs", type_="check")
    op.drop_constraint("ck_ai_jobs_target_level_valid", "ai_gamification_jobs", type_="check")
    op.drop_constraint("ck_ai_jobs_source_type_valid", "ai_gamification_jobs", type_="check")
    op.drop_constraint("ck_ai_jobs_status_valid", "ai_gamification_jobs", type_="check")
    op.drop_constraint("ck_challenges_event_type_valid", "challenges", type_="check")
    op.drop_constraint("ck_challenges_period_type_valid", "challenges", type_="check")
    op.drop_constraint("ck_materials_status_valid", "materials", type_="check")
    op.drop_constraint("ck_materials_type_valid", "materials", type_="check")
    op.drop_constraint("ck_users_role_valid", "users", type_="check")

    op.alter_column("answers", "created_at", existing_type=sa.DateTime(), nullable=True)
    op.alter_column("answers", "answer_payload", existing_type=sa.Text(), nullable=True)
