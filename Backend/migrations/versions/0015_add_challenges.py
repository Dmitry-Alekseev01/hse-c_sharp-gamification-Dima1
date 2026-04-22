"""add challenges and user challenge progress/claims

Revision ID: 0015_add_challenges
Revises: 0014_achievements_ledger
Create Date: 2026-04-22 13:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_add_challenges"
down_revision = "0014_achievements_ledger"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("reward_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_challenges_code", "challenges", ["code"])
    op.create_index("ix_challenges_period_type", "challenges", ["period_type"])
    op.create_index("ix_challenges_event_type", "challenges", ["event_type"])
    op.create_index("ix_challenges_is_active", "challenges", ["is_active"])
    op.create_index("ix_challenges_created_by", "challenges", ["created_by"])

    op.create_table(
        "user_challenge_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("progress_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "challenge_id", "period_key", name="uq_user_challenge_progress_period"),
    )
    op.create_index("ix_user_challenge_progress_user_id", "user_challenge_progress", ["user_id"])
    op.create_index("ix_user_challenge_progress_challenge_id", "user_challenge_progress", ["challenge_id"])
    op.create_index("ix_user_challenge_progress_period_key", "user_challenge_progress", ["period_key"])

    op.create_table(
        "user_challenge_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("reward_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["points_ledger.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "challenge_id", "period_key", name="uq_user_challenge_claim_period"),
    )
    op.create_index("ix_user_challenge_claims_user_id", "user_challenge_claims", ["user_id"])
    op.create_index("ix_user_challenge_claims_challenge_id", "user_challenge_claims", ["challenge_id"])
    op.create_index("ix_user_challenge_claims_period_key", "user_challenge_claims", ["period_key"])
    op.create_index("ix_user_challenge_claims_ledger_entry_id", "user_challenge_claims", ["ledger_entry_id"])
    op.create_index("ix_user_challenge_claims_claimed_at", "user_challenge_claims", ["claimed_at"])


def downgrade():
    op.drop_index("ix_user_challenge_claims_claimed_at", table_name="user_challenge_claims")
    op.drop_index("ix_user_challenge_claims_ledger_entry_id", table_name="user_challenge_claims")
    op.drop_index("ix_user_challenge_claims_period_key", table_name="user_challenge_claims")
    op.drop_index("ix_user_challenge_claims_challenge_id", table_name="user_challenge_claims")
    op.drop_index("ix_user_challenge_claims_user_id", table_name="user_challenge_claims")
    op.drop_table("user_challenge_claims")

    op.drop_index("ix_user_challenge_progress_period_key", table_name="user_challenge_progress")
    op.drop_index("ix_user_challenge_progress_challenge_id", table_name="user_challenge_progress")
    op.drop_index("ix_user_challenge_progress_user_id", table_name="user_challenge_progress")
    op.drop_table("user_challenge_progress")

    op.drop_index("ix_challenges_created_by", table_name="challenges")
    op.drop_index("ix_challenges_is_active", table_name="challenges")
    op.drop_index("ix_challenges_event_type", table_name="challenges")
    op.drop_index("ix_challenges_period_type", table_name="challenges")
    op.drop_index("ix_challenges_code", table_name="challenges")
    op.drop_table("challenges")
