from datetime import datetime
from typing import Optional
from .common import SchemaBase

class ClaimAttachmentCreate(SchemaBase):
    claim_id: int
    file_name: str
    content_type: str
    storage_key: str
    description: Optional[str] = None

class ClaimAttachmentResponse(ClaimAttachmentCreate):
    id: int
    uploaded_by: Optional[int] = None
    created_at: datetime
