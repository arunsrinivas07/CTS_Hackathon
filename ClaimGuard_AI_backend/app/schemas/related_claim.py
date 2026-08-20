from typing import Optional
from .common import SchemaBase

class RelatedClaimCreate(SchemaBase):
    claim_id: int
    related_claim_id: int
    relationship_type: str
    confidence_score: Optional[float] = None
    reason: Optional[str] = None

class RelatedClaimResponse(RelatedClaimCreate):
    id: int
