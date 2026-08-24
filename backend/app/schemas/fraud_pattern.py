from typing import Optional
from .common import SchemaBase

class FraudPatternCreate(SchemaBase):
    name: str
    category: str
    description: str
    indicators: list[str] = []
    severity: Optional[str] = None

class FraudPatternResponse(FraudPatternCreate):
    id: int
    is_active: bool = True
