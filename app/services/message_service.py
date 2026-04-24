"""
Message Service — Business logic for message management.

CRITICAL: All queries MUST filter by business_id for multi-tenant isolation.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.message import Message, MessageChannel, MessageStatus, MessageDirection
from app.schemas.message_schema import MessageCreate
from app.core.logger import log_info, log_warning


class MessageService:
    """Service for managing messages with multi-tenant isolation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_message(self, message_data: MessageCreate, business_id: int) -> Message:
        """
        Create a new message scoped to business_id.
        
        Args:
            message_data: MessageCreate schema
            business_id: Tenant ID from authenticated user
            
        Returns:
            Created Message model
            
        Multi-tenant isolation: message is created with business_id.
        """
        log_info(f"[SERVICE] Creating message for business {business_id}")
        
        message = Message(
            **message_data.model_dump(),
            business_id=business_id
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        log_info(f"[SERVICE] Message created: id={message.id}")
        return message
    
    def get_messages_by_contact(
        self,
        contact_id: int,
        business_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Get all messages for a contact, ordered chronologically.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Message).filter(
            Message.contact_id == contact_id,
            Message.business_id == business_id
        ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_messages_for_business(
        self,
        business_id: int,
        skip: int = 0,
        limit: int = 100,
        channel: Optional[MessageChannel] = None,
        direction: Optional[MessageDirection] = None,
        status: Optional[MessageStatus] = None
    ) -> List[Message]:
        """
        Get all messages for a business with optional filters.
        
        **SECURITY**: This query MUST filter by business_id!
        
        Multi-tenant isolation: filtered by business_id.
        """
        query = self.db.query(Message).filter(
            Message.business_id == business_id
        )
        
        if channel:
            query = query.filter(Message.channel == channel)
        if direction:
            query = query.filter(Message.direction == direction)
        if status:
            query = query.filter(Message.status == status)
        
        return query.order_by(
            Message.created_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_message(self, message_id: int, business_id: int) -> Optional[Message]:
        """
        Get a message by ID, scoped to business_id.
        
        Returns None if message doesn't exist or belongs to another tenant.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Message).filter(
            Message.id == message_id,
            Message.business_id == business_id
        ).first()
    
    def mark_message_as_read(self, message_id: int, business_id: int) -> Message:
        """
        Mark a message as read, scoped to business_id.
        
        Raises ValueError if message not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Marking message {message_id} as read for business {business_id}")
        
        message = self.get_message(message_id, business_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        message.status = MessageStatus.READ
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_unread_count(self, business_id: int) -> int:
        """
        Get count of unread incoming messages for a business.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Message).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INCOMING,
            Message.status == MessageStatus.UNREAD
        ).count()
    
    def get_unread_messages_for_contact(self, contact_id: int, business_id: int) -> List[Message]:
        """
        Get unread messages for a specific contact.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Message).filter(
            Message.contact_id == contact_id,
            Message.business_id == business_id,
            Message.direction == MessageDirection.INCOMING,
            Message.status == MessageStatus.UNREAD
        ).all()
