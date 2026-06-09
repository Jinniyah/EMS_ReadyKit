"""
routers/station_members.py
Station membership management endpoints (B-ACCESS1 Phase 2).

Refactor (Session B):
- Role constants imported from deps (REF-3)
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.station import StationRead
from ems_readykit.schemas.station_member import (
    VALID_ROLES,
    StationMemberCreate,
    StationMemberRead,
    StationMemberUpdate,
)

router = APIRouter(prefix="/stations", tags=["station-members"])


# ── Helpers ────────────────────────────────────────────────────────────────────

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
        StationMember.active,
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
    if target_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_my_stations(
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[Station]:
    members = (
        db.query(StationMember)
        .filter(
            StationMember.user_id == current_user.email,
            StationMember.active,
        )
        .all()
    )
    if not members:
        return []

    station_ids = [m.station_id for m in members]
    return (
        db.query(Station)
        .filter(Station.station_id.in_(station_ids), Station.active)
        .order_by(Station.name)
        .all()
    )


# ── GET /stations/{id}/members ────────────────────────────────────────────────

@router.get(
    "/{station_id}/members",
    response_model=List[StationMemberRead],
    summary="List members of a station",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def list_station_members(
    station_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> List[StationMember]:
    _get_station_or_404(station_id, db)
    query = db.query(StationMember).filter(StationMember.station_id == station_id)
    if not include_inactive:
        query = query.filter(StationMember.active)
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
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> StationMember:
    _get_station_or_404(station_id, db)
    _enforce_role_assignment_permission(current_user, payload.role)

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
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> StationMember:
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
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> Response:
    _get_station_or_404(station_id, db)
    member = _get_active_member_or_404(station_id, user_id, db)

    if user_id == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot remove yourself from a station. Ask another Administrator or Supervisor.",
        )

    _enforce_role_assignment_permission(current_user, member.role)

    member.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
