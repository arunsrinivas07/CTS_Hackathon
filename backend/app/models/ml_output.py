from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, func
from app.database import Base

class MLOutput(Base):
    __tablename__ = "ml_outputs"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(50), nullable=False)
    transaction_id = Column(String(100))
    bene_id = Column(String(100))
    provider_id = Column(String(100))
    claim_score = Column(Float)
    effective_claim_score = Column(Float)
    claim_score_label = Column(String(255))
    provider_score = Column(Float)
    provider_score_label = Column(String(255))
    final_risk_score = Column(Float, nullable=False)
    final_risk_tier = Column(String(50), nullable=False)
    model_weights = Column(JSON)
    leie_override = Column(Boolean, nullable=False, default=False)
    leie_details = Column(Text)
    claim_evidence = Column(JSON)
    provider_evidence = Column(JSON)
    explanation = Column(Text)
    disclaimer = Column(Text)
    scored_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
