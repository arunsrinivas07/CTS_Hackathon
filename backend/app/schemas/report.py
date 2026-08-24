from datetime import datetime
from typing import Optional
from .common import SchemaBase

class ReportCreate(SchemaBase):
    investigation_id: int
    report_type: str
    title: str
    content: Optional[str] = None

class ReportUpdate(SchemaBase):
    title: Optional[str] = None
    content: Optional[str] = None
    report_type: Optional[str] = None

class ReportResponse(ReportCreate):
    id: int
    generated_by: Optional[int] = None
    created_at: datetime
