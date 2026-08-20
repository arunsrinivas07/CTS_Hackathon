from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class RuleEvaluation(Base):
    __tablename__ = "rule_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("policy_rules.id"), nullable=False)
    passed = Column(Boolean, nullable=False)
    score = Column(Float, nullable=True)
    details = Column(String(2000), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
