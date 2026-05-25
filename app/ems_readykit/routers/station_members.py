"""
routers/station_members.py
Station membership management endpoints (B-ACCESS1 Phase 2).

Endpoints:
  GET    /stations/my                         — stations the current user is assigned to (all roles)
  GET    /stations/{id}/members               — list members of a station (Supervisor+)
  POST   /stations/{id}/members               — add a user to a station (Supervisor+ with role restrictions)
  PATCH  /stations/{id}/members/{user_id}     — update preferred_name or role (Supervisor+ with role restrictions)
  DELETE /stations/{id}/members/{user_id}     — deactivate a member (soft remove, Supervisor+ with role restrictions)

Role assignment rules (enforced in the router, not just the DB):
  - Administrator role can only be assigned/removed by an Administrator
  - Supervisor role can be assigned/removed by Administrator or Supervisor
  - Responder role can be assigned/removed by Administrator or Supervisor

GET /stations/my:
  Returns only stations where current user has an active membership.
  This is the endpoint the station picker will use once Phase 4 enforcement
  is enabled. Currently registered alongside the existing GET /stations so
  both work in parallel — no breaking change until Phase 4.

IMPORTANT — route ordering:
  /stations/my MUST be registered BEFORE /stations/{station_id} in main.py
  or FastAPI will match "my" as a station_id integer and return a 422.
  This is handled in main.py by registering station_members router first.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.station import StationRead
from ems_readykit.schemas.station_member import (
    StationMemberCreate,
    StationMemberRead,
    StationMemberUpdate,
    VALID_ROLES,
)

router = APIRouter(prefix="/stations", tags=["station-members"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_ADMIN_ONLY      = (ROLE_ADMINISTRATOR,)


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_station_or_404(station_id: int, db: Session) -> Station:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return station


def _get_active_member_or_404(station_id: int, user_id: str, db: Session) -> StationMember:
    member = db.query(StationMember).filter(
        StationMember.station_id == station_id,
        StationMember.user_id    == user_id,
        StationMember.active     == True,
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active membership found for user '{user_id}' at station {station_id}.",
        )
    return member


def _enforce_role_assignment_permission(
    assigning_user: CurrentUser,
    target_role: str,
) -> None:
    """
    Raise 403 if the assigning user does not have permission to assign the
    target role. Administrators can assign any role. Supervisors can only
    assign Responder or Supervisor roles — not Administrator.
    """
    if target_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{target_role}'. Must be one of: {sorted(VALID_ROLES)}",
        )
    if target_role == ROLE_ADMINISTRATOR and not assigning_user.has_role(ROLE_ADMINISTRATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Administrators can assign the Administrator role.",
        )


# ── GET /stations/my ──────────────────────────────────────────────────────────

@router.get(
    "/my",
    response_model=List[StationRead],
    summary="List stations the current user is assigned to",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_my_stations(
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[Station]:
    """
    Returns only the active stations this user is a member of.

    This is the membership-aware replacement for GET /stations (which currently
    returns all stations). The station picker will switch to this endpoint in
    Phase 4 when access enforcement goes live.

    Administrators who have no station_members rows yet (e.g. immediately after
    a fresh deploy before seed runs) receive an empty list — the seed bootstrap
    assignment prevents this in practice.
    """
    members = (
        db.query(StationMember)
        .filter(
            StationMember.user_id == current_user.email,
            StationMember.active  == True,
        )
        .all()
    )
    if not members:
        return []

    station_ids = [m.station_id for m in members]
    return (
        db.query(Station)
        .filter(Station.station_id.in_(station_ids), Station.active == True)
        .order_by(Station.name)
        .all()
    )


# ── GET /stations/{id}/members ────────────────────────────────────────────────

@router.get(
    "/{station_id}/members",
    response_model=List[StationMemberRead],
    summary="List members of a station",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def list_station_members(
    station_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> List[StationMember]:
    """
    Returns all members of a station. Supervisor+ only.
    Pass include_inactive=true to see soft-removed members.
    """
    _get_station_or_404(station_id, db)

    query = db.query(StationMember).filter(
        StationMember.station_id == station_id,
    )
    if not include_inactive:
        query = query.filter(StationMember.active == True)

    return query.order_by(StationMember.role, StationMember.user_id).all()


# ── POST /stations/{id}/members ───────────────────────────────────────────────

@router.post(
    "/{station_id}/members",
    response_model=StationMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to a station",
)
def add_station_member(
    station_id: int,
    payload: StationMemberCreate,
    current_user: CurrentUser = Depends(require_role(*_SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> StationMember:
    """
    Adds a user to a station with the specified role.

    Role assignment rules:
    - Administrator role: Admin only
    - Supervisor role: Admin or Supervisor
    - Responder role: Admin or Supervisor

    If the user was previously a member (active=False), their row is
    reactivated rather than creating a duplicate (respects the unique constraint).
    """
    _get_station_or_404(station_id, db)
    _enforce_role_assignment_permission(current_user, payload.role)

    # Check for existing row (active or inactive) — upsert rather than insert
    existing = db.query(StationMember).filter(
        StationMember.station_id == station_id,
        StationMember.user_id    == payload.user_id,
    ).first()

    if existing:
        if existing.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{payload.user_id}' is already an active member of station {station_id}.",
            )
        # Reactivate soft-deleted member
        existing.active         = True
        existing.role           = payload.role
        existing.preferred_name = payload.preferred_name
        existing.assigned_by    = current_user.email
        db.commit()
        db.refresh(existing)
        return existing

    member = StationMember(
        station_id=station_id,
        user_id=payload.user_id,
        preferred_name=payload.preferred_name,
        role=payload.role,
        assigned_by=current_user.email,
        active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


# ── PATCH /stations/{id}/members/{user_id} ────────────────────────────────────

@router.patch(
    "/{station_id}/members/{user_id}",
    response_model=StationMemberRead,
    summary="Update a station member's role or preferred name",
)
def update_station_member(
    station_id: int,
    user_id: str,
    payload: StationMemberUpdate,
    current_user: CurrentUser = Depends(require_role(*_SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> StationMember:
    """
    Updates preferred_name and/or role for an active member.
    Role change rules are the same as assignment rules.
    """
    _get_station_or_404(station_id, db)
    member = _get_active_member_or_404(station_id, user_id, db)

    if payload.role is not None:
        _enforce_role_assignment_permission(current_user, payload.role)
        member.role = payload.role

    if payload.preferred_name is not None:
        member.preferred_name = payload.preferred_name

    db.commit()
    db.refresh(member)
    return member


# ── DELETE /stations/{id}/members/{user_id} ───────────────────────────────────

@router.delete(
    "/{station_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a user from a station (soft delete)",
)
def remove_station_member(
    station_id: int,
    user_id: str,
    current_user: CurrentUser = Depends(require_role(*_SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> None:
    """
    Soft-removes a user from a station (sets active=False).
    The row is preserved for audit history.

    Removal rules mirror assignment rules:
    - Removing an Administrator: Admin only
    - Removing a Supervisor or Responder: Admin or Supervisor

    A user cannot remove themselves — they must ask another admin/supervisor.
    This prevents accidental self-lockout.
    """
    _get_station_or_404(station_id, db)
    member = _get_active_member_or_404(station_id, user_id, db)

    # Prevent self-removal
    if user_id == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot remove yourself from a station. Ask another Administrator or Supervisor.",
        )

    # Enforce role-based removal permission
    _enforce_role_assignment_permission(current_user, member.role)

    member.active = False
    db.commit()
