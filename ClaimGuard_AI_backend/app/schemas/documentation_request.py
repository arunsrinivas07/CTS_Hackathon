from datetime import datetime
from typing import Optional, Literal
from .common import SchemaBase

class DocumentationRequestCreate(SchemaBase):
    investigation_id: int
    provider_id: int
    request_type: str
    description: str
    due_at: Optional[datetime] = None

class DocumentationRequestUpdate(SchemaBase):
    status: Optional[str] = None
    response_text: Optional[str] = None
    due_at: Optional[datetime] = None

class DocumentationRequestResponse(DocumentationRequestCreate):
    id: int
    status: Literal["requested","sent","received","overdue","closed"]
    response_text: Optional[str] = None
