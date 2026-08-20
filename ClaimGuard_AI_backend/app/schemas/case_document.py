from datetime import datetime
from typing import Optional
from .common import SchemaBase

class CaseDocumentCreate(SchemaBase):
    investigation_id: int
    file_name: str
    content_type: str
    file_size: Optional[int] = None
    storage_key: str
    description: Optional[str] = None

class CaseDocumentResponse(CaseDocumentCreate):
    id: int
    uploaded_by: int
    created_at: datetime
