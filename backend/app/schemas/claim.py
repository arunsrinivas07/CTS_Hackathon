import json
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal, Any, List
from pydantic import field_validator
from .common import SchemaBase
from .risk import RiskScoreResponse


class ProviderSummary(SchemaBase):
    """Embedded provider summary returned inside ClaimResponse."""
    id: int
    npi: str
    name: str
    provider_type: Optional[str] = None
    specialty: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True


class PatientSummary(SchemaBase):
    """Embedded patient summary returned inside ClaimResponse."""
    id: int
    patient_external_id: str
    first_name: str
    last_name: Optional[str] = None  # Allow NULL for unknown last names
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    member_id: Optional[str] = None


class ClaimBase(SchemaBase):
    claim_number: str
    patient_id: int
    provider_id: int
    claim_type: Optional[str] = None
    service_date: date
    submission_date: Optional[date] = None
    total_billed_amount: Decimal
    total_paid_amount: Optional[Decimal] = None
    status: Literal["submitted","processing","paid","denied","flagged","closed"] = "submitted"
    assigned_to: Optional[int] = None
    diag_count: Optional[int] = 1
    proc_count: Optional[int] = 1
    line_count: Optional[int] = 1
    state: Optional[str] = None
    raw_extracted_features: Optional[Any] = None

    @field_validator("raw_extracted_features", mode="before")
    @classmethod
    def parse_extracted_features(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {"raw_text": v}
        return v

class ClaimCreate(ClaimBase):
    pass

class ClaimUpdate(SchemaBase):
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    total_paid_amount: Optional[Decimal] = None

class ClaimResponse(ClaimBase):
    id: int
    assigned_investigator: Optional[Any] = None
    risk_scores: Optional[List[RiskScoreResponse]] = None
    provider: Optional[ProviderSummary] = None
    patient: Optional[PatientSummary] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
