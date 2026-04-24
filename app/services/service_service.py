from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from app.models.service import Service
from app.schemas.service_schema import ServiceCreate, ServiceUpdate
from app.core.logger import log_info, log_warning


class ServiceService:
    """
    Service business logic for managing services.
    
    VALIDATIONS:
    - Service name must be non-empty
    - Duration must be positive
    - All queries scoped to business_id (multi-tenant isolation)
    
    Soft delete: is_active flag instead of hard delete.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_service(self, service_data: ServiceCreate, business_id: int) -> Service:
        """
        Create a new service with validations.
        
        VALIDATIONS:
        - Name must be non-empty
        - Duration must be positive
        
        Multi-tenant isolation: Scoped to business_id.
        """
        log_info(f"[SERVICE] Creating service: {service_data.name} for business {business_id}")
        
        # Validation: Name required and non-empty
        if not service_data.name or not service_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service name is required and cannot be empty"
            )
        
        # Validation: Duration must be positive
        if service_data.duration_minutes <= 0:
            log_warning(f"[SERVICE] Invalid duration rejected: {service_data.duration_minutes}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service duration must be greater than 0 minutes"
            )
        
        service = Service(
            **service_data.model_dump(),
            business_id=business_id
        )
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        
        log_info(f"[SERVICE] Service created: id={service.id}, name={service.name}")
        return service
    
    def get_services(self, business_id: int, skip: int = 0, limit: int = 50) -> list[Service]:
        """
        Get all active services for a business with pagination.
        
        Multi-tenant isolation: Filtered by business_id.
        Pagination: Enforces max limit of 100.
        """
        log_info(f"[SERVICE] Fetching services for business {business_id}")
        
        # Enforce max limit
        limit = min(limit, 100)
        
        services = self.db.query(Service).filter(
            Service.business_id == business_id,
            Service.is_active == True  # Only active services
        ).offset(skip).limit(limit).all()
        
        return services
    
    def get_service(self, service_id: int, business_id: int) -> Service:
        """
        Get a single service by ID.
        
        Multi-tenant isolation: Filtered by business_id.
        Returns None if not found.
        """
        log_info(f"[SERVICE] Fetching service {service_id}")
        
        service = self.db.query(Service).filter(
            Service.id == service_id,
            Service.business_id == business_id
        ).first()
        
        return service
    
    def update_service(self, service_id: int, service_data: ServiceUpdate, business_id: int) -> Service:
        """
        Update service details with validations.
        
        Multi-tenant isolation: Filtered by business_id.
        
        VALIDATIONS:
        - If updating name: must be non-empty
        - If updating duration: must be positive
        """
        log_info(f"[SERVICE] Updating service {service_id} for business {business_id}")
        
        service = self.get_service(service_id, business_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_id} not found"
            )
        
        # Validation: If updating name, it must be non-empty
        if service_data.name is not None and not service_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service name cannot be empty"
            )
        
        # Validation: If updating duration, it must be positive
        if service_data.duration_minutes is not None and service_data.duration_minutes <= 0:
            log_warning(f"[SERVICE] Invalid duration update rejected: {service_data.duration_minutes}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service duration must be greater than 0 minutes"
            )
        
        # Update fields
        update_data = service_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)
        
        service.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(service)
        
        log_info(f"[SERVICE] Service updated: {service.id}")
        return service
    
    def delete_service(self, service_id: int, business_id: int) -> bool:
        """
        Soft delete a service (set is_active=False).
        
        Multi-tenant isolation: Filtered by business_id.
        Returns True if deleted, False if not found.
        """
        log_info(f"[SERVICE] Deleting service {service_id}")
        
        service = self.get_service(service_id, business_id)
        if not service:
            return False
        
        service.is_active = False
        service.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        log_info(f"[SERVICE] Service deleted (soft): id={service_id}")
        return True
    
    def get_public_services(self, business_id: int) -> list[Service]:
        """
        Get all active services for a business (public endpoint).
        
        Used for unauthenticated customers viewing available services for booking.
        
        Multi-tenant isolation: Filtered by business_id.
        No authentication required.
        """
        log_info(f"[SERVICE] Fetching public services for business {business_id}")
        
        services = self.db.query(Service).filter(
            Service.business_id == business_id,
            Service.is_active == True
        ).all()
        
        return services
