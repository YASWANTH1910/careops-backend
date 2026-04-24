from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class MessageChannel(str, enum.Enum):
    """Message channel enumeration."""
    EMAIL = "email"
    SMS = "sms"
    SYSTEM = "system"


class MessageDirection(str, enum.Enum):
    """Message direction enumeration."""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class MessageStatus(str, enum.Enum):
    """Message delivery status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class Message(Base):
    """
    Message model for communication tracking.

    Scoped to a single business via business_id (multi-tenant isolation).
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    channel = Column(SQLEnum(MessageChannel), nullable=False, index=True)
    direction = Column(SQLEnum(MessageDirection), nullable=False, index=True)
    status = Column(SQLEnum(MessageStatus), nullable=False, default=MessageStatus.PENDING, index=True)
    content = Column(String(5000), nullable=False)
    subject = Column(String(500), nullable=True)  # For emails
    error_message = Column(String(1000), nullable=True)  # If delivery failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="messages")
    contact = relationship("Contact", back_populates="messages")
    assigned_user = relationship("User", back_populates="messages_sent", foreign_keys=[assigned_user_id])

    def __repr__(self):
        return f"<Message(id={self.id}, contact_id={self.contact_id}, channel={self.channel}, business_id={self.business_id})>"
