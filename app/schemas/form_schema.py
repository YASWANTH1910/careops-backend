from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any, Dict
from app.models.form import FormStatus


# ── Request Schemas ──────────────────────────────────────────────────────────

class FormFieldSchema(BaseModel):
    """A single field definition inside a Form template."""
    name: str           # Internal key used in FormSubmission.answers
    label: str          # Display label
    type: str           # "text" | "textarea" | "date" | "checkbox" | "select"
    required: bool = False
    options: Optional[List[str]] = None  # For "select" type


class FormCreate(BaseModel):
    """Schema for creating a new Form template."""
    title: str
    description: Optional[str] = None
    fields: List[FormFieldSchema] = []
    status: FormStatus = FormStatus.DRAFT


class FormUpdate(BaseModel):
    """Schema for updating a Form template."""
    title: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[FormFieldSchema]] = None
    status: Optional[FormStatus] = None


class FormSubmissionCreate(BaseModel):
    """Schema for a contact submitting answers to a form."""
    contact_id: Optional[int] = None
    answers: Dict[str, Any]  # {"field_name": "value", ...}
    is_complete: bool = False


class FormSubmissionUpdate(BaseModel):
    """Schema for updating (appending to) a submission."""
    answers: Optional[Dict[str, Any]] = None
    is_complete: Optional[bool] = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class FormResponse(BaseModel):
    """Schema for Form template response."""
    id: int
    business_id: int
    title: str
    description: Optional[str]
    status: FormStatus
    fields: List[Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FormSubmissionResponse(BaseModel):
    """Schema for FormSubmission response."""
    id: int
    business_id: int
    form_id: int
    contact_id: Optional[int]
    answers: Dict[str, Any]
    is_complete: bool
    submitted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
