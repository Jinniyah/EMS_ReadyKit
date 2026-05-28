"""
routers/stations.py
Station CRUD endpoints.

Refactor (Session B):
- Role constants imported from deps (REF-3)
- require_station_membership moved to deps (REF-4); imported from there
- HTTP_422_UNPROCESSABLE_CONTENT replaces deprecated constant (REF-7)
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


@router.get(
    "",
    response_model=List[StationRead],
    summary="List all stations (Administrator only)",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def list_stations(
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Station]:
    """Returns all stations. Administrator only."""
    return db.query(Station).filter(Station.active == active).all()


@router.post(
    "",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a station",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
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
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[InventoryLocation]:
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
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> Station:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

    require_station_membership(station_id, current_user, db)

    return station
