from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from sqlalchemy import text
from app.core.config import settings
from app.core.logger import log_info, log_error
from app.core.database import SessionLocal
from app.services.automation_service import AutomationService
from app.routes import auth, contacts, bookings, inventory, alerts, messages, dashboard, conversations, leads, forms, business, services

# Create FastAPI application
app = FastAPI(
    title="CareOps API",
    description="Production-ready backend for unified business operations platform",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Includes CORS headers so that 500 responses are visible to the browser
    (without these, the browser sees a CORS error instead of the real 500).
    """
    log_error(f"Unhandled exception: {str(exc)}")

    origin = request.headers.get("origin", "")
    headers = {}
    if origin in settings.cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers=headers,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "detail": str(exc) if not settings.is_production else "An error occurred"
        }
    )

# Health Check Endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# Startup Event
@app.on_event("startup")
async def startup_event():
    log_info(f"[STARTUP] Starting CareOps API in {settings.ENVIRONMENT} mode")

    # Backward-compatible enum repair:
    # some databases were initialized with `formstatus` values from form templates only.
    # bookings also use this enum type for `bookings.form_status`, so ensure required labels exist.
    db_session = SessionLocal()
    try:
        db_session.execute(text("ALTER TYPE formstatus ADD VALUE IF NOT EXISTS 'PENDING'"))
        db_session.execute(text("ALTER TYPE formstatus ADD VALUE IF NOT EXISTS 'COMPLETED'"))
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        log_error(f"[STARTUP] Failed to ensure formstatus enum values: {str(e)}")
    finally:
        db_session.close()
    
    if not settings.is_production:
        log_info("[STARTUP] Initializing database tables (development mode)")
        from app.core.database import init_db
        init_db()
    
    # Start background automation worker
    log_info("[STARTUP] Starting background automation worker")
    asyncio.create_task(automation_worker())
    
    log_info("[STARTUP] Application started successfully")


async def automation_worker():
    log_info("[AUTOMATION_WORKER] Background worker started")
    
    await asyncio.sleep(5)  # Wait 5 seconds before first run
    
    while True:
        try:
            db_session = SessionLocal()
            try:
                automation_service = AutomationService(db_session)
                
                # Run all automation methods
                log_info("[AUTOMATION_WORKER] Running automation checks...")
                
                # Send pending reminders
                try:
                    automation_service.send_pending_reminders()
                    log_info("[AUTOMATION_WORKER] Sent pending reminders")
                except Exception as e:
                    log_error(f"[AUTOMATION_WORKER] Error sending reminders: {str(e)}")
                
                # Check low inventory
                try:
                    automation_service.check_low_inventory_alerts()
                    log_info("[AUTOMATION_WORKER] Checked low inventory alerts")
                except Exception as e:
                    log_error(f"[AUTOMATION_WORKER] Error checking inventory: {str(e)}")
                
                # Close inactive conversations
                try:
                    automation_service.close_inactive_conversations()
                    log_info("[AUTOMATION_WORKER] Checked inactive conversations")
                except Exception as e:
                    log_error(f"[AUTOMATION_WORKER] Error closing conversations: {str(e)}")
                
                log_info("[AUTOMATION_WORKER] Automation checks completed")
            finally:
                db_session.close()
        except Exception as e:
            log_error(f"[AUTOMATION_WORKER] Unexpected error: {str(e)}")
        
        # Wait 1 hour before next run
        await asyncio.sleep(3600)


# Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    log_info("[SHUTDOWN] Shutting down CareOps API")


# Register Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(contacts.router)
app.include_router(bookings.router)
app.include_router(inventory.router)
app.include_router(alerts.router)
app.include_router(messages.router)
app.include_router(conversations.router)
app.include_router(leads.router)
app.include_router(forms.router)
app.include_router(services.router)
app.include_router(services.public_router)
app.include_router(business.router)

# Root Endpoint
@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information."""
    return {
        "message": "CareOps API",
        "version": "1.0.0",
        "docs": "/docs" if not settings.is_production else "disabled",
        "health": "/health"
    }
