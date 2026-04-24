from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.models.booking import BookingStatus
from app.schemas.booking_schema import BookingCreate, BookingUpdate, BookingResponse
from app.services.booking_service import BookingService
from app.services.contact_service import ContactService
from app.core.logger import log_info

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# Schema for public booking (no auth required)
class PublicBookingCreate(BaseModel):
    """Schema for creating a booking from public form."""
    business_id: int
    contact_id: int
    start_time: str  # ISO format: "2024-12-25T14:30:00Z"
    end_time: str    # ISO format: "2024-12-25T15:30:00Z"
    service_type: Optional[str] = None
    notes: Optional[str] = None


@router.post("/public", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_public_booking(
    booking_data: PublicBookingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a booking from public form (no authentication required).
    
    Expected flow:
    1. Frontend calls POST /contacts/public to create/get contact
    2. Frontend calls this endpoint with the returned contact_id
    3. Returns booking response
    """
    log_info(f"[ROUTE] Creating public booking for business {booking_data.business_id}, contact: {booking_data.contact_id}")
    log_info(f"[ROUTE] Public booking request: start_time={booking_data.start_time}, end_time={booking_data.end_time}")
    
    try:
        booking_service = BookingService(db)
        
        # Parse ISO datetime strings to datetime objects
        from datetime import datetime
        try:
            start_time = datetime.fromisoformat(booking_data.start_time.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(booking_data.end_time.replace('Z', '+00:00'))
            log_info(f"[ROUTE] Parsed datetime: start={start_time}, end={end_time}")
        except Exception as parse_error:
            log_info(f"[ROUTE] DateTime parsing error: {str(parse_error)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime format: {str(parse_error)}"
            )
        
        booking_create = BookingCreate(
            contact_id=booking_data.contact_id,
            assigned_user_id=None,
            start_time=start_time,
            end_time=end_time,
            service_type=booking_data.service_type,
            notes=booking_data.notes
        )
        
        booking = booking_service.create_booking(booking_create, business_id=booking_data.business_id)
        log_info(f"[ROUTE] Public booking created: {booking.id}")
        
        return BookingResponse.model_validate(booking)
    except HTTPException:
        raise
    except Exception as e:
        log_info(f"[ROUTE] Error creating public booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new booking.
    
    VALIDATIONS (service-level):
    - Booking date cannot be in the past
    - Contact must belong to the same business
    
    EVENT TRIGGER: Sends confirmation message via automation.
    """
    log_info(f"[ROUTE] POST /bookings - user_id={current_user.id}, business_id={current_user.business_id}")
    log_info(f"[ROUTE] Request: contact_id={booking_data.contact_id}, start_time={booking_data.start_time}")
    
    service = BookingService(db)
    try:
        booking = service.create_booking(booking_data, business_id=current_user.business_id)
        log_info(f"[ROUTE] Booking created successfully: id={booking.id}")
        return BookingResponse.model_validate(booking)
    except HTTPException:
        raise
    except Exception as e:
        log_info(f"[ROUTE] Error creating booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[BookingResponse])
def get_bookings(
    skip: int = 0,
    limit: int = 100,
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all bookings with pagination and optional status filter.
    
    Pagination: skip, limit (max 100)
    """
    log_info(f"[ROUTE] GET /bookings - user_id={current_user.id}, business_id={current_user.business_id}, status={status}")
    
    service = BookingService(db)
    bookings = service.get_bookings(
        business_id=current_user.business_id,
        skip=skip,
        limit=limit,
        status=status
    )
    
    log_info(f"[ROUTE] Returned {len(bookings)} bookings for business {current_user.business_id}")
    return [BookingResponse.model_validate(b) for b in bookings]


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get booking by ID."""
    service = BookingService(db)
    booking = service.get_booking(booking_id, business_id=current_user.business_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking {booking_id} not found"
        )
    return BookingResponse.model_validate(booking)


@router.patch("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update booking details."""
    service = BookingService(db)
    try:
        booking = service.update_booking(booking_id, booking_data, business_id=current_user.business_id)
        return BookingResponse.model_validate(booking)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise


@router.post("/{booking_id}/send-reminder", status_code=status.HTTP_200_OK)
def send_booking_reminder(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually send booking reminder."""
    service = BookingService(db)
    try:
        service.send_reminder(booking_id, business_id=current_user.business_id)
        return {"message": "Reminder sent successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{booking_id}/send-form-reminder", status_code=status.HTTP_200_OK)
def send_form_reminder(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually send form completion reminder."""
    service = BookingService(db)
    try:
        service.send_form_reminder(booking_id, business_id=current_user.business_id)
        return {"message": "Form reminder sent successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{booking_id}", status_code=status.HTTP_200_OK)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a booking."""
    service = BookingService(db)
    deleted = service.delete_booking(booking_id, business_id=current_user.business_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking {booking_id} not found"
        )
    return {"message": "Booking deleted successfully"}
