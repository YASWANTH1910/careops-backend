from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models.user import UserRole


# ── Request Schemas ──────────────────────────────────────────────────────────

class AdminRegisterRequest(BaseModel):
    """
    Schema for Business Admin self-registration.

    Creates a new Business + Admin User atomically.
    This is the ONLY registration endpoint.
    """
    business_name: str
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Schema for admin login."""
    email: EmailStr
    password: str


# ── Response Schemas ─────────────────────────────────────────────────────────

class BusinessResponse(BaseModel):
    """Schema for business information in responses."""
    id: int
    name: str
    plan: str
    is_onboarded: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive fields like hashed_password)."""
    id: int
    business_id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime
    business: Optional[BusinessResponse] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
