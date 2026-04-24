from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status
from app.models.inventory import Inventory
from app.models.alert import Alert, AlertType, AlertSeverity
from app.schemas.inventory_schema import InventoryCreate, InventoryUpdate
from app.core.logger import log_info, log_warning


class InventoryService:
    """
    Inventory service with validations and multi-tenant isolation.
    
    VALIDATIONS:
    - Quantity cannot be negative
    - Item name cannot be empty
    - All queries are scoped to business_id
    
    Triggers alerts when inventory falls below threshold.
    Prevents duplicate alerts for the same low stock event.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_inventory(self, inventory_data: InventoryCreate, business_id: int) -> Inventory:
        """
        Create a new inventory item with validations.
        
        VALIDATIONS:
        - Item name required and non-empty
        - Quantity cannot be negative
        """
        log_info(f"[SERVICE] Creating inventory item: {inventory_data.item_name} for business {business_id}")
        
        # Validation: Item name required
        if not inventory_data.item_name or not inventory_data.item_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item name is required and cannot be empty"
            )
        
        # Validation: Quantity cannot be negative
        if inventory_data.quantity < 0:
            log_warning(f"[SERVICE] Negative quantity rejected: {inventory_data.quantity}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity cannot be negative"
            )

        inventory = Inventory(**inventory_data.model_dump(), business_id=business_id)
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)

        # Check if low stock alert needed
        self._check_and_create_alert(inventory)

        return inventory
    
    def update_inventory(self, inventory_id: int, inventory_data: InventoryUpdate, business_id: int) -> Inventory:
        """
        Update inventory item with validations.
        
        VALIDATIONS:
        - Quantity cannot be negative
        - Item belongs to business_id (multi-tenant isolation)
        
        EVENT TRIGGER: Create alert if quantity drops below threshold
        """
        log_info(f"[SERVICE] Updating inventory {inventory_id} for business {business_id}")

        inventory = self.db.query(Inventory).filter(
            Inventory.id == inventory_id,
            Inventory.business_id == business_id,
        ).first()
        if not inventory:
            raise ValueError(f"Inventory {inventory_id} not found")
        
        # Validation: Quantity cannot be negative
        if 'quantity' in inventory_data.model_dump(exclude_unset=True):
            new_quantity = inventory_data.quantity
            if new_quantity is not None and new_quantity < 0:
                log_warning(f"[SERVICE] Negative quantity rejected: {new_quantity}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity cannot be negative"
                )
        
        # Track if quantity changed
        old_quantity = inventory.quantity
        
        # Update fields
        update_data = inventory_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(inventory, field, value)
        
        inventory.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(inventory)
        
        # Check if alert needed (only if quantity changed)
        if 'quantity' in update_data and inventory.quantity != old_quantity:
            self._check_and_create_alert(inventory)
        
        log_info(f"[SERVICE] Inventory updated: {inventory.id}")
        return inventory
    
    def get_inventory(self, inventory_id: int, business_id: int) -> Inventory:
        """
        Get inventory by ID scoped to business_id.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Inventory).filter(
            Inventory.id == inventory_id,
            Inventory.business_id == business_id,
        ).first()

    def get_all_inventory(self, skip: int = 0, limit: int = 100, business_id: int = None) -> list[Inventory]:
        """
        Get all inventory items with pagination.
        
        Multi-tenant isolation: filtered by business_id.
        Pagination: enforces max limit of 100
        """
        # Enforce max limit
        limit = min(limit, 100)
        
        query = self.db.query(Inventory)
        if business_id is not None:
            query = query.filter(Inventory.business_id == business_id)
        return query.offset(skip).limit(limit).all()

    def get_low_stock_items(self, business_id: int = None) -> list[Inventory]:
        """
        Get all low-stock items.
        
        Multi-tenant isolation: filtered by business_id if provided.
        """
        query = self.db.query(Inventory).filter(Inventory.quantity < Inventory.threshold)
        if business_id is not None:
            query = query.filter(Inventory.business_id == business_id)
        return query.all()
    
    def delete_inventory(self, inventory_id: int, business_id: int) -> bool:
        """
        Delete an inventory item scoped to business_id.
        
        Multi-tenant isolation: filtered by business_id.
        Returns True if deleted, False if not found.
        """
        log_info(f"[SERVICE] Deleting inventory {inventory_id}")
        
        inventory = self.get_inventory(inventory_id, business_id)
        if not inventory:
            return False
        
        self.db.delete(inventory)
        self.db.commit()
        
        log_info(f"[SERVICE] Inventory deleted: id={inventory_id}")
        return True
    
    def _check_and_create_alert(self, inventory: Inventory):
        """
        Check if inventory is low and create alert if needed.
        
        PREVENTS DUPLICATE ALERTS:
        - Only creates alert if no active alert exists for this item
        """
        if not inventory.is_low_stock:
            return
        
        log_warning(f"[SERVICE] Low stock detected for {inventory.item_name}: {inventory.quantity}/{inventory.threshold}")
        
        # Check if active alert already exists
        existing_alert = self.db.query(Alert).filter(
            Alert.type == AlertType.INVENTORY,
            Alert.reference_type == "inventory",
            Alert.reference_id == inventory.id,
            Alert.is_dismissed == False
        ).first()
        
        if existing_alert:
            log_info(f"[SERVICE] Active alert already exists for {inventory.item_name}, skipping")
            return
        
        # Create new alert — scoped to same business as inventory item
        alert = Alert(
            business_id=inventory.business_id,
            type=AlertType.INVENTORY,
            severity=AlertSeverity.WARNING if inventory.quantity > 0 else AlertSeverity.CRITICAL,
            message=f"Low stock: {inventory.item_name}",
            details=f"Current quantity: {inventory.quantity}, Threshold: {inventory.threshold}",
            reference_type="inventory",
            reference_id=inventory.id,
        )

        self.db.add(alert)
        self.db.commit()

        log_info(f"[SERVICE] Low stock alert created for {inventory.item_name}")
