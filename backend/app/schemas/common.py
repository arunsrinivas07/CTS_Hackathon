from datetime import datetime
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class MessageResponse(SchemaBase):
    message: str

class PaginatedResponse(SchemaBase, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20

class TimestampSchema(SchemaBase):
    created_at: datetime
    updated_at: Optional[datetime] = None
