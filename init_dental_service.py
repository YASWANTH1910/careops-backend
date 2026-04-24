#!/usr/bin/env python3
"""
Initialize or Update Dental Service for Business
This script ensures the Dental Service exists with proper configuration.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.models.service import Service
from app.models.business import Business
from app.core.logger import log_info, log_error

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    log_error("DATABASE_URL not found in environment variables")
    sys.exit(1)

# Create database session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

DENTAL_SERVICE_DATA = {
    "name": "Dental Service",
    "description": "Professional dental cleaning that removes plaque and tartar buildup, helps prevent cavities and gum disease, and keeps teeth and gums healthy. Recommended every 6 months for good oral hygiene.",
    "duration_minutes": 60,
    "price": 0.0,
    "is_active": True,
}

def init_dental_service():
    """Initialize or update Dental Service for business_id=2"""
    try:
        business_id = 2
        
        # Check if business exists
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            log_error(f"Business with ID {business_id} not found")
            return False
        
        log_info(f"Found business: {business.name}")
        
        # Check if Dental Service exists
        dental_service = db.query(Service).filter(
            Service.business_id == business_id,
            Service.name == DENTAL_SERVICE_DATA["name"]
        ).first()
        
        if dental_service:
            # Update existing service
            log_info(f"Updating existing Dental Service (ID: {dental_service.id})")
            dental_service.description = DENTAL_SERVICE_DATA["description"]
            dental_service.duration_minutes = DENTAL_SERVICE_DATA["duration_minutes"]
            dental_service.price = DENTAL_SERVICE_DATA["price"]
            dental_service.is_active = DENTAL_SERVICE_DATA["is_active"]
        else:
            # Create new service
            log_info("Creating new Dental Service")
            dental_service = Service(
                business_id=business_id,
                **DENTAL_SERVICE_DATA
            )
            db.add(dental_service)
        
        db.commit()
        db.refresh(dental_service)
        
        log_info(f"✅ Dental Service initialized successfully!")
        log_info(f"   Name: {dental_service.name}")
        log_info(f"   Duration: {dental_service.duration_minutes} minutes")
        log_info(f"   Description: {dental_service.description[:50]}...")
        
        return True
        
    except Exception as e:
        db.rollback()
        log_error(f"Error initializing Dental Service: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = init_dental_service()
    sys.exit(0 if success else 1)
