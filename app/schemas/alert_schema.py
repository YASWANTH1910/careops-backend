from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.alert import AlertType, AlertSeverity


# Request Schemas
class AlertCreate(BaseModel):
    """Schema for creating a new alert."""
    business_id: int
    type: AlertType
    severity: AlertSeverity
    message: str
    details: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None


class AlertDismiss(BaseModel):
    """Schema for dismissing an alert."""
    is_dismissed: bool = True


# Response Schemas
class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: int
    type: AlertType
    severity: AlertSeverity
    message: str
    details: Optional[str]
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    reference_type: Optional[str]
    reference_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True
