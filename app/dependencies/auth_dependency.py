from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.core.logger import log_info, log_warning

# HTTP Bearer token scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: decode JWT and return the authenticated User.

    The JWT must contain:
      - sub (user_id as string)
      - role ("admin" or "user")
      - business_id (as string)

    Raises 401 if token is missing, invalid, or user not found.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")

    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency: require the current user to have the 'admin' role.

    Use this to protect admin-only routes:
      - Inventory management (create / update / delete)
      - Lead management (delete)
      - Business settings changes
      - Form template management

    Raises 403 if the authenticated user is not an admin.
    """
    log_info(
        f"[Auth] require_admin check: user_id={current_user.id}, "
        f"role={current_user.role!r}, business_id={current_user.business_id}, "
        f"match={current_user.role == UserRole.ADMIN}"
    )
    if current_user.role != UserRole.ADMIN:
        log_warning(
            f"[Auth] 403 ADMIN REQUIRED — user_id={current_user.id} "
            f"has role={current_user.role!r}, expected {UserRole.ADMIN!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Admin access required. "
                f"Your account has role='{current_user.role.value}' — only 'admin' can perform this action."
            )
        )
    return current_user
