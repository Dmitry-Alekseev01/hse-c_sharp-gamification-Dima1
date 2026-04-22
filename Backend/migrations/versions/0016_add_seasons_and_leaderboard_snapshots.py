"""add seasons and leaderboard snapshots

Revision ID: 0016_add_seasons
Revises: 0015_add_challenges
Create Date: 2026-04-22 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_add_seasons"
down_revision = "0015_add_challenges"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_seasons_code", "seasons", ["code"])
    op.create_index("ix_seasons_starts_at", "seasons", ["starts_at"])
    op.create_index("ix_seasons_ends_at", "seasons", ["ends_at"])
    op.create_index("ix_seasons_is_active", "seasons", ["is_active"])
    op.create_index("ix_seasons_created_by", "seasons", ["created_by"])

    op.create_table(
        "leaderboard_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("season_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bucket_start", sa.DateTime(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["group_id"], ["study_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope",
            "period",
            "group_id",
            "season_id",
            "user_id",
            "bucket_start",
            name="uq_leaderboard_snapshot_identity",
        ),
    )
    op.create_index("ix_leaderboard_snapshots_scope", "leaderboard_snapshots", ["scope"])
    op.create_index("ix_leaderboard_snapshots_period", "leaderboard_snapshots", ["period"])
    op.create_index("ix_leaderboard_snapshots_group_id", "leaderboard_snapshots", ["group_id"])
    op.create_index("ix_leaderboard_snapshots_season_id", "leaderboard_snapshots", ["season_id"])
    op.create_index("ix_leaderboard_snapshots_user_id", "leaderboard_snapshots", ["user_id"])
    op.create_index("ix_leaderboard_snapshots_bucket_start", "leaderboard_snapshots", ["bucket_start"])


def downgrade():
    op.drop_index("ix_leaderboard_snapshots_bucket_start", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_user_id", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_season_id", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_group_id", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_period", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_scope", table_name="leaderboard_snapshots")
    op.drop_table("leaderboard_snapshots")

    op.drop_index("ix_seasons_created_by", table_name="seasons")
    op.drop_index("ix_seasons_is_active", table_name="seasons")
    op.drop_index("ix_seasons_ends_at", table_name="seasons")
    op.drop_index("ix_seasons_starts_at", table_name="seasons")
    op.drop_index("ix_seasons_code", table_name="seasons")
    op.drop_table("seasons")
