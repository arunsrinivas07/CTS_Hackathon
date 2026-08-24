from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class MLOutputBase(BaseModel):
    transaction_type: str
    transaction_id: Optional[str] = None
    bene_id: Optional[str] = None
    provider_id: Optional[str] = None
    claim_score: Optional[float] = None
    effective_claim_score: Optional[float] = None
    claim_score_label: Optional[str] = None
    provider_score: Optional[float] = None
    provider_score_label: Optional[str] = None
    final_risk_score: float
    final_risk_tier: str
    model_weights: Optional[Dict[str, Any]] = None
    leie_override: bool = False
    leie_details: Optional[str] = None
    claim_evidence: Optional[Dict[str, Any]] = None
    provider_evidence: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    disclaimer: Optional[str] = None
    scored_at: Optional[datetime] = None

class MLOutputCreate(MLOutputBase):
    pass

class MLOutputUpdate(BaseModel):
    transaction_type: Optional[str] = None
    final_risk_score: Optional[float] = None
    final_risk_tier: Optional[str] = None
    explanation: Optional[str] = None

class MLOutputResponse(MLOutputBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
