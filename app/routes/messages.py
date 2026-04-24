from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.schemas.message_schema import MessageCreate, MessageResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new message."""
    service = MessageService(db)
    message = service.create_message(message_data, business_id=current_user.business_id)
    
    return MessageResponse.model_validate(message)


@router.get("/{contact_id}", response_model=List[MessageResponse])
def get_messages_by_contact(
    contact_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages for a specific contact."""
    service = MessageService(db)
    messages = service.get_messages_by_contact(
        contact_id=contact_id,
        business_id=current_user.business_id,
        skip=skip,
        limit=limit
    )
    
    return [MessageResponse.model_validate(m) for m in messages]


@router.get("", response_model=List[MessageResponse])
def get_all_messages(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages for the business with pagination."""
    service = MessageService(db)
    messages = service.get_messages_for_business(
        business_id=current_user.business_id,
        skip=skip,
        limit=limit
    )
    
    return [MessageResponse.model_validate(m) for m in messages]
