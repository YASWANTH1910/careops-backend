from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.message import MessageChannel, MessageDirection, MessageStatus


# Request Schemas
class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    contact_id: int
    assigned_user_id: Optional[int] = None
    channel: MessageChannel
    direction: MessageDirection
    content: str
    subject: Optional[str] = None


# Response Schemas
class MessageResponse(BaseModel):
    """Schema for message response."""
    id: int
    contact_id: int
    assigned_user_id: Optional[int]
    channel: MessageChannel
    direction: MessageDirection
    status: MessageStatus
    content: str
    subject: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
    
    class Config:
        from_attributes = True
