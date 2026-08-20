from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field
from .common import SchemaBase

class UserBase(SchemaBase):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role_id: int

class UserUpdate(SchemaBase):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    role_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
