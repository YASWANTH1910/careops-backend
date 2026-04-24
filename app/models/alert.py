from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class AlertType(str, enum.Enum):
    """Alert type enumeration."""
    INVENTORY = "inventory"
    INTEGRATION = "integration"
    BOOKING = "booking"
    SYSTEM = "system"


class AlertSeverity(str, enum.Enum):
    """Alert severity enumeration."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(Base):
    """
    Alert model for system notifications.

    Scoped to a single business via business_id (multi-tenant isolation).
    Alerts are never deleted, only dismissed — maintains a complete audit trail.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(AlertType), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.INFO, index=True)
    message = Column(String(1000), nullable=False)
    details = Column(String(2000), nullable=True)
    is_dismissed = Column(Boolean, default=False, nullable=False, index=True)
    dismissed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Reference fields for context
    reference_type = Column(String(50), nullable=True)  # e.g., "inventory", "booking"
    reference_id = Column(Integer, nullable=True)  # ID of related entity

    # Relationships
    business = relationship("Business", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.type}, severity={self.severity}, business_id={self.business_id})>"
