"""
Leads-specific routes.

All queries are scoped to current_user.business_id — full multi-tenant isolation.

Routes:
  POST /leads/public          — Public lead form (no auth, takes business_id as query param)
  GET  /leads                 — Admin: list leads for their business
  POST /leads                 — Admin: create lead manually
  PATCH /leads/{id}           — Admin: update lead
  POST  /leads/{id}/convert   — Admin: convert lead → booking
  DELETE /leads/{id}          — Admin only (require_admin)
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.core.logger import log_info
from app.dependencies.auth_dependency import get_current_user, require_admin
from app.models.user import User
from app.models.booking import Booking, BookingStatus, FormStatus
from app.schemas.contact_schema import ContactCreate, ContactUpdate, ContactResponse, PublicLeadCreate
from app.schemas.booking_schema import BookingCreate, BookingResponse
from app.services.lead_service import LeadService
from app.services.booking_service import BookingService
import app.services.email_service as email_service

router = APIRouter(prefix="/leads", tags=["Leads"])


# ── Public Lead Form ──────────────────────────────────────────────────────────

@router.post("/public", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def submit_public_lead(
    lead_data: PublicLeadCreate,
    background_tasks: BackgroundTasks,
    business_id: int = Query(..., description="The business this lead should be assigned to"),
    db: Session = Depends(get_db),
):
    """
    Public endpoint — no authentication required.

    Used by the public-facing lead capture form (/contact page).
    business_id must be passed as a query param so the lead is routed
    to the correct tenant (e.g. ?business_id=7).
    """
    log_info(f"[Leads] Public lead form submission: {lead_data.email} → business {business_id}")

    service = LeadService(db)
    contact = service.create_public_lead(lead_data, business_id=business_id)

    if settings.ADMIN_EMAIL:
        background_tasks.add_task(
            email_service.send_admin_new_lead_alert,
            admin_email=settings.ADMIN_EMAIL,
            lead_name=contact.name,
            lead_email=contact.email or "N/A",
            service_interest=contact.service_interest or "",
        )

    log_info(f"[Leads] Public lead created: contact_id={contact.id}")
    return ContactResponse.model_validate(contact)


# ── Authenticated Leads ───────────────────────────────────────────────────────

@router.get("", response_model=List[ContactResponse])
def get_leads(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all leads for the current user's business.

    Automatically scoped to current_user.business_id — no cross-tenant leakage.
    """
    service = LeadService(db)
    contacts = service.get_leads(business_id=current_user.business_id, skip=skip, limit=limit, status=status_filter)
    return [ContactResponse.model_validate(c) for c in contacts]


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new lead (manual entry from dashboard). Scoped to current business."""
    log_info(
        f"[Leads] Creating lead: name='{lead_data.name}' "
        f"for business_id={current_user.business_id}, user_id={current_user.id}, role={current_user.role}"
    )
    try:
        service = LeadService(db)
        contact = service.create_lead(lead_data, business_id=current_user.business_id)
        log_info(f"[Leads] Lead created successfully: contact_id={contact.id}")
        return ContactResponse.model_validate(contact)
    except Exception as exc:
        log_info(f"[Leads] ERROR creating lead: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create lead: {str(exc)}"
        )


@router.patch("/{lead_id}", response_model=ContactResponse)
def update_lead(
    lead_id: int,
    lead_data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update lead — must belong to current user's business."""
    service = LeadService(db)
    try:
        contact = service.update_lead(lead_id, lead_data, business_id=current_user.business_id)
        return ContactResponse.model_validate(contact)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found"
        )


@router.post("/{lead_id}/convert", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def convert_lead_to_booking(
    lead_id: int,
    booking_data: BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Convert a lead (Contact) to a Booking.

    - Lead must belong to current business.
    - Booking inherits the same business_id.
    """
    lead_service = LeadService(db)
    contact = lead_service.get_lead(lead_id, business_id=current_user.business_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lead {lead_id} not found")

    # Create booking using BookingService
    booking_service = BookingService(db)
    booking_data.business_id = current_user.business_id
    booking_data.contact_id = contact.id
    booking = booking_service.create_booking(booking_data)
    
    # Update lead status to "Booked"
    contact.status = "Booked"
    db.commit()

    if contact.email:
        background_tasks.add_task(
            email_service.send_booking_confirmation,
            contact_name=contact.name,
            contact_email=contact.email,
            start_time=booking.start_time,
            service_type=booking.service_type or "",
        )

    if settings.ADMIN_EMAIL:
        background_tasks.add_task(
            email_service.send_admin_new_booking_alert,
            admin_email=settings.ADMIN_EMAIL,
            contact_name=contact.name,
            start_time=booking.start_time,
            service_type=booking.service_type or "",
        )

    log_info(f"[Leads] Lead {lead_id} converted to booking {booking.id}")
    return BookingResponse.model_validate(booking)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),   # ← Admin only
):
    """
    Delete a lead — Admin only.

    Uses require_admin to protect this destructive action.
    """
    service = LeadService(db)
    deleted = service.delete_lead(lead_id, business_id=admin.business_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lead {lead_id} not found")
