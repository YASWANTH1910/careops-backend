"""
Business Routes — CareOps SaaS

PATCH /business/onboard → marks the owner's business as fully onboarded.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User, UserRole
from app.schemas.user_schema import BusinessResponse
from app.core.logger import log_info

router = APIRouter(prefix="/business", tags=["Business"])


@router.patch("/onboard", response_model=BusinessResponse)
def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark the current owner's business as onboarded.

    - Admin only (403 for non-admin users).
    - Idempotent — calling again when already onboarded is safe.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the business admin can complete onboarding."
        )

    business = current_user.business
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found."
        )

    business.is_onboarded = True
    db.commit()
    db.refresh(business)

    log_info(f"[BUSINESS] Onboarding completed: business_id={business.id}")
    return BusinessResponse.model_validate(business)
