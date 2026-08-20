from typing import Optional, Literal
from .common import SchemaBase

class FindingCreate(SchemaBase):
    investigation_id: int
    finding_type: str
    title: str
    description: str
    severity: Literal["low","medium","high","critical"]
    confidence: Optional[float] = None
    source: Optional[str] = None

class FindingUpdate(SchemaBase):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None

class FindingResponse(FindingCreate):
    id: int
