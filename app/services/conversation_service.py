"""
Conversation Service — Business logic for conversation management.

Aggregates messages into conversations grouped by contact.
CRITICAL: All queries MUST filter by business_id for multi-tenant isolation.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.models.message import Message
from app.models.contact import Contact
from app.core.logger import log_info, log_warning


class ConversationService:
    """Service for managing conversations with multi-tenant isolation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_conversations(
        self,
        business_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations (contacts with messages) for a business.
        
        **CRITICAL SECURITY**: This query MUST filter by business_id!
        It previously had ZERO tenant isolation (security hole).
        
        Returns conversations sorted by most recent message.
        """
        log_info(f"[SERVICE] Fetching conversations for business {business_id}")
        
        # Get all contacts that have messages, scoped to business
        contacts_with_messages = self.db.query(Contact).filter(
            Contact.business_id == business_id
        ).join(Message).distinct().all()
        
        conversations = []
        
        for contact in contacts_with_messages:
            # Get messages for this contact (scoped to business)
            messages = self.db.query(Message).filter(
                Message.contact_id == contact.id,
                Message.business_id == business_id
            ).order_by(Message.created_at.asc()).all()
            
            if not messages:
                continue
            
            last_message = messages[-1]
            
            conversations.append(self._build_conversation_dict(contact, messages, last_message))
        
        # Sort by most recent message
        conversations.sort(key=lambda x: x["updatedAt"], reverse=True)
        
        return conversations[skip : skip + limit]
    
    def get_conversation(
        self,
        contact_id: int,
        business_id: int
    ) -> Dict[str, Any]:
        """
        Get a single conversation by contact ID.
        
        **CRITICAL SECURITY**: This query MUST filter by business_id!
        
        Returns all messages for the contact scoped to business.
        Raises ValueError if contact doesn't belong to the business.
        """
        log_info(f"[SERVICE] Fetching conversation for contact {contact_id}, business {business_id}")
        
        # Get contact, scoped to business
        contact = self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.business_id == business_id
        ).first()
        
        if not contact:
            raise ValueError(f"Conversation not found or doesn't belong to this business")
        
        # Get messages for this contact, scoped to business
        messages = self.db.query(Message).filter(
            Message.contact_id == contact_id,
            Message.business_id == business_id
        ).order_by(Message.created_at.asc()).all()
        
        if not messages:
            last_message = None
        else:
            last_message = messages[-1]
        
        return self._build_conversation_dict(contact, messages, last_message)
    
    def _build_conversation_dict(
        self,
        contact: Contact,
        messages: List[Message],
        last_message: Message
    ) -> Dict[str, Any]:
        """Helper to build conversation dictionary from contact and messages."""
        contact_name = contact.name or "Unknown"
        
        return {
            "id": str(contact.id),
            "contactId": contact.id,
            "contactName": contact_name,
            "contactEmail": contact.email,
            "contactPhone": contact.phone,
            "messages": [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "sender": "admin" if m.direction == "outgoing" else "contact",
                    "channel": m.channel,
                    "timestamp": m.created_at.isoformat(),
                    "status": m.status.value if hasattr(m.status, 'value') else str(m.status)
                } for m in messages
            ],
            "lastMessage": {
                "content": last_message.content,
                "timestamp": last_message.created_at.isoformat()
            } if last_message else None,
            "unreadCount": self._count_unread_messages(messages),
            "status": "Open",
            "updatedAt": last_message.created_at.isoformat() if last_message else contact.created_at.isoformat(),
            "automationStatus": "Active"
        }
    
    def _count_unread_messages(self, messages: List[Message]) -> int:
        """Count unread messages in a conversation."""
        return sum(1 for m in messages if m.status == "unread" or m.status.value == "unread")
    
    def get_contact_messages(
        self,
        contact_id: int,
        business_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a contact, paginated.
        
        **CRITICAL SECURITY**: This query MUST filter by business_id!
        """
        messages = self.db.query(Message).filter(
            Message.contact_id == contact_id,
            Message.business_id == business_id
        ).order_by(Message.created_at.asc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": str(m.id),
                "content": m.content,
                "sender": "admin" if m.direction == "outgoing" else "contact",
                "channel": m.channel,
                "timestamp": m.created_at.isoformat(),
                "status": m.status.value if hasattr(m.status, 'value') else str(m.status)
            } for m in messages
        ]
    
    def send_message(
        self,
        contact_id: int,
        business_id: int,
        content: str,
        channel: str,
        assigned_user_id: int = None
    ) -> Message:
        """
        Send a message to a contact (admin → contact).
        
        Validates contact belongs to business before sending.
        
        **CRITICAL SECURITY**: This MUST verify contact belongs to business!
        """
        log_info(f"[SERVICE] Sending message to contact {contact_id}, business {business_id}")
        
        # Verify contact exists and belongs to business
        contact = self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.business_id == business_id
        ).first()
        
        if not contact:
            raise ValueError(f"Contact not found or doesn't belong to this business")
        
        message = Message(
            contact_id=contact_id,
            business_id=business_id,
            content=content,
            channel=channel,
            direction="outgoing",
            assigned_user_id=assigned_user_id,
            status="sent"
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
