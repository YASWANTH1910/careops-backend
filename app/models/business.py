from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class BusinessPlan(str, enum.Enum):
    """Subscription plan for a business."""
    FREE = "free"
    PRO = "pro"

class Business(Base):
    """
    Business model — represents a single SaaS tenant.

    One Business Owner registers → creates one Business record.
    All Contacts, Bookings, Inventory etc. are scoped to this business.
    """
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    plan = Column(SQLEnum(BusinessPlan), nullable=False, default=BusinessPlan.FREE)
    is_onboarded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="business", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="business", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="business", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="business", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="business", cascade="all, delete-orphan")
    forms = relationship("Form", back_populates="business", cascade="all, delete-orphan")
    form_submissions = relationship("FormSubmission", back_populates="business", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="business", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Business(id={self.id}, name={self.name}, plan={self.plan})>"
