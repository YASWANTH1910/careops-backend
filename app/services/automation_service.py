from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.logger import log_info
from app.models.contact import Contact
from app.models.booking import Booking
from app.services.integration_service import IntegrationService


class AutomationService:
    """
    Event-based automation service.
    
    CRITICAL DESIGN PRINCIPLES:
    - Automation triggers ONLY on explicit events
    - Never runs silently or with hidden conditions
    - Always called explicitly from service layer
    - Integration failures don't break automation flow
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.integration = IntegrationService(db)
    
    def handle_new_contact(self, contact: Contact):
        """
        EVENT: New contact created
        ACTION: Send welcome message
        """
        log_info(f"[AUTOMATION] Handling new contact event: {contact.id}")
        
        if contact.email:
            try:
                success = self.integration.send_email(
                    to_email=contact.email,
                    subject="Welcome to CareOps!",
                    content=f"Hi {contact.name},\n\nThank you for contacting us. We'll be in touch soon!",
                    contact_id=contact.id,
                    business_id=contact.business_id
                )
                log_info(f"[AUTOMATION] Welcome email sent: {success}")
            except Exception as e:
                log_info(f"[AUTOMATION] Email sending failed (non-blocking): {str(e)}")
        
        if contact.phone:
            try:
                success = self.integration.send_sms(
                    to_phone=contact.phone,
                    content=f"Hi {contact.name}, thank you for contacting us!",
                    contact_id=contact.id,
                    business_id=contact.business_id
                )
                log_info(f"[AUTOMATION] Welcome SMS sent: {success}")
            except Exception as e:
                log_info(f"[AUTOMATION] SMS sending failed (non-blocking): {str(e)}")
    
    def handle_booking_created(self, booking: Booking):
        """
        EVENT: Booking created
        ACTION: Send confirmation message
        """
        log_info(f"[AUTOMATION] Handling booking created event: {booking.id}")
        
        contact = self.db.query(Contact).filter(Contact.id == booking.contact_id).first()
        if not contact:
            log_info(f"[AUTOMATION] Contact not found for booking {booking.id}")
            return
        
        message = f"Hi {contact.name}, your booking is confirmed for {booking.start_time.strftime('%Y-%m-%d %H:%M')}."
        
        if contact.email:
            try:
                success = self.integration.send_email(
                    to_email=contact.email,
                    subject="Booking Confirmation",
                    content=message,
                    contact_id=contact.id,
                    business_id=booking.business_id
                )
                log_info(f"[AUTOMATION] Booking confirmation email sent: {success}")
            except Exception as e:
                log_info(f"[AUTOMATION] Email sending failed (non-blocking): {str(e)}")
        
        if contact.phone:
            try:
                success = self.integration.send_sms(
                    to_phone=contact.phone,
                    content=message,
                    contact_id=contact.id,
                    business_id=booking.business_id
                )
                log_info(f"[AUTOMATION] Booking confirmation SMS sent: {success}")
            except Exception as e:
                log_info(f"[AUTOMATION] SMS sending failed (non-blocking): {str(e)}")
        
        # Create calendar event
        if contact.email:
            try:
                self.integration.create_calendar_event(
                    title=f"Booking with {contact.name}",
                    start_time=booking.start_time,
                    end_time=booking.end_time,
                    attendee_email=contact.email,
                    business_id=booking.business_id
                )
            except Exception as e:
                log_info(f"[AUTOMATION] Calendar event creation failed (non-blocking): {str(e)}")
    
    def handle_booking_reminder(self, booking: Booking):
        """
        EVENT: Booking reminder (triggered by scheduler)
        ACTION: Send reminder message
        """
        log_info(f"[AUTOMATION] Handling booking reminder event: {booking.id}")
        
        contact = self.db.query(Contact).filter(Contact.id == booking.contact_id).first()
        if not contact:
            return
        
        message = f"Hi {contact.name}, reminder: your booking is tomorrow at {booking.start_time.strftime('%H:%M')}."
        
        if contact.email:
            try:
                self.integration.send_email(
                    to_email=contact.email,
                    subject="Booking Reminder",
                    content=message,
                    contact_id=contact.id,
                    business_id=booking.business_id
                )
            except Exception as e:
                log_info(f"[AUTOMATION] Email sending failed (non-blocking): {str(e)}")
        
        if contact.phone:
            try:
                self.integration.send_sms(
                    to_phone=contact.phone,
                    content=message,
                    contact_id=contact.id,
                    business_id=booking.business_id
                )
            except Exception as e:
                log_info(f"[AUTOMATION] SMS sending failed (non-blocking): {str(e)}")
    
    def handle_form_pending_reminder(self, booking: Booking):
        """
        EVENT: Form still pending (triggered by scheduler)
        ACTION: Send form reminder
        """
        log_info(f"[AUTOMATION] Handling form pending reminder event: {booking.id}")
        
        contact = self.db.query(Contact).filter(Contact.id == booking.contact_id).first()
        if not contact:
            return
        
        message = f"Hi {contact.name}, please complete your intake form before your appointment."
        
        if contact.email:
            try:
                self.integration.send_email(
                    to_email=contact.email,
                    subject="Form Reminder",
                    content=message,
                    contact_id=contact.id,
                    business_id=booking.business_id
                )
            except Exception as e:
                log_info(f"[AUTOMATION] Email sending failed (non-blocking): {str(e)}")
        
        if contact.phone:
            try:
                self.integration.send_sms(
                    to_phone=contact.phone,
                    content=message,
                    contact_id=contact.id,
                    business_id=booking.business_id
                )
            except Exception as e:
                log_info(f"[AUTOMATION] SMS sending failed (non-blocking): {str(e)}")
    
    def should_stop_automation(self, contact_id: int) -> bool:
        """
        Check if automation should stop for a contact.
        
        RULE: Automation stops when an admin replies to the contact.
        """
        from app.models.message import Message, MessageDirection
        
        # Check if an admin has sent any message to this contact
        admin_message = self.db.query(Message).filter(
            Message.contact_id == contact_id,
            Message.direction == MessageDirection.OUTGOING,
            Message.assigned_user_id.isnot(None)
        ).first()
        
        return admin_message is not None

