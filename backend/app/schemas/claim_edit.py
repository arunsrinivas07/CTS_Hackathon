from datetime import datetime
from typing import Optional
from .common import SchemaBase

class ClaimEditCreate(SchemaBase):
    claim_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    edited_by: Optional[int] = None

class ClaimEditResponse(ClaimEditCreate):
    id: int
    edited_at: datetime
