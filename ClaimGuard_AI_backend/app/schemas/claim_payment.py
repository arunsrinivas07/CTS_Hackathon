from datetime import date
from decimal import Decimal
from typing import Optional
from .common import SchemaBase

class ClaimPaymentCreate(SchemaBase):
    claim_id: int
    payment_date: date
    paid_amount: Decimal
    adjustment_amount: Optional[Decimal] = None
    denial_amount: Optional[Decimal] = None
    payment_reference: Optional[str] = None

class ClaimPaymentResponse(ClaimPaymentCreate):
    id: int
