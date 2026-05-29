"""
routers/deps.py
Shared FastAPI dependencies and constants used across all routers.

## Role constants
ALL_ROLES, SUPERVISOR_PLUS, and ADMIN_ONLY are defined here as the single
source of truth. Previously each router defined its own local _ALL_ROLES /
_SUPERVISOR_PLUS tuple — 9 separate definitions that could drift when a new
role is added. Import from here instead:

    from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, ADMIN_ONLY

## Shared helpers
get_vehicle_or_404         — query vehicle by ID or raise 404
require_station_membership — raise 403 if user is not an active member of a
    station. The 403 message is written for frontline EMS users, not developers.
    Administrators bypass this check entirely.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
    resolve_current_user,
)
from ems_readykit.core.database import get_db

__all__ = [
    "get_db",
    "get_current_user",
    "require_role",
    "ALL_ROLES",
    "SUPERVISOR_PLUS",
    "ADMIN_ONLY",
    "get_vehicle_or_404",
    "require_station_membership",
]

# ── Role constant tuples ──────────────────────────────────────────────────────

ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
ADMIN_ONLY      = (ROLE_ADMINISTRATOR,)

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
        @router.get("/stations", dependencies=[Depends(require_role(*ADMIN_ONLY))])

    Usage (access control + user object in handler):
        @router.post("/checks/daily")
        def create_check(..., current_user: CurrentUser = Depends(require_role(*ALL_ROLES))):
            ...
    """
    def _check(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You don't have permission to do that. "
                    "If you think this is wrong, contact your supervisor."
                ),
            )
        return current_user

    return _check


# ── Shared model helpers ──────────────────────────────────────────────────────

def get_vehicle_or_404(vehicle_id: int, db: Session) -> "Vehicle":  # noqa: F821
    """Query a vehicle by ID or raise HTTP 404."""
    from ems_readykit.models.vehicle import Vehicle
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle


def require_station_membership(
    station_id: int,
    current_user: CurrentUser,
    db: Session,
) -> None:
    """
    Raise HTTP 403 if the current user is not an active member of the station.
    Administrators bypass this check — they have access to all stations.

    The error message is written for frontline EMS users who may be tired
    or stressed. It tells them what's wrong and what to do about it, rather
    than giving a technical access-denied message.

    Note: StationMember.user_id is keyed on email (preferred_username from
    the JWT), not the stable OID. This is intentional — see station_members.py
    for the rationale.
    """
    from ems_readykit.models.station_member import StationMember

    if current_user.has_role(ROLE_ADMINISTRATOR):
        return

    member = db.query(StationMember).filter(
        StationMember.station_id == station_id,
        StationMember.user_id    == current_user.email,
        StationMember.active     == True,
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You're not listed as a member of this station. "
                "If you're supposed to have access, ask your supervisor "
                "to add you in Station Administration."
            ),
        )
