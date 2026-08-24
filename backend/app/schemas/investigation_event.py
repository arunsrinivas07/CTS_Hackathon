from datetime import datetime
from typing import Optional
from .common import SchemaBase

class InvestigationEventCreate(SchemaBase):
    investigation_id: int
    event_type: str
    description: str
    actor_id: Optional[int] = None
    event_data: Optional[dict] = None

class InvestigationEventResponse(InvestigationEventCreate):
    id: int
    created_at: datetime
