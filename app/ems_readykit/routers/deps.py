"""
routers/deps.py
Shared FastAPI dependencies used across all routers.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ems_readykit.core.auth import CurrentUser, resolve_current_user
from ems_readykit.core.database import get_db

__all__ = ["get_db", "get_current_user", "require_role"]

# ── Auth bearer scheme ────────────────────────────────────────────────────────

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """
    FastAPI dependency — validates the Bearer token and returns a CurrentUser.
    Raises HTTP 401 if the token is missing or invalid.
    """
    return resolve_current_user(credentials.credentials)


# ── RBAC helper ───────────────────────────────────────────────────────────────


def require_role(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    """
    Dependency factory — returns a FastAPI dependency that enforces role membership.

    Usage (access control only):
        @router.get("/stations", dependencies=[Depends(require_role("Supervisor", "Administrator"))])

    Usage (access control + user object in handler):
        @router.post("/checks/daily")
        def create_check(..., current_user: CurrentUser = Depends(require_role("Responder", "Supervisor", "Administrator"))):
            ...
    """
    def _check(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {list(roles)}",
            )
        return current_user

    return _check
