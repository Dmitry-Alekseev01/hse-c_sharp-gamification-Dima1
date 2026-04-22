from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class AIGamificationJob(Base):
    __tablename__ = "ai_gamification_jobs"

    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(30), nullable=False, default="pending", index=True)
    source_type = Column(String(30), nullable=False, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    raw_text = Column(Text, nullable=True)
    source_snapshot = Column(Text, nullable=True)

    target_level = Column(String(30), nullable=True)
    language = Column(String(16), nullable=False, default="ru")
    style = Column(String(30), nullable=True)
    tone = Column(String(30), nullable=True)
    constraints_json = Column(JSON, nullable=True)

    draft_json = Column(JSON, nullable=True)
    error_text = Column(Text, nullable=True)
    model = Column(String(120), nullable=True)
    provider = Column(String(120), nullable=True)
    usage_json = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    applied_target_type = Column(String(30), nullable=True)
    applied_target_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship("User", lazy="selectin")

