from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Service(Base):
    """
    Service model for business services/offerings.
    
    Represents a type of service (e.g., haircut, consultation, cleaning)
    that customers can book.
    
    Scoped to a single business via business_id (multi-tenant isolation).
    """
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Service details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Float, nullable=True, default=0.0)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    business = relationship("Business", back_populates="services")

    def __repr__(self):
        return f"<Service(id={self.id}, name={self.name}, business_id={self.business_id}, duration_minutes={self.duration_minutes})>"
