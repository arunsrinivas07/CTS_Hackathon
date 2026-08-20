from typing import Optional
from .common import SchemaBase

class ProviderNetworkCreate(SchemaBase):
    provider_id: int
    network_name: str
    network_id: Optional[str] = None
    effective_date: Optional[str] = None
    termination_date: Optional[str] = None

class ProviderNetworkResponse(ProviderNetworkCreate):
    id: int
    is_active: bool = True
