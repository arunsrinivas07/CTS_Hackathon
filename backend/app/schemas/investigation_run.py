from datetime import datetime
from typing import Optional
from .common import SchemaBase

class InvestigationRunCreate(SchemaBase):
    investigation_id: int
    run_type: str
    initiated_by: Optional[int] = None

class InvestigationRunResponse(InvestigationRunCreate):
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: Optional[str] = None
