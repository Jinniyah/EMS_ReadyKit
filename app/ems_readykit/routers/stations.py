"""
routers/stations.py
Station CRUD endpoints.

Session C (ACC-B8): Station membership enforced on station endpoints.

Post-Block-6 additions:
  PATCH /stations/{id}  — Edit station (name, address, region, call_sign,
                          primary_color). Administrator only.
  DELETE /stations/{id} — Soft-deactivate station (sets active=False).
                          Administrator only.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.routers.deps import (
    ALL_ROLES,
    ADMIN_ONLY,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.station import StationCreate, StationRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stations", tags=["stations"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_station_or_404(station_id: int, db: Session) -> Station:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return station


# ── GET /stations — Admin list ────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[StationRead],
    summary="List all stations (Administrator only)",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def list_stations(
    active: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> List[Station]:
    return db.query(Station).filter(Station.active == active).all()


# ── GET /stations/my — member-scoped list ─────────────────────────────────────

@router.get(
    "/my",
    response_model=List[StationRead],
    summary="List stations the current user is assigned to",
)
def list_my_stations(
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[Station]:
    member_rows = (
        db.query(StationMember)
        .filter(
            StationMember.user_id == current_user.email,
            StationMember.active  == True,
        )
        .all()
    )
    if not member_rows:
        return []
    station_ids = [m.station_id for m in member_rows]
    return (
        db.query(Station)
        .filter(
            Station.station_id.in_(station_ids),
            Station.active == True,
        )
        .order_by(Station.name)
        .all()
    )


# ── POST /stations — create ────────────────────────────────────────────────────

@router.post(
    "",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a station (Administrator only)",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def create_station(payload: StationCreate, db: Session = Depends(get_db)) -> Station:
    station = Station(
        name=payload.name, address=payload.address, region=payload.region,
        active=payload.active, call_sign=payload.call_sign, primary_color=payload.primary_color,
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    logger.info("Station created: station_id=%s name=%r", station.station_id, station.name,
        extra={"action": "STATION_CREATED", "entity_type": "station", "entity_id": str(station.station_id)})
    return station


# ── PATCH /stations/{id} — edit ────────────────────────────────────────────────

@router.patch(
    "/{station_id}",
    response_model=StationRead,
    summary="Edit a station — Administrator only",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def update_station(
    station_id: int,
    payload: StationCreate,
    db: Session = Depends(get_db),
) -> Station:
    """
    Edit station fields: name, address, region, call_sign, primary_color, active.
    Administrator only. The station_id never changes.
    """
    station = _get_station_or_404(station_id, db)
    station.name          = payload.name
    station.address       = payload.address
    station.region        = payload.region
    station.call_sign     = payload.call_sign
    station.primary_color = payload.primary_color
    station.active        = payload.active
    db.commit()
    db.refresh(station)
    logger.info("Station updated: station_id=%s name=%r", station.station_id, station.name,
        extra={"action": "STATION_UPDATED", "entity_type": "station", "entity_id": str(station_id)})
    return station


# ── DELETE /stations/{id} — soft deactivate ────────────────────────────────────

@router.delete(
    "/{station_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a station — Administrator only",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def deactivate_station(
    station_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """
    Soft-deactivate: sets active=False. The station and all its data are
    retained for audit history but hidden from the UI and membership queries.
    """
    station = _get_station_or_404(station_id, db)
    if not station.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Station '{station.name}' is already inactive.",
        )
    station.active = False
    db.commit()
    logger.info("Station deactivated: station_id=%s name=%r", station_id, station.name,
        extra={"action": "STATION_DEACTIVATED", "entity_type": "station", "entity_id": str(station_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── GET /stations/{station_id}/locations ──────────────────────────────────────

@router.get(
    "/{station_id}/locations",
    response_model=List[InventoryLocationRead],
    summary="List checkable non-vehicle locations at a station",
)
def list_station_locations(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[InventoryLocation]:
    station = _get_station_or_404(station_id, db)
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


# ── GET /stations/{station_id}/supply-room — SUPPLY-B3 ───────────────────────

@router.get(
    "/{station_id}/supply-room",
    response_model=InventoryLocationRead,
    summary="Get the supply room for a station (SUPPLY-B3)",
)
def get_supply_room(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> InventoryLocation:
    """
    Returns the STATION_SUPPLY_ROOM inventory location for this station.
    Membership enforced. Returns 404 if no supply room has been created yet.
    """
    _get_station_or_404(station_id, db)
    require_station_membership(station_id, current_user, db)
    location = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id   == station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} does not have a supply room configured.",
        )
    return location


# ── GET /stations/{station_id} ─────────────────────────────────────────────────

@router.get(
    "/{station_id}",
    response_model=StationRead,
    summary="Get a station",
)
def get_station(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> Station:
    station = _get_station_or_404(station_id, db)
    require_station_membership(station_id, current_user, db)
    return station
