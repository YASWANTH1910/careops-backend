from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class FormStatus(str, enum.Enum):
    """Whether the form is active and accepting submissions."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Form(Base):
    """
    Form template model — owner creates forms, contacts fill them in.

    Scoped to a single business via business_id (multi-tenant isolation).
    Each Form can have multiple FormSubmissions.

    Example use cases: intake forms, consent forms, feedback forms.
    """
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(FormStatus), nullable=False, default=FormStatus.DRAFT, index=True)

    # JSON schema for form fields:
    # [{"name": "dob", "label": "Date of Birth", "type": "date", "required": true}, ...]
    fields = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    business = relationship("Business", back_populates="forms")
    submissions = relationship("FormSubmission", back_populates="form", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Form(id={self.id}, title={self.title}, business_id={self.business_id}, status={self.status})>"


class FormSubmission(Base):
    """
    A contact's filled-in response to a Form.

    Stores answers as a free-form JSON dict keyed by field name.
    Scoped to business_id for fast filtering without joining to Form.
    """
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    form_id = Column(Integer, ForeignKey("forms.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True, index=True)

    # {"dob": "1990-01-15", "allergies": "none", "consent": true}
    answers = Column(JSON, nullable=False, default=dict)
    is_complete = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    business = relationship("Business", back_populates="form_submissions")
    form = relationship("Form", back_populates="submissions")
    contact = relationship("Contact", back_populates="form_submissions")

    def __repr__(self):
        return f"<FormSubmission(id={self.id}, form_id={self.form_id}, contact_id={self.contact_id}, complete={self.is_complete})>"
