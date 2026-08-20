from datetime import datetime
from typing import Optional, Literal
from .common import SchemaBase

class RiskScoreCreate(SchemaBase):
    claim_id: int
    overall_score: float
    fraud_score: Optional[float] = None
    waste_score: Optional[float] = None
    abuse_score: Optional[float] = None
    risk_level: Literal["low","medium","high","critical"]
    explanation: Optional[str] = None

class RiskScoreUpdate(SchemaBase):
    overall_score: Optional[float] = None
    risk_level: Optional[str] = None
    explanation: Optional[str] = None

class RiskScoreResponse(RiskScoreCreate):
    id: int
    model_version: Optional[str] = None
    created_at: datetime
