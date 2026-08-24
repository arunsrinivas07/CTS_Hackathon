from typing import Optional
from pydantic import EmailStr, Field
from .common import SchemaBase

class LoginRequest(SchemaBase):
    email: str
    password: str = Field(min_length=1)

class TokenResponse(SchemaBase):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None

class RefreshTokenRequest(SchemaBase):
    refresh_token: str

class PasswordChangeRequest(SchemaBase):
    current_password: str
    new_password: str = Field(min_length=1)

class PasswordResetRequest(SchemaBase):
    email: str

class PasswordResetConfirm(SchemaBase):
    token: str
    new_password: str = Field(min_length=1)

