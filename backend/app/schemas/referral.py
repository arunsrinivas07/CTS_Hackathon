from datetime import datetime
from typing import Optional
from .common import SchemaBase

class ReferralCreate(SchemaBase):
    investigation_id: int
    referral_type: str
    referred_to: str
    reason: str
    external_reference: Optional[str] = None

class ReferralResponse(ReferralCreate):
    id: int
    status: str = "pending"
    created_at: datetime
