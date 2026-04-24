"""
Auth Routes — CareOps

Architecture:
  POST /auth/register  → Business Admin ONLY. Creates Business + Admin User atomically.
  POST /auth/login     → Admin login. Returns JWT with role + business_id.
  GET  /auth/me        → Returns current user profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.business import Business
from app.models.user import User, UserRole
from app.schemas.user_schema import AdminRegisterRequest, UserLogin, TokenResponse, UserResponse
from app.dependencies.auth_dependency import get_current_user
from app.core.logger import log_info, log_warning

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _build_jwt(user: User) -> str:
    """
    Build a JWT embedding user_id, role and business_id.

    This means all route dependencies can extract the tenant
    without a second database query.
    """
    return create_access_token(data={
        "sub": str(user.id),
        "role": user.role.value,
        "business_id": str(user.business_id),
    })


# ── Register (Admin only) ──────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_admin(payload: AdminRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new Business Admin.

    - Creates a Business record with the given business_name.
    - Creates a User with role='admin' linked to that Business.
    - Returns a JWT token (includes role + business_id).
    """
    log_info(f"[AUTH] Admin registration attempt: {payload.email}")

    if db.query(User).filter(User.email == payload.email).first():
        log_warning(f"[AUTH] Registration failed — email already exists: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Atomically create Business + Admin user
    business = Business(name=payload.business_name)
    db.add(business)
    db.flush()  # get business.id without full commit

    admin = User(
        business_id=business.id,
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    log_info(f"[AUTH] Admin registered: user_id={admin.id}, business_id={business.id}")

    return TokenResponse(
        access_token=_build_jwt(admin),
        user=UserResponse.model_validate(admin)
    )


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Admin login.

    Returns a JWT that embeds:
      - sub: user_id
      - role: "admin"
      - business_id: the tenant ID

    All protected routes use this JWT to scope data to the correct business.
    """
    log_info(f"[AUTH] Login attempt: {credentials.email}")

    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        log_warning(f"[AUTH] Login failed: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    log_info(f"[AUTH] Login successful: user_id={user.id}, role={user.role}, business_id={user.business_id}")

    return TokenResponse(
        access_token=_build_jwt(user),
        user=UserResponse.model_validate(user)
    )


# ── Current User ───────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated admin's profile."""
    return UserResponse.model_validate(current_user)
