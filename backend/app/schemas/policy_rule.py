from typing import Optional
from .common import SchemaBase

class PolicyRuleCreate(SchemaBase):
    rule_code: str
    name: str
    description: str
    category: str
    threshold: Optional[float] = None
    configuration: Optional[dict] = None

class PolicyRuleUpdate(SchemaBase):
    name: Optional[str] = None
    description: Optional[str] = None
    threshold: Optional[float] = None
    configuration: Optional[dict] = None
    is_active: Optional[bool] = None

class PolicyRuleResponse(PolicyRuleCreate):
    id: int
    is_active: bool = True
