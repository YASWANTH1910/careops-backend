from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.booking import Booking, BookingStatus, FormStatus
from app.models.contact import Contact
from app.schemas.booking_schema import BookingCreate, BookingUpdate
from app.services.automation_service import AutomationService
from app.core.logger import log_info, log_warning, log_error


class BookingService:
    """
    Booking service with validation and multi-tenant isolation.
    
    All automations are explicitly triggered from this service layer.
    All queries are scoped to business_id for multi-tenant security.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.automation = AutomationService(db)
    
    def create_booking(self, booking_data: BookingCreate, business_id: int) -> Booking:
        """
        Create a new booking with validations.
        
        VALIDATIONS:
        - Booking start_time cannot be too far in the past (allow 5 min buffer for clock skew)
        - Contact must belong to the same business_id
        
        EVENT TRIGGER: handle_booking_created
        
        CRITICAL: Automation errors NEVER rollback booking creation.
        """
        log_info(f"[SERVICE] Creating booking for contact {booking_data.contact_id}, business_id={business_id}")
        
        # Validation: Booking date cannot be more than 5 minutes in the past (clock skew tolerance)
        # Use timezone-aware datetime for comparison with ISO timestamps
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        five_min_ago = now - timedelta(minutes=5)
        
        log_info(f"[SERVICE] Time validation: now={now}, booking_start={booking_data.start_time}, five_min_ago={five_min_ago}")
        
        if booking_data.start_time < five_min_ago:
            log_warning(f"[SERVICE] Past booking date rejected: {booking_data.start_time} is more than 5 min before {now}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Booking date cannot be in the past (requested: {booking_data.start_time}, current: {now})"
            )
        
        # Validation: Contact must belong to the same business
        log_info(f"[SERVICE] Looking up contact: contact_id={booking_data.contact_id}, business_id={business_id}")
        contact = self.db.query(Contact).filter(
            Contact.id == booking_data.contact_id,
            Contact.business_id == business_id
        ).first()
        
        if not contact:
            log_warning(f"[SERVICE] Contact {booking_data.contact_id} not found or not owned by business {business_id}")
            # Check if contact exists at all
            any_contact = self.db.query(Contact).filter(Contact.id == booking_data.contact_id).first()
            if not any_contact:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Contact {booking_data.contact_id} does not exist"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Contact {booking_data.contact_id} does not belong to business {business_id}"
                )
        
        log_info(f"[SERVICE] Validation passed - contact found: {contact.name}, email={contact.email}")
        
        # Create booking
        booking = Booking(
            **booking_data.model_dump(),
            business_id=business_id,
            status=BookingStatus.PENDING.value,  # Use .value to get "pending" string
            form_status=FormStatus.PENDING.value  # Use .value to get "pending" string
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        
        log_info(f"[SERVICE] Booking committed successfully with id={booking.id}, business_id={booking.business_id}, contact_id={booking.contact_id}")
        
        # EXPLICIT EVENT TRIGGER - wrapped in try/except to prevent rollback
        try:
            log_info(f"[SERVICE] Triggering automation event: handle_booking_created")
            self.automation.handle_booking_created(booking)
            log_info(f"[SERVICE] Automation completed successfully")
        except Exception as e:
            log_warning(f"[SERVICE] Automation failed (non-blocking): {str(e)}")
        
        return booking
    
    def update_booking(self, booking_id: int, booking_data: BookingUpdate, business_id: int) -> Booking:
        """
        Update an existing booking.
        
        VALIDATIONS:
        - Booking must belong to the same business_id
        
        No automatic event triggers on update.
        Events must be triggered explicitly if needed.
        """
        log_info(f"[SERVICE] Updating booking {booking_id}")
        
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.business_id == business_id
        ).first()
        
        if not booking:
            raise ValueError(f"Booking {booking_id} not found in your business")
        
        # Update fields
        update_data = booking_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking, field, value)
        
        self.db.commit()
        self.db.refresh(booking)
        
        log_info(f"[SERVICE] Booking updated: {booking.id}")
        return booking
    
    def get_booking(self, booking_id: int, business_id: int) -> Booking:
        """
        Get booking by ID scoped to business_id.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.business_id == business_id
        ).first()
    
    def get_bookings(
        self,
        business_id: int,
        skip: int = 0,
        limit: int = 100,
        status: BookingStatus = None
    ) -> list[Booking]:
        """
        Get bookings with pagination and optional status filter.
        
        Multi-tenant isolation: filtered by business_id.
        Pagination: enforces max limit of 100
        """
        # Enforce max limit
        limit = min(limit, 100)
        
        query = self.db.query(Booking).filter(Booking.business_id == business_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def send_reminder(self, booking_id: int, business_id: int):
        """
        Manually trigger booking reminder.
        
        EVENT TRIGGER: handle_booking_reminder
        """
        log_info(f"[SERVICE] Sending reminder for booking {booking_id}")
        
        booking = self.get_booking(booking_id, business_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found in your business")
        
        # EXPLICIT EVENT TRIGGER
        self.automation.handle_booking_reminder(booking)
    
    def send_form_reminder(self, booking_id: int, business_id: int):
        """
        Manually trigger form reminder.
        
        EVENT TRIGGER: handle_form_pending_reminder
        """
        log_info(f"[SERVICE] Sending form reminder for booking {booking_id}")
        
        booking = self.get_booking(booking_id, business_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found in your business")
        
        # EXPLICIT EVENT TRIGGER
        self.automation.handle_form_pending_reminder(booking)
    
    def delete_booking(self, booking_id: int, business_id: int) -> bool:
        """
        Delete a booking scoped to business_id.
        
        Multi-tenant isolation: filtered by business_id.
        Returns True if deleted, False if not found.
        """
        log_info(f"[SERVICE] Deleting booking {booking_id}")
        
        booking = self.get_booking(booking_id, business_id)
        if not booking:
            return False
        
        self.db.delete(booking)
        self.db.commit()
        
        log_info(f"[SERVICE] Booking deleted: id={booking_id}")
        return True
