"""
routers/stations.py
Station CRUD endpoints.

Endpoints:
  GET  /stations                   — list all stations (Administrator only — B-ACCESS1 Phase 4)
  POST /stations                   — create a station (Administrator only)
  GET  /stations/{id}              — get a single station (all roles, membership enforced)
  GET  /stations/{id}/locations    — list checkable non-vehicle locations (all roles, membership enforced)

B-ACCESS1 Phase 4 changes:
  GET /stations is now Administrator only. All other roles use GET /stations/my
  (in station_members router) which returns only their assigned stations.

  GET /stations/{id} and GET /stations/{id}/locations now enforce station
  membership — a user cannot access a station they are not assigned to.
  Administrators bypass the membership check and can access all stations.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.station import StationCreate, StationRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stations", tags=["stations"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_ADMIN_ONLY      = (ROLE_ADMINISTRATOR,)


def require_station_membership(station_id: int, current_user: CurrentUser, db: Session) -> None:
    """
    Raises HTTP 403 if the current user is not an active member of the station.
    Administrators bypass this check — they have access to all stations.
    """
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
            detail="You are not assigned to this station.",
        )


@router.get(
    "",
    response_model=List[StationRead],
    summary="List all stations (Administrator only)",
    dependencies=[Depends(require_role(*_ADMIN_ONLY))],
)
def list_stations(
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Station]:
    """
    Returns all stations. Administrator only.
    All other roles use GET /stations/my which returns only their assigned stations.
    """
    return db.query(Station).filter(Station.active == active).all()


@router.post(
    "",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a station",
    dependencies=[Depends(require_role(*_ADMIN_ONLY))],
)
def create_station(payload: StationCreate, db: Session = Depends(get_db)) -> Station:
    """Creates a new station. Requires Administrator role."""
    station = Station(
        name=payload.name,
        address=payload.address,
        region=payload.region,
        active=payload.active,
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    logger.info(
        "Station created: station_id=%s name=%r region=%r",
        station.station_id, station.name, station.region,
        extra={
            "action":      "STATION_CREATED",
            "entity_type": "station",
            "entity_id":   str(station.station_id),
        },
    )
    return station


@router.get(
    "/{station_id}/locations",
    response_model=List[InventoryLocationRead],
    summary="List checkable non-vehicle locations at a station",
)
def list_station_locations(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[InventoryLocation]:
    """
    Returns all JUMP_BAG and EQUIPMENT inventory locations at a station.
    Membership enforced — user must be assigned to the station.
    Administrators bypass the membership check.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

    require_station_membership(station_id, current_user, db)

    return (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == station_id,
            InventoryLocation.location_type.in_([
                LocationType.JUMP_BAG,
                LocationType.EQUIPMENT,
            ]),
        )
        .order_by(InventoryLocation.label)
        .all()
    )


@router.get(
    "/{station_id}",
    response_model=StationRead,
    summary="Get a station",
)
def get_station(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
    db: Session = Depends(get_db),
) -> Station:
    """
    Returns a single station by ID.
    Membership enforced — user must be assigned to the station.
    Administrators bypass the membership check.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

    require_station_membership(station_id, current_user, db)

    return station
