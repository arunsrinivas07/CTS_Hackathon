from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal
from .common import SchemaBase

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

class ClaimCreate(ClaimBase):
    pass

class ClaimUpdate(SchemaBase):
    status: Optional[str] = None
    total_paid_amount: Optional[Decimal] = None

class ClaimResponse(ClaimBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
