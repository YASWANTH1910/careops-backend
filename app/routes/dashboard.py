from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.services.dashboard_service import DashboardService
from app.core.logger import log_info

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get dashboard statistics and overview.
    
    Returns key metrics for the business operations.
    Always returns valid JSON structure even if some stats fail to compute.
    """
    try:
        service = DashboardService(db)
        stats = service.get_dashboard_stats(business_id=current_user.business_id)
        return stats
    except Exception as e:
        log_info(f"[ROUTE] Error fetching dashboard stats: {str(e)}")
        # Return safe defaults if something goes wrong
        return {
            "bookings": {"total": 0, "today": 0, "upcoming": 0},
            "contacts": {"total": 0, "new_this_week": 0},
            "inventory": {"total_items": 0, "low_stock_items": 0},
            "alerts": {"active": 0, "critical": 0},
            "messages": {"total": 0, "unread": 0},
        }
