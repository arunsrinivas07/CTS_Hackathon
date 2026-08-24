from datetime import datetime
from typing import Optional, Literal
from .common import SchemaBase

class DecisionCreate(SchemaBase):
    investigation_id: int
    decision_type: Optional[str] = "fwa_decision"
    decision: Literal["no_issue","potential_fraud","potential_waste","potential_abuse","escalate"]
    rationale: str
    confidence: Optional[float] = None

class DecisionResponse(DecisionCreate):
    id: int
    decided_by: Optional[int] = None
    created_at: datetime
