from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    fraud_score = Column(Float, nullable=True)
    waste_score = Column(Float, nullable=True)
    abuse_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=False)
    explanation = Column(String(2000), nullable=True)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
