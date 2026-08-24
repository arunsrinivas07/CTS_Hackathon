from datetime import datetime
from typing import Optional
from .common import SchemaBase

class EvidenceCreate(SchemaBase):
    investigation_id: int
    evidence_type: str
    title: str
    description: Optional[str] = None
    source_reference: Optional[str] = None
    file_path: Optional[str] = None
    hash_value: Optional[str] = None

class EvidenceResponse(EvidenceCreate):
    id: int
    collected_by: Optional[int] = None
    collected_at: datetime
