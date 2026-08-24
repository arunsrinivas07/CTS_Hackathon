from typing import Optional
from .common import SchemaBase

class ClaimDiagnosisCreate(SchemaBase):
    claim_id: int
    diagnosis_code: str
    diagnosis_description: Optional[str] = None
    diagnosis_type: Optional[str] = None
    sequence_number: int = 1

class ClaimDiagnosisResponse(ClaimDiagnosisCreate):
    id: int
