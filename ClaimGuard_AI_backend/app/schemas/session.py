from datetime import datetime
from typing import Optional
from .common import SchemaBase

class SessionCreate(SchemaBase):
    user_id: int
    refresh_token: str
    expires_at: datetime

class SessionResponse(SchemaBase):
    id: int
    user_id: int
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime
