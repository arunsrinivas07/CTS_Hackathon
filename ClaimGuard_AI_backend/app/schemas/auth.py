from typing import Optional
from pydantic import EmailStr, Field
from .common import SchemaBase

class LoginRequest(SchemaBase):
    email: EmailStr
    password: str = Field(min_length=8)

class TokenResponse(SchemaBase):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None

class RefreshTokenRequest(SchemaBase):
    refresh_token: str

class PasswordChangeRequest(SchemaBase):
    current_password: str
    new_password: str = Field(min_length=8)

class PasswordResetRequest(SchemaBase):
    email: EmailStr

class PasswordResetConfirm(SchemaBase):
    token: str
    new_password: str = Field(min_length=8)
