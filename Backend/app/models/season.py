from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    snapshots = relationship(
        "LeaderboardSnapshot",
        back_populates="season",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "period",
            "group_id",
            "season_id",
            "user_id",
            "bucket_start",
            name="uq_leaderboard_snapshot_identity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String(20), nullable=False, index=True)  # global | group
    period = Column(String(20), nullable=False, index=True)  # all_time | week | season
    group_id = Column(Integer, ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    total_points = Column(Float, nullable=False, default=0.0)
    bucket_start = Column(DateTime, nullable=False, index=True)
    computed_at = Column(DateTime, server_default=func.now(), nullable=False)

    season = relationship("Season", back_populates="snapshots", lazy="selectin")
