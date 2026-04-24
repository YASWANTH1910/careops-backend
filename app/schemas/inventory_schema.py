from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Request Schemas
class InventoryCreate(BaseModel):
    """Schema for creating a new inventory item."""
    item_name: str
    quantity: int = 0
    threshold: int = 10
    unit: Optional[str] = None
    notes: Optional[str] = None


class InventoryUpdate(BaseModel):
    """Schema for updating inventory details."""
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    threshold: Optional[int] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


# Response Schemas
class InventoryResponse(BaseModel):
    """Schema for inventory response."""
    id: int
    item_name: str
    quantity: int
    threshold: int
    unit: Optional[str]
    notes: Optional[str]
    is_low_stock: bool
    updated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True
