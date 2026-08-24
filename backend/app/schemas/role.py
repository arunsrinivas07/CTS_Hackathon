from typing import Optional
from .common import SchemaBase

class RoleCreate(SchemaBase):
    name: str
    description: Optional[str] = None

class RoleUpdate(SchemaBase):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class RoleResponse(SchemaBase):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
