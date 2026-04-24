from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Inventory(Base):
    """
    Inventory model for tracking stock levels.

    Scoped to a single business via business_id (multi-tenant isolation).
    item_name is unique per-business (not globally), so no global unique constraint.
    """
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False, index=True)  # unique per-business, not globally
    quantity = Column(Integer, nullable=False, default=0)
    threshold = Column(Integer, nullable=False, default=10)
    unit = Column(String(50), nullable=True)
    notes = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    business = relationship("Business", back_populates="inventory")

    def __repr__(self):
        return f"<Inventory(id={self.id}, item_name={self.item_name}, business_id={self.business_id}, quantity={self.quantity})>"

    @property
    def is_low_stock(self) -> bool:
        """Check if inventory is below threshold."""
        return self.quantity < self.threshold
