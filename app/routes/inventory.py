from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.logger import log_info, log_warning
from app.dependencies.auth_dependency import get_current_user, require_admin
from app.models.user import User
from app.models.inventory import Inventory
from app.schemas.inventory_schema import InventoryCreate, InventoryUpdate, InventoryResponse
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(require_admin),  # Only admins manage inventory
):
    """
    Create a new inventory item for the admin's business.

    Admin-only: only admins can manage inventory.
    EVENT TRIGGER: Creates alert if quantity is below threshold.
    """
    log_info(
        f"[Inventory] Create requested: user_id={owner.id}, role={owner.role!r}, "
        f"business_id={owner.business_id}, item='{inventory_data.item_name}'"
    )
    try:
        service = InventoryService(db)
        inventory = service.create_inventory(inventory_data, business_id=owner.business_id)
        log_info(f"[Inventory] Item created: id={inventory.id}, name='{inventory_data.item_name}'")
        return InventoryResponse.model_validate(inventory)
    except Exception as exc:
        db.rollback()
        log_warning(f"[Inventory] ERROR creating item: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create inventory item: {str(exc)}"
        )



@router.get("", response_model=List[InventoryResponse])
def get_inventory(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all inventory items for the current user's business."""
    service = InventoryService(db)
    items = service.get_all_inventory(skip=skip, limit=limit, business_id=current_user.business_id)
    return [InventoryResponse.model_validate(i) for i in items]


@router.get("/low-stock", response_model=List[InventoryResponse])
def get_low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all low-stock items for the current business."""
    service = InventoryService(db)
    items = service.get_low_stock_items(business_id=current_user.business_id)
    return [InventoryResponse.model_validate(i) for i in items]


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory_item(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get inventory item by ID — must belong to current business."""
    item = db.query(Inventory).filter(
        Inventory.id == inventory_id,
        Inventory.business_id == current_user.business_id,
    ).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item {inventory_id} not found"
        )
    return InventoryResponse.model_validate(item)


@router.patch("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(
    inventory_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    owner: User = Depends(require_admin),  # Mutating inventory requires admin
):
    """
    Update inventory item — Owner only.

    EVENT TRIGGER: Creates alert if quantity drops below threshold.
    """
    service = InventoryService(db)
    try:
        item = service.update_inventory(inventory_id, inventory_data, business_id=owner.business_id)
        return InventoryResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
