from datetime import datetime
from typing import Optional
from .common import SchemaBase

class RuleEvaluationCreate(SchemaBase):
    claim_id: int
    rule_id: int
    triggered: bool
    score: Optional[float] = None
    explanation: Optional[str] = None
    evaluation_data: Optional[dict] = None

class RuleEvaluationResponse(RuleEvaluationCreate):
    id: int
    evaluated_at: datetime
