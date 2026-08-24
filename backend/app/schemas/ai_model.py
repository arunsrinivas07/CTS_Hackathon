from datetime import datetime
from typing import Optional
from .common import SchemaBase

class AIModelCreate(SchemaBase):
    name: str
    version: str
    model_type: str
    description: Optional[str] = None
    provider: Optional[str] = None

class AIModelUpdate(SchemaBase):
    description: Optional[str] = None
    is_active: Optional[bool] = None

class AIModelResponse(AIModelCreate):
    id: int
    is_active: bool
    created_at: datetime
