from typing import Optional
from .common import SchemaBase

class PermissionCreate(SchemaBase):
    name: str
    resource: str
    action: str
    description: Optional[str] = None

class PermissionResponse(SchemaBase):
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str] = None
