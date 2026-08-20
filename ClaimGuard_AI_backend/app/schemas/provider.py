from typing import Optional
from .common import SchemaBase

class ProviderCreate(SchemaBase):
    npi: str
    name: str
    provider_type: Optional[str] = None
    specialty: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None

class ProviderUpdate(SchemaBase):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    specialty: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class ProviderResponse(ProviderCreate):
    id: int
    is_active: bool = True
