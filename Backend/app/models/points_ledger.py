from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class PointsLedger(Base):
    __tablename__ = "points_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delta = Column(Float, nullable=False, default=0.0)
    reason_code = Column(String(100), nullable=False, index=True)
    source_type = Column(String(50), nullable=True, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    idempotency_key = Column(String(200), nullable=True, unique=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="points_ledger_entries", lazy="selectin")
