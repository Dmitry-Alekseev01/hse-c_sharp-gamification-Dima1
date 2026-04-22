from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement_user_achievement"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievement_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_event = Column(String(120), nullable=True)
    earned_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="earned_achievements", lazy="selectin")
    achievement = relationship("AchievementDefinition", back_populates="user_achievements", lazy="selectin")
