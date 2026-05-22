"""
routers/stations.py
Station CRUD endpoints.

Endpoints:
  GET  /stations                   — list all stations (ALL roles — Responders need this to start a check)
  POST /stations                   — create a station (Administrator only)
  GET  /stations/{id}              — get a single station (ALL roles)
  GET  /stations/{id}/locations    — list checkable non-vehicle locations at a station (ALL roles)

RBAC note:
  GET /stations and GET /stations/{id}/locations are intentionally open to all
  authenticated roles. A Responder (e.g. Cindy) may work across multiple stations
  and must be able to select their station and see available jump bags / equipment
  when starting a daily inventory check. Station data is non-sensitive operational
  reference data. Write operations (POST) remain Administrator-only.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.station import StationCreate, StationRead

router = APIRouter(prefix="/stations", tags=["stations"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_ADMIN_ONLY      = (ROLE_ADMINISTRATOR,)


@router.get(
    "",
    response_model=List[StationRead],
    summary="List stations",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_stations(
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Station]:
    """
    Returns all active stations.
    Open to all authenticated roles — Responders need this to select
    their station when starting a daily inventory check.
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
    return station


@router.get(
    "/{station_id}/locations",
    response_model=List[InventoryLocationRead],
    summary="List checkable non-vehicle locations at a station",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_station_locations(
    station_id: int,
    db: Session = Depends(get_db),
) -> List[InventoryLocation]:
    """
    Returns all JUMP_BAG and EQUIPMENT inventory locations at a station.

    Excludes VEHICLE locations (returned via /stations/{id}/vehicles) and
    STATION_SUPPLY_ROOM (internal restocking only, not a checkable unit).

    Used by the check wizard Step 1 to show portable bags and equipment
    alongside vehicle cards so responders can select what they are checking.
    All authenticated roles.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

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
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def get_station(station_id: int, db: Session = Depends(get_db)) -> Station:
    """
    Returns a single station by ID.
    Open to all authenticated roles.
    Returns 404 if not found.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return station
