from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from app.schemas.service_schema import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServicePublicResponse
)
from app.services.service_service import ServiceService


# ADMIN ROUTES
router = APIRouter(prefix="/services", tags=["Services"])

# PUBLIC ROUTES
public_router = APIRouter(prefix="/public/services", tags=["Public Services"])


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ServiceService(db)

    try:
        new_service = service.create_service(
            service_data,
            business_id=current_user.business_id
        )
        return ServiceResponse.model_validate(new_service)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[ServiceResponse])
def get_services(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ServiceService(db)

    services = service.get_services(
        business_id=current_user.business_id,
        skip=skip,
        limit=limit
    )

    return [ServiceResponse.model_validate(s) for s in services]


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ServiceService(db)

    found_service = service.get_service(
        service_id,
        business_id=current_user.business_id
    )

    if not found_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )

    return ServiceResponse.model_validate(found_service)


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ServiceService(db)

    try:
        updated_service = service.update_service(
            service_id,
            service_data,
            business_id=current_user.business_id
        )

        return ServiceResponse.model_validate(updated_service)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{service_id}", status_code=status.HTTP_200_OK)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ServiceService(db)

    deleted = service.delete_service(
        service_id,
        business_id=current_user.business_id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )

    return {"message": "Service deleted successfully"}


# PUBLIC SERVICES (NO AUTH REQUIRED)

@public_router.get("/{business_id}", response_model=List[ServicePublicResponse])
def get_public_services(
    business_id: int,
    db: Session = Depends(get_db)
):
    service = ServiceService(db)

    services = service.get_public_services(business_id)

    return [ServicePublicResponse.model_validate(s) for s in services]