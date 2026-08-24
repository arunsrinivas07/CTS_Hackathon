from datetime import datetime
from typing import Optional
from .common import SchemaBase

class ClaimStatusHistoryCreate(SchemaBase):
    claim_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[int] = None
    reason: Optional[str] = None

class ClaimStatusHistoryResponse(ClaimStatusHistoryCreate):
    id: int
    changed_at: datetime
