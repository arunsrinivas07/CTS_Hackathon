from datetime import datetime
from typing import Optional
from .common import SchemaBase

class AnomalyCreate(SchemaBase):
    claim_id: int
    anomaly_type: str
    description: str
    score: float
    evidence: Optional[dict] = None

class AnomalyResponse(AnomalyCreate):
    id: int
    detected_at: datetime
