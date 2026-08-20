from datetime import datetime
from typing import Optional, Literal
from .common import SchemaBase

class InvestigationCreate(SchemaBase):
    claim_id: int
    assigned_to: Optional[int] = None
    priority: Literal["low","medium","high","critical"] = "medium"
    reason: Optional[str] = None

class InvestigationUpdate(SchemaBase):
    assigned_to: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class InvestigationResponse(InvestigationCreate):
    id: int
    status: Literal["open","in_review","escalated","resolved","closed"]
    created_at: datetime
    updated_at: Optional[datetime] = None
