from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    decision_type = Column(String(50), default="fwa_decision", nullable=False)
    decision = Column(String(50), nullable=False)
    rationale = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
