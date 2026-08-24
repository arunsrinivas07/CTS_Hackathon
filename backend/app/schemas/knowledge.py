from datetime import datetime
from typing import Optional
from .common import SchemaBase

class KnowledgeDocumentCreate(SchemaBase):
    title: str
    source: str
    source_type: str
    content: Optional[str] = None
    metadata: Optional[dict] = None

class KnowledgeDocumentUpdate(SchemaBase):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[dict] = None
    is_active: Optional[bool] = None

class KnowledgeDocumentResponse(KnowledgeDocumentCreate):
    id: int
    is_active: bool
    created_at: datetime
