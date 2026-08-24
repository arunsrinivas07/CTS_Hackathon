from decimal import Decimal
from typing import Optional
from .common import SchemaBase

class ClaimLineItemCreate(SchemaBase):
    claim_id: Optional[int] = None
    line_number: int
    procedure_code: Optional[str] = None
    revenue_code: Optional[str] = None
    units: Decimal = Decimal("1")
    billed_amount: Decimal
    paid_amount: Optional[Decimal] = None
    modifier: Optional[str] = None

class ClaimLineItemResponse(ClaimLineItemCreate):
    id: int
