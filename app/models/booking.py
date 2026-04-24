from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class BookingStatus(str, enum.Enum):
    """Booking status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class FormStatus(str, enum.Enum):
    """Form completion status enumeration."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class Booking(Base):
    """
    Booking model for appointments/reservations.

    Scoped to a single business via business_id (multi-tenant isolation).
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(BookingStatus), nullable=False, default=BookingStatus.PENDING, index=True)
    form_status = Column(SQLEnum(FormStatus), nullable=False, default=FormStatus.PENDING)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    service_type = Column(String(255), nullable=True)
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    business = relationship("Business", back_populates="bookings")
    contact = relationship("Contact", back_populates="bookings")
    assigned_user = relationship("User", back_populates="bookings_assigned", foreign_keys=[assigned_user_id])

    def __repr__(self):
        return f"<Booking(id={self.id}, contact_id={self.contact_id}, business_id={self.business_id}, status={self.status})>"
