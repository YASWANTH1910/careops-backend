"""
Dashboard Service — Business logic for dashboard statistics and aggregations.

All complex queries and aggregations are centralized here.
Multi-tenant isolation ensures all queries filter by business_id.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.models.booking import Booking, BookingStatus
from app.models.contact import Contact
from app.models.inventory import Inventory
from app.models.alert import Alert
from app.models.message import Message, MessageDirection, MessageStatus
from app.core.logger import log_info


class DashboardService:
    """Service for aggregating dashboard metrics with multi-tenant isolation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_stats(self, business_id: int) -> dict:
        """
        Get all dashboard statistics for a business.
        
        Returns a dictionary with booking, contact, inventory, alert, and message stats.
        
        Multi-tenant isolation: all queries filtered by business_id.
        Defensive: always returns valid JSON structure even if individual stats fail.
        """
        log_info(f"[SERVICE] Fetching dashboard stats for business {business_id}")
        
        # Initialize with safe defaults
        stats = {
            "bookings": {"total": 0, "today": 0, "upcoming": 0},
            "contacts": {"total": 0, "new_this_week": 0},
            "inventory": {"total_items": 0, "low_stock_items": 0},
            "alerts": {"active": 0, "critical": 0},
            "messages": {"total": 0, "unread": 0},
        }
        
        # Try to fetch each stat independently; continue if one fails
        try:
            stats["bookings"] = self._get_booking_stats(business_id)
        except Exception as e:
            log_info(f"[SERVICE] Error fetching booking stats: {str(e)}")
        
        try:
            stats["contacts"] = self._get_contact_stats(business_id)
        except Exception as e:
            log_info(f"[SERVICE] Error fetching contact stats: {str(e)}")
        
        try:
            stats["inventory"] = self._get_inventory_stats(business_id)
        except Exception as e:
            log_info(f"[SERVICE] Error fetching inventory stats: {str(e)}")
        
        try:
            stats["alerts"] = self._get_alert_stats(business_id)
        except Exception as e:
            log_info(f"[SERVICE] Error fetching alert stats: {str(e)}")
        
        try:
            stats["messages"] = self._get_message_stats(business_id)
        except Exception as e:
            log_info(f"[SERVICE] Error fetching message stats: {str(e)}")
        
        return stats
    
    def _get_booking_stats(self, business_id: int) -> dict:
        """Get booking-related statistics."""
        today = datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)
        
        total_bookings = self.db.query(Booking).filter(
            Booking.business_id == business_id
        ).count()
        
        todays_bookings = self.db.query(Booking).filter(
            Booking.business_id == business_id,
            func.date(Booking.start_time) == today
        ).count()
        
        upcoming_bookings = self.db.query(Booking).filter(
            Booking.business_id == business_id,
            Booking.start_time > now,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        ).count()
        
        return {
            "total": total_bookings,
            "today": todays_bookings,
            "upcoming": upcoming_bookings
        }
    
    def _get_contact_stats(self, business_id: int) -> dict:
        """Get contact-related statistics."""
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        total_contacts = self.db.query(Contact).filter(
            Contact.business_id == business_id
        ).count()
        
        new_contacts_this_week = self.db.query(Contact).filter(
            Contact.business_id == business_id,
            Contact.created_at >= week_ago
        ).count()
        
        return {
            "total": total_contacts,
            "new_this_week": new_contacts_this_week
        }
    
    def _get_inventory_stats(self, business_id: int) -> dict:
        """Get inventory-related statistics."""
        total_inventory_items = self.db.query(Inventory).filter(
            Inventory.business_id == business_id
        ).count()
        
        low_stock_items = self.db.query(Inventory).filter(
            Inventory.business_id == business_id,
            Inventory.quantity < Inventory.threshold
        ).count()
        
        return {
            "total_items": total_inventory_items,
            "low_stock_items": low_stock_items
        }
    
    def _get_alert_stats(self, business_id: int) -> dict:
        """Get alert-related statistics."""
        active_alerts = self.db.query(Alert).filter(
            Alert.business_id == business_id,
            Alert.is_dismissed == False
        ).count()
        
        critical_alerts = self.db.query(Alert).filter(
            Alert.business_id == business_id,
            Alert.is_dismissed == False,
            Alert.severity == "CRITICAL"
        ).count()
        
        return {
            "active": active_alerts,
            "critical": critical_alerts
        }
    
    def _get_message_stats(self, business_id: int) -> dict:
        """Get message-related statistics."""
        try:
            total_messages = self.db.query(Message).filter(
                Message.business_id == business_id
            ).count()
            
            # Get unread incoming messages (DELIVERED status = successfully received)
            # Note: MessageStatus enum only has PENDING, SENT, DELIVERED, FAILED
            # DELIVERED incoming messages are considered "unread" by the business user
            unread_messages = self.db.query(Message).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INCOMING,
                Message.status == MessageStatus.DELIVERED
            ).count()
            
            return {
                "total": total_messages,
                "unread": unread_messages
            }
        except Exception as e:
            log_info(f"[SERVICE] Error fetching message stats for business {business_id}: {str(e)}")
            # Return safe defaults if query fails
            return {
                "total": 0,
                "unread": 0
            }
    
    def get_booking_stats(self, business_id: int) -> dict:
        """Get booking statistics only."""
        return self._get_booking_stats(business_id)
    
    def get_contact_stats(self, business_id: int) -> dict:
        """Get contact statistics only."""
        return self._get_contact_stats(business_id)
    
    def get_inventory_stats(self, business_id: int) -> dict:
        """Get inventory statistics only."""
        return self._get_inventory_stats(business_id)
    
    def get_alert_stats(self, business_id: int) -> dict:
        """Get alert statistics only."""
        return self._get_alert_stats(business_id)
    
    def get_message_stats(self, business_id: int) -> dict:
        """Get message statistics only."""
        return self._get_message_stats(business_id)
