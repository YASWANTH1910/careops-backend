"""
Conversations Routes — CareOps

SECURITY PATTERN: All queries MUST filter by business_id for multi-tenant isolation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.models.contact import Contact
from app.models.message import Message
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=List[Dict[str, Any]])
def get_conversations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all conversations grouped by contact.

    SECURITY: Scoped to current business_id.
    """
    service = ConversationService(db)

    conversations = service.get_conversations(
        business_id=current_user.business_id,
        skip=skip,
        limit=limit
    )

    return conversations


@router.get("/{contact_id}", response_model=Dict[str, Any])
def get_conversation(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single conversation by contact ID.

    SECURITY: Scoped to current business_id.
    """
    service = ConversationService(db)

    try:
        conversation = service.get_conversation(
            contact_id=contact_id,
            business_id=current_user.business_id
        )

        return conversation

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{contact_id}/messages", status_code=status.HTTP_201_CREATED)
def send_message(
    contact_id: int,
    message_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to a contact conversation.

    SECURITY: Contact must belong to the same business.
    """

    contact = (
        db.query(Contact)
        .filter(
            Contact.id == contact_id,
            Contact.business_id == current_user.business_id
        )
        .first()
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    new_message = Message(
        contact_id=contact_id,
        assigned_user_id=current_user.id,
        content=message_data.get("content"),
        channel=message_data.get("channel", "email"),
        direction="outgoing",
        status="sent"
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "id": str(new_message.id),
        "content": new_message.content,
        "sender": "admin",
        "channel": new_message.channel,
        "timestamp": new_message.created_at.isoformat(),
        "status": new_message.status
    }