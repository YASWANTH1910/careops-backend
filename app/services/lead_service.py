"""
Lead Service — Business logic for lead management.

Leads are Contacts with status="New" or source="lead_form".
Multi-tenant isolation ensures all queries filter by business_id.
"""
from sqlalchemy.orm import Session
from typing import List
from app.models.contact import Contact
from app.schemas.contact_schema import PublicLeadCreate, ContactCreate
from app.core.logger import log_info


class LeadService:
    """Service for managing leads (new contacts) with multi-tenant isolation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_public_lead(self, lead_data: PublicLeadCreate, business_id: int) -> Contact:
        """
        Create a new lead from public lead form.
        
        Public endpoint sets:
        - status="New"
        - source="lead_form"
        
        Args:
            lead_data: PublicLeadCreate schema
            business_id: Tenant ID (from query param validation)
            
        Returns:
            Created Contact model
        """
        log_info(f"[SERVICE] Creating public lead for business {business_id}: {lead_data.email}")
        
        contact = Contact(
            business_id=business_id,
            name=lead_data.name,
            email=lead_data.email,
            phone=lead_data.phone,
            service_interest=lead_data.service_interest,
            notes=lead_data.notes,
            status="New",
            source="lead_form",
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Public lead created: contact_id={contact.id}")
        return contact
    
    def create_lead(self, lead_data: ContactCreate, business_id: int) -> Contact:
        """
        Create a new lead from authenticated admin.
        
        Admin-only: manual lead creation.
        
        Args:
            lead_data: ContactCreate schema
            business_id: Tenant ID from authenticated user
            
        Returns:
            Created Contact model
        """
        log_info(f"[SERVICE] Admin creating lead for business {business_id}: {lead_data.name}")
        
        contact = Contact(
            **lead_data.model_dump(),
            business_id=business_id,
            status="New",
            source="manual"
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Lead created: contact_id={contact.id}")
        return contact
    
    def get_leads(self, business_id: int, skip: int = 0, limit: int = 100, status: str = None) -> List[Contact]:
        """
        Get all leads for a business with optional status filter.
        
        Multi-tenant isolation: filtered by business_id.
        """
        query = self.db.query(Contact).filter(
            Contact.business_id == business_id
        )
        
        if status:
            query = query.filter(Contact.status == status)
        
        return query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_lead(self, lead_id: int, business_id: int) -> Contact:
        """
        Get a lead by ID, scoped to business_id.
        
        Returns None if lead doesn't exist or belongs to another tenant.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Contact).filter(
            Contact.id == lead_id,
            Contact.business_id == business_id
        ).first()
    
    def update_lead(self, lead_id: int, lead_data: ContactCreate, business_id: int) -> Contact:
        """
        Update a lead, scoped to business_id.
        
        Raises ValueError if lead not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Updating lead {lead_id} for business {business_id}")
        
        contact = self.get_lead(lead_id, business_id)
        if not contact:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Update fields
        update_data = lead_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contact, field, value)
        
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Lead updated: lead_id={contact.id}")
        return contact
    
    def delete_lead(self, lead_id: int, business_id: int) -> bool:
        """
        Delete a lead, scoped to business_id.
        
        Returns True if deleted, False if not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Deleting lead {lead_id} for business {business_id}")
        
        contact = self.get_lead(lead_id, business_id)
        if not contact:
            return False
        
        self.db.delete(contact)
        self.db.commit()
        
        log_info(f"[SERVICE] Lead deleted: lead_id={lead_id}")
        return True
    
    def convert_lead_to_booking(self, lead_id: int, business_id: int) -> Contact:
        """
        Convert lead status from "New" to another status (e.g., "Qualified").
        
        Raises ValueError if lead not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Converting lead {lead_id} for business {business_id}")
        
        contact = self.get_lead(lead_id, business_id)
        if not contact:
            raise ValueError(f"Lead {lead_id} not found")
        
        contact.status = "Qualified"
        self.db.commit()
        self.db.refresh(contact)
        
        log_info(f"[SERVICE] Lead converted: lead_id={contact.id}")
        return contact
    
    def get_new_leads_count(self, business_id: int) -> int:
        """
        Get count of new leads for a business.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Contact).filter(
            Contact.business_id == business_id,
            Contact.status == "New"
        ).count()
