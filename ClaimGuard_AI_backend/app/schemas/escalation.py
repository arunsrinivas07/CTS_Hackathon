from datetime import datetime
from typing import Optional
from .common import SchemaBase

class EscalationCreate(SchemaBase):
    investigation_id: int
    from_user_id: Optional[int] = None
    to_user_id: Optional[int] = None
    reason: str
    priority: str = "high"

class EscalationResponse(EscalationCreate):
    id: int
    status: str = "open"
    created_at: datetime
