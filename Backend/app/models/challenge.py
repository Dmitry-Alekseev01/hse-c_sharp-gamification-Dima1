from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Challenge(Base):
    __tablename__ = "challenges"
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('daily', 'weekly')",
            name="ck_challenges_period_type_valid",
        ),
        CheckConstraint(
            "event_type IN ('answer_submitted', 'attempt_completed', 'streak_day')",
            name="ck_challenges_event_type_valid",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    period_type = Column(String(20), nullable=False, index=True)  # daily | weekly
    event_type = Column(String(50), nullable=False, index=True)  # answer_submitted | attempt_completed | streak_day
    target_value = Column(Integer, nullable=False)
    reward_points = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    progress_items = relationship(
        "UserChallengeProgress",
        back_populates="challenge",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    claims = relationship(
        "UserChallengeClaim",
        back_populates="challenge",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", "period_key", name="uq_user_challenge_progress_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    period_key = Column(String(32), nullable=False, index=True)
    progress_value = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    challenge = relationship("Challenge", back_populates="progress_items", lazy="selectin")
    user = relationship("User", back_populates="challenge_progress_entries", lazy="selectin")


class UserChallengeClaim(Base):
    __tablename__ = "user_challenge_claims"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", "period_key", name="uq_user_challenge_claim_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    period_key = Column(String(32), nullable=False, index=True)
    reward_points = Column(Float, nullable=False, default=0.0)
    ledger_entry_id = Column(Integer, ForeignKey("points_ledger.id", ondelete="SET NULL"), nullable=True, index=True)
    claimed_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    challenge = relationship("Challenge", back_populates="claims", lazy="selectin")
    user = relationship("User", back_populates="challenge_claims", lazy="selectin")
