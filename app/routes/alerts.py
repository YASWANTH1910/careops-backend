from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.models.alert import AlertType, AlertSeverity
from app.schemas.alert_schema import AlertResponse, AlertDismiss
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    skip: int = 0,
    limit: int = 100,
    include_dismissed: bool = False,
    alert_type: Optional[AlertType] = None,
    severity: Optional[AlertSeverity] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alerts for the current business with pagination and filters."""
    service = AlertService(db)
    alerts = service.get_alerts(
        business_id=current_user.business_id,
        skip=skip,
        limit=limit,
        include_dismissed=include_dismissed,
        alert_type=alert_type,
        severity=severity,
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get("/count", response_model=dict)
def get_alert_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of active alerts for the current business."""
    service = AlertService(db)
    count = service.get_active_alert_count(business_id=current_user.business_id)
    return {"active_count": count}


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alert by ID — must belong to current business."""
    service = AlertService(db)
    alert = service.get_alert(alert_id, business_id=current_user.business_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dismiss an alert (doesn't delete it) — must belong to current business."""
    service = AlertService(db)
    # Verify the alert belongs to this business before dismissing
    alert = service.get_alert(alert_id, business_id=current_user.business_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found")
    try:
        alert = service.dismiss_alert(alert_id)
        return AlertResponse.model_validate(alert)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
