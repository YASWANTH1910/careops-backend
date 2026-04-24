from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Contact(Base):
    """
    Contact model for customers/leads.

    Scoped to a single business via business_id (multi-tenant isolation).
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)

    # Lead pipeline fields
    status = Column(String(50), nullable=True, default="New", index=True)  # New, Contacted, Booked, Lost
    service_interest = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)   # comma-separated tags
    source = Column(String(100), nullable=True, default="manual")  # manual, lead_form, import

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    business = relationship("Business", back_populates="contacts")
    bookings = relationship("Booking", back_populates="contact", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    form_submissions = relationship("FormSubmission", back_populates="contact", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Contact(id={self.id}, name={self.name}, business_id={self.business_id}, status={self.status})>"
