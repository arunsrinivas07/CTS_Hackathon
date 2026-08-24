from datetime import datetime
from typing import Optional
from .common import SchemaBase

class DocumentationRequestCreate(SchemaBase):
    investigation_id: int
    requested_from: Optional[str] = None
    document_type: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class DocumentationRequestUpdate(SchemaBase):
    requested_from: Optional[str] = None
    document_type: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    is_fulfilled: Optional[bool] = None

class DocumentationRequestResponse(DocumentationRequestCreate):
    id: int
    is_fulfilled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

