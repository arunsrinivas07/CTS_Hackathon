from datetime import datetime
from typing import Optional, Dict, Any
from .common import SchemaBase

class AuditLogCreate(SchemaBase):
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None

class AuditLogResponse(AuditLogCreate):
    id: int
    created_at: datetime
