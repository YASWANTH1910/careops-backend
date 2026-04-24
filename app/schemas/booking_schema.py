from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.booking import BookingStatus, FormStatus


# Request Schemas
class BookingCreate(BaseModel):
    """Schema for creating a new booking."""
    contact_id: int
    assigned_user_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    service_type: Optional[str] = None
    notes: Optional[str] = None


class BookingUpdate(BaseModel):
    """Schema for updating booking details."""
    assigned_user_id: Optional[int] = None
    status: Optional[BookingStatus] = None
    form_status: Optional[FormStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    service_type: Optional[str] = None
    notes: Optional[str] = None


# Response Schemas
class BookingResponse(BaseModel):
    """Schema for booking response."""
    id: int
    contact_id: int
    assigned_user_id: Optional[int]
    status: str  # Changed from BookingStatus to str since we store as string value
    form_status: str  # Changed from FormStatus to str since we store as string value
    start_time: datetime
    end_time: datetime
    service_type: Optional[str]
    notes: Optional[str]
    created_at: datetime
    business_id: Optional[int] = None  # Added optional business_id to response
    
    class Config:
        from_attributes = True
