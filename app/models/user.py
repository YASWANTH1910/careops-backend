from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    """
    User role enumeration for CareOps access control.

    - ADMIN: Business admin — full access to all business data and management
    - USER:  Reserved for future public/limited access (currently unused for auth)
    """
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """
    User model for authentication and multi-tenant authorization.

    Every user belongs to exactly one Business (business_id).
    The admin registers and creates their Business.

    JWT Payload includes: sub (user_id), role, business_id
    — allowing all routes to filter data by business without extra DB calls.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(60), nullable=False)  # Bcrypt hash is always 60 chars
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.ADMIN)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    business = relationship("Business", back_populates="users")
    bookings_assigned = relationship("Booking", back_populates="assigned_user", foreign_keys="Booking.assigned_user_id")
    messages_sent = relationship("Message", back_populates="assigned_user", foreign_keys="Message.assigned_user_id")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role}, business_id={self.business_id})>"
