from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.logger import log_info, log_error
from app.models.message import Message, MessageChannel, MessageDirection, MessageStatus
from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.email_service import send_email as smtp_send_email


class IntegrationService:
    """
    Integration service for external communications.
    
    CRITICAL DESIGN PRINCIPLE:
    - Integration failures MUST NOT break core business flow
    - All failures are logged and create alerts
    - Returns status for tracking, but doesn't raise exceptions
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        contact_id: int,
        business_id: int,
        assigned_user_id: Optional[int] = None
    ) -> bool:
        """
        Send email via integration (SendGrid/SMTP).
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content
            contact_id: Contact ID for message association
            business_id: Business ID for alert association and multi-tenant isolation
            assigned_user_id: Optional assigned user ID
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = Message(
            business_id=business_id,
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
            channel=MessageChannel.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.PENDING,
            content=content,
            subject=subject
        )
        
        try:
            log_info(f"[INTEGRATION] Sending email to {to_email}: {subject}")

            email_sent = smtp_send_email(
                to_email=to_email,
                subject=subject,
                body=content
            )

            if email_sent:
                message.status = MessageStatus.SENT
                message.sent_at = datetime.now(timezone.utc)
                log_info(f"[INTEGRATION] Email sent successfully to {to_email}")
            else:
                message.status = MessageStatus.FAILED
                message.error_message = "SMTP send failed or SMTP is not configured"
                log_error(f"[INTEGRATION] Email delivery failed to {to_email}")

            self.db.add(message)
            self.db.commit()
            return email_sent
            
        except Exception as e:
            log_error(f"[INTEGRATION] Failed to send email to {to_email}: {str(e)}")
            
            try:
                # Update message status
                message.status = MessageStatus.FAILED
                message.error_message = str(e)
                self.db.add(message)
                
                # Create integration alert with proper business_id
                alert = Alert(
                    business_id=business_id,
                    type=AlertType.INTEGRATION,
                    severity=AlertSeverity.WARNING,
                    message=f"Failed to send email to {to_email}",
                    details=str(e),
                    is_dismissed=False,
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(alert)
                self.db.commit()
                log_info(f"[INTEGRATION] Created alert for email failure")
            except Exception as alert_error:
                log_error(f"[INTEGRATION] Failed to create failure alert: {str(alert_error)}")
            
            return False
    
    def send_sms(
        self,
        to_phone: str,
        content: str,
        contact_id: int,
        business_id: int,
        assigned_user_id: Optional[int] = None
    ) -> bool:
        """
        Send SMS via integration (Twilio).
        
        Args:
            to_phone: Recipient phone number
            content: SMS content
            contact_id: Contact ID for message association
            business_id: Business ID for alert association and multi-tenant isolation
            assigned_user_id: Optional assigned user ID
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = Message(
            business_id=business_id,
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
            channel=MessageChannel.SMS,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.PENDING,
            content=content
        )
        
        try:
            # TODO: Implement actual Twilio integration
            # For now, simulate success
            log_info(f"[INTEGRATION] Sending SMS to {to_phone}")
            
            # Simulate SMS sending
            message.status = MessageStatus.SENT
            message.sent_at = datetime.now(timezone.utc)
            
            self.db.add(message)
            self.db.commit()
            
            log_info(f"[INTEGRATION] SMS sent successfully to {to_phone}")
            return True
            
        except Exception as e:
            log_error(f"[INTEGRATION] Failed to send SMS to {to_phone}: {str(e)}")
            
            try:
                # Update message status
                message.status = MessageStatus.FAILED
                message.error_message = str(e)
                self.db.add(message)
                
                # Create integration alert with proper business_id
                alert = Alert(
                    business_id=business_id,
                    type=AlertType.INTEGRATION,
                    severity=AlertSeverity.WARNING,
                    message=f"Failed to send SMS to {to_phone}",
                    details=str(e),
                    is_dismissed=False,
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(alert)
                self.db.commit()
                log_info(f"[INTEGRATION] Created alert for SMS failure")
            except Exception as alert_error:
                log_error(f"[INTEGRATION] Failed to create failure alert: {str(alert_error)}")
            
            return False
    
    def create_calendar_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendee_email: str,
        business_id: int
    ) -> bool:
        """
        Create calendar event via integration (Google Calendar/Outlook).
        
        Args:
            title: Event title
            start_time: Event start time (should be timezone-aware)
            end_time: Event end time (should be timezone-aware)
            attendee_email: Attendee email address
            business_id: Business ID for alert association and multi-tenant isolation
        
        Returns:
            True if created successfully, False otherwise
        """
        try:
            # TODO: Implement actual calendar integration
            log_info(f"[INTEGRATION] Creating calendar event: {title} at {start_time}")
            
            # Simulate calendar event creation
            log_info(f"[INTEGRATION] Calendar event created successfully")
            return True
            
        except Exception as e:
            log_error(f"[INTEGRATION] Failed to create calendar event: {str(e)}")
            
            try:
                # Create integration alert with proper business_id
                alert = Alert(
                    business_id=business_id,
                    type=AlertType.INTEGRATION,
                    severity=AlertSeverity.WARNING,
                    message=f"Failed to create calendar event: {title}",
                    details=str(e),
                    is_dismissed=False,
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(alert)
                self.db.commit()
                log_info(f"[INTEGRATION] Created alert for calendar event failure")
            except Exception as alert_error:
                log_error(f"[INTEGRATION] Failed to create failure alert: {str(alert_error)}")
            
            return False
    
    def trigger_webhook(self, event_type: str, payload: dict, business_id: int) -> bool:
        """
        Trigger webhook for external integrations.
        
        Args:
            event_type: Type of event (e.g., "booking.created")
            payload: Event payload
            business_id: Business ID for alert association and multi-tenant isolation
        
        Returns:
            True if triggered successfully, False otherwise
        """
        try:
            # TODO: Implement actual webhook integration
            log_info(f"[INTEGRATION] Triggering webhook: {event_type}")
            
            # Simulate webhook trigger
            log_info(f"[INTEGRATION] Webhook triggered successfully")
            return True
            
        except Exception as e:
            log_error(f"[INTEGRATION] Failed to trigger webhook: {str(e)}")
            
            try:
                # Create integration alert with proper business_id
                alert = Alert(
                    business_id=business_id,
                    type=AlertType.INTEGRATION,
                    severity=AlertSeverity.WARNING,
                    message=f"Failed to trigger webhook: {event_type}",
                    details=str(e),
                    is_dismissed=False,
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(alert)
                self.db.commit()
                log_info(f"[INTEGRATION] Created alert for webhook failure")
            except Exception as alert_error:
                log_error(f"[INTEGRATION] Failed to create failure alert: {str(alert_error)}")
            
            return False
