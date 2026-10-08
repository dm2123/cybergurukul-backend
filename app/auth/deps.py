"""Auth dependencies: current user resolution and RBAC role guards."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.database import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = ["student", "instructor", "certificate_manager", "workshop_manager", "admin", "super_admin"]


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = (await db.execute(select(User).where(User.id == int(payload["sub"])))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_roles(*roles: str):
    """Dependency factory: allow only users whose role is in `roles` (or higher in hierarchy)."""

    async def guard(user: User = Depends(get_current_user)) -> User:
        allowed = set(roles)
        # super_admin bypasses all guards
        if user.role == "super_admin":
            return user
        user_rank = ROLE_HIERARCHY.index(user.role) if user.role in ROLE_HIERARCHY else -1
        for r in allowed:
            need = ROLE_HIERARCHY.index(r) if r in ROLE_HIERARCHY else 999
            if user_rank >= need:
                return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return guard


require_admin = require_roles("admin")
require_staff = require_roles("workshop_manager")
