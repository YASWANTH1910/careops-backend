from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# Request Schemas
class ServiceCreate(BaseModel):
    """Schema for creating a new service."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(..., gt=0)
    price: Optional[float] = Field(None, ge=0.0)


class ServiceUpdate(BaseModel):
    """Schema for updating service details."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, ge=0.0)
    is_active: Optional[bool] = None


# Response Schemas
class ServiceResponse(BaseModel):
    """Schema for service response."""
    id: int
    name: str
    description: Optional[str]
    duration_minutes: int
    price: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ServicePublicResponse(BaseModel):
    """Schema for public service response (limited data for unauthenticated access)."""
    id: int
    name: str
    description: Optional[str]
    duration_minutes: int
    price: Optional[float]
    
    class Config:
        from_attributes = True
