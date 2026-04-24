from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# Request Schemas
class ContactCreate(BaseModel):
    """Schema for creating a new contact."""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = "New"
    service_interest: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[str] = "manual"


class ContactUpdate(BaseModel):
    """Schema for updating contact details."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    service_interest: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None


# Response Schemas
class ContactResponse(BaseModel):
    """Schema for contact response."""
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    status: Optional[str] = "New"
    service_interest: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[str] = "manual"
    created_at: datetime

    class Config:
        from_attributes = True


# Public lead form submission (no auth required)
class PublicLeadCreate(BaseModel):
    """Schema for public lead form submissions."""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    service_interest: Optional[str] = None
    notes: Optional[str] = None
