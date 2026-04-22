from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class AchievementDefinition(Base):
    __tablename__ = "achievement_definitions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    reward = Column(String(255), nullable=True)
    criteria_type = Column(String(50), nullable=False, index=True)
    threshold_value = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_achievements = relationship(
        "UserAchievement",
        back_populates="achievement",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
