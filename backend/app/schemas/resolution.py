from datetime import datetime
from typing import Optional, Literal
from .common import SchemaBase

class ResolutionCreate(SchemaBase):
    investigation_id: int
    resolution_type: Literal["closed_no_issue","fraud_confirmed","waste_confirmed","abuse_confirmed","referred"]
    summary: str
    recovery_amount: Optional[float] = None
    notes: Optional[str] = None

class ResolutionResponse(ResolutionCreate):
    id: int
    resolved_by: int
    resolved_at: datetime
