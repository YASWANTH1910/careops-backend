"""
Contact Service — Business logic for contact management.

Multi-tenant isolation ensures all queries filter by business_id.
Includes service-level validations for data integrity.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.contact import Contact
from app.schemas.contact_schema import ContactCreate, ContactUpdate
from app.core.logger import log_info, log_warning


class ContactService:
    """Service for managing contacts with multi-tenant isolation and validations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_or_create_contact(self, business_id: int, name: str, email: str, phone: str = None) -> Contact:
        """
        Find an existing contact by email or create a new one.
        
        This is used for public booking flows where we don't require full validation.
        
        Args:
            business_id: Tenant ID
            name: Contact name
            email: Contact email (unique per business)
            phone: Contact phone (optional)
            
        Returns:
            Contact model (existing or newly created)
        """
        log_info(f"[SERVICE] Finding or creating contact: {email} for business {business_id}")
        
        # Try to find existing contact by email
        existing_contact = self.db.query(Contact).filter(
            Contact.business_id == business_id,
            Contact.email == email.strip().lower() if email else None
        ).first()
        
        if existing_contact:
            log_info(f"[SERVICE] Contact found: id={existing_contact.id}")
            return existing_contact
        
        # Create new contact
        log_info(f"[SERVICE] Creating new contact: {name} ({email}) for business {business_id}")
        
        contact = Contact(
            business_id=business_id,
            name=name.strip() if name else "Unknown",
            email=email.strip().lower() if email else None,
            phone=phone.strip() if phone else None,
            status="New",
            source="public_booking"
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Contact created: id={contact.id}")
        return contact
    
    def create_contact(self, contact_data: ContactCreate, business_id: int) -> Contact:
        """
        Create a new contact scoped to business_id.
        
        VALIDATIONS:
        - Name is required (non-empty)
        - Email is required (non-empty)
        - Email must be unique within the same business_id
        
        Args:
            contact_data: ContactCreate schema
            business_id: Tenant ID from authenticated user
            
        Returns:
            Created Contact model
            
        Raises:
            HTTPException: If validation fails
        """
        # Validation: Name required
        if not contact_data.name or not contact_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name is required and cannot be empty"
            )
        
        # Validation: Email required
        if not contact_data.email or not contact_data.email.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required and cannot be empty"
            )
        
        # Validation: Email must be unique within this business
        existing_contact = self.db.query(Contact).filter(
            Contact.business_id == business_id,
            Contact.email == contact_data.email.strip().lower()
        ).first()
        
        if existing_contact:
            log_warning(f"[SERVICE] Duplicate email attempt: {contact_data.email} for business {business_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A contact with email '{contact_data.email}' already exists in this business"
            )
        
        log_info(f"[SERVICE] Creating contact: {contact_data.name} for business {business_id}")
        
        contact = Contact(
            **contact_data.model_dump(),
            business_id=business_id
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Contact created: id={contact.id}, business={business_id}")
        return contact
    
    def get_contacts(self, business_id: int, skip: int = 0, limit: int = 100) -> list[Contact]:
        """
        Get all contacts for a business with pagination.
        
        Multi-tenant isolation: filtered by business_id.
        Pagination: enforces max limit of 100
        """
        # Enforce max limit
        limit = min(limit, 100)
        
        return self.db.query(Contact).filter(
            Contact.business_id == business_id
        ).offset(skip).limit(limit).all()
    
    def get_contact(self, contact_id: int, business_id: int) -> Contact:
        """
        Get a contact by ID, scoped to business_id.
        
        Returns None if contact doesn't exist or belongs to another tenant.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.business_id == business_id
        ).first()
    
    def update_contact(self, contact_id: int, contact_data: ContactUpdate, business_id: int) -> Contact:
        """
        Update a contact, scoped to business_id.
        
        VALIDATIONS:
        - If email is being updated, it must be unique within business_id
        
        Raises ValueError if contact not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Updating contact {contact_id} for business {business_id}")
        
        contact = self.get_contact(contact_id, business_id)
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Validation: If email is being updated, check uniqueness
        update_data = contact_data.model_dump(exclude_unset=True)
        if 'email' in update_data and update_data['email']:
            new_email = update_data['email'].strip().lower()
            
            # Check if another contact already has this email
            existing = self.db.query(Contact).filter(
                Contact.business_id == business_id,
                Contact.email == new_email,
                Contact.id != contact_id  # Exclude current contact
            ).first()
            
            if existing:
                log_warning(f"[SERVICE] Duplicate email during update: {new_email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{new_email}' is already used by another contact in this business"
                )
        
        # Update fields that are set
        for field, value in update_data.items():
            setattr(contact, field, value)
        
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Contact updated: id={contact.id}")
        return contact
    
    def delete_contact(self, contact_id: int, business_id: int) -> bool:
        """
        Delete a contact, scoped to business_id.
        
        Returns True if deleted, False if not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Deleting contact {contact_id} for business {business_id}")
        
        contact = self.get_contact(contact_id, business_id)
        if not contact:
            return False
        
        self.db.delete(contact)
        self.db.commit()
        
        log_info(f"[SERVICE] Contact deleted: id={contact_id}")
        return True
    
    def search_contacts(self, business_id: int, query: str, skip: int = 0, limit: int = 100) -> list[Contact]:
        """
        Search contacts by name, email, or phone.
        
        Multi-tenant isolation: filtered by business_id.
        Pagination: enforces max limit of 100
        """
        limit = min(limit, 100)
        
        return self.db.query(Contact).filter(
            Contact.business_id == business_id,
            (Contact.name.ilike(f"%{query}%")) |
            (Contact.email.ilike(f"%{query}%")) |
            (Contact.phone.ilike(f"%{query}%"))
        ).offset(skip).limit(limit).all()
    
    def filter_contacts_by_status(self, business_id: int, status: str, skip: int = 0, limit: int = 100) -> list[Contact]:
        """
        Get contacts filtered by status.
        
        Multi-tenant isolation: filtered by business_id.
        Pagination: enforces max limit of 100
        """
        limit = min(limit, 100)
        
        return self.db.query(Contact).filter(
            Contact.business_id == business_id,
            Contact.status == status
        ).offset(skip).limit(limit).all()
