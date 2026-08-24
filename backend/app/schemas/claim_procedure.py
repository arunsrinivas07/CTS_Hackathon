from datetime import date
from typing import Optional
from .common import SchemaBase

class ClaimProcedureCreate(SchemaBase):
    claim_id: int
    procedure_code: str
    procedure_description: Optional[str] = None
    service_date: Optional[date] = None
    units: int = 1
    modifier_1: Optional[str] = None
    modifier_2: Optional[str] = None

class ClaimProcedureResponse(ClaimProcedureCreate):
    id: int
