from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user, require_admin
from app.models.user import User
from app.schemas.contact_schema import ContactCreate, ContactUpdate, ContactResponse
from app.services.contact_service import ContactService
from app.services.automation_service import AutomationService
from app.core.logger import log_info

router = APIRouter(prefix="/contacts", tags=["Contacts"])


# Schema for public contact creation (no auth required)
class PublicContactCreate(BaseModel):
    """Schema for creating a contact from public form."""
    business_id: int
    name: str
    email: str
    phone: Optional[str] = None


@router.post("/public", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_public_contact(
    contact_data: PublicContactCreate,
    db: Session = Depends(get_db)
):
    """
    Create a contact from public form (no authentication required).
    
    Used for public booking flows where customer provides their contact info.
    """
    log_info(f"[ROUTE] Creating public contact: {contact_data.email} for business {contact_data.business_id}")
    
    try:
        service = ContactService(db)
        contact = service.find_or_create_contact(
            business_id=contact_data.business_id,
            name=contact_data.name,
            email=contact_data.email,
            phone=contact_data.phone
        )
        log_info(f"[ROUTE] Public contact created/found: {contact.id}")
        return ContactResponse.model_validate(contact)
    except HTTPException:
        raise
    except Exception as e:
        log_info(f"[ROUTE] Error creating public contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new contact.
    
    EVENT TRIGGER: Sends welcome message via automation.
    """
    service = ContactService(db)
    contact = service.create_contact(contact_data, business_id=current_user.business_id)
    
    # EXPLICIT EVENT TRIGGER
    automation = AutomationService(db)
    automation.handle_new_contact(contact)
    
    return ContactResponse.model_validate(contact)


@router.get("", response_model=List[ContactResponse])
def get_contacts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all contacts with pagination."""
    service = ContactService(db)
    contacts = service.get_contacts(business_id=current_user.business_id, skip=skip, limit=limit)
    return [ContactResponse.model_validate(c) for c in contacts]


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get contact by ID."""
    service = ContactService(db)
    contact = service.get_contact(contact_id, business_id=current_user.business_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact {contact_id} not found"
        )
    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update contact details."""
    service = ContactService(db)
    try:
        contact = service.update_contact(contact_id, contact_data, business_id=current_user.business_id)
        return ContactResponse.model_validate(contact)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only
):
    """Delete contact (admin only)."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.business_id == current_user.business_id,
    ).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact {contact_id} not found"
        )
    
    db.delete(contact)
    db.commit()
