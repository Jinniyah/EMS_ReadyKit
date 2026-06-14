"""
routers/admin_stations.py
Station and location admin endpoints.

Routes (all prefixed /admin via router):
  POST  /admin/stations              Create station (Admin only)
  PATCH /admin/locations/{id}        Rename inventory location label (Admin only)
  GET   /admin/retired               List retired vehicles/locations/stations (Admin only)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import (
    ADMIN_ONLY,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.station import StationCreate, StationRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# -- ADMIN-B15: Create station -------------------------------------------------


@router.post(
    "/stations",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new station -- Administrator only (ADMIN-B15)",
)
def create_station(
    payload: StationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> Station:
    """
    Creates a new station and immediately adds the creating administrator as
    an active StationMember with role 'Administrator', and auto-creates the
    station supply room with 4 default shelf compartments.
    """
    station = Station(
        name=payload.name,
        address=payload.address,
        region=payload.region,
        active=payload.active,
        call_sign=payload.call_sign,
        primary_color=payload.primary_color,
    )
    db.add(station)
    db.flush()

    member = StationMember(
        station_id=station.station_id,
        user_id=current_user.email,
        role=ROLE_ADMINISTRATOR,
        assigned_by=current_user.email,
        active=True,
    )
    db.add(member)

    supply_room = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label=f"{station.name} Supply Room",
    )
    db.add(supply_room)
    db.flush()

    _DEFAULT_SUPPLY_COMPARTMENTS = [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf -- airway & PPE supplies", 1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf -- dressings & bandages", 2),
        (
            "Cab 2 - Shelf 1",
            "Cabinet 2, top shelf -- medications & controlled items",
            3,
        ),
        ("Cab 2 - Shelf 2", "Cabinet 2, bottom shelf -- equipment & restock items", 4),
    ]
    for comp_name, comp_desc, sort_order in _DEFAULT_SUPPLY_COMPARTMENTS:
        db.add(
            Compartment(
                location_id=supply_room.location_id,
                name=comp_name,
                location_descriptor=comp_desc,
                sort_order=sort_order,
                active=True,
            )
        )

    db.commit()
    db.refresh(station)
    logger.info(
        "Station created: station_id=%s name=%r; auto-added member=%r",
        station.station_id,
        station.name,
        current_user.email,
        extra={
            "action": "STATION_CREATED",
            "entity_type": "station",
            "entity_id": str(station.station_id),
        },
    )
    return station


# -- SS-B1: Rename an inventory location ---------------------------------------


class _LocationLabelPatch(BaseModel):
    label: str = Field(..., min_length=1, max_length=150)


@router.patch(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Rename an inventory location label (SS-B1) -- Admin only",
)
def rename_location(
    location_id: int,
    payload: _LocationLabelPatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> InventoryLocation:
    loc = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.location_id == location_id)
        .first()
    )
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {location_id} not found.",
        )
    require_station_membership(loc.station_id, current_user, db)
    loc.label = payload.label.strip()
    db.commit()
    db.refresh(loc)
    write_audit_event(
        db,
        actor=current_user.email or current_user.name,
        action="LOCATION_RENAMED",
        entity_type="inventory_location",
        entity_id=str(location_id),
        metadata={"new_label": loc.label},
    )
    return loc


# -- RET-B4: List retired objects ----------------------------------------------


class _RetiredItem(BaseModel):
    type: str
    id: int
    name: str
    retired_at: datetime
    retired_by: Optional[str]
    retirement_reason: Optional[str]
    station_id: Optional[int]


@router.get(
    "/retired",
    response_model=List[_RetiredItem],
    summary="List retired vehicles, locations, or stations (RET-B4) -- Admin only",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def list_retired(
    type: str = Query(
        ...,
        description="One of: vehicles, locations, stations",
        pattern="^(vehicles|locations|stations)$",
    ),
    station_id: Optional[int] = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> List[_RetiredItem]:
    result: List[_RetiredItem] = []

    if type == "vehicles":
        query = db.query(Vehicle).filter(Vehicle.retired_at.isnot(None))
        if station_id:
            query = query.filter(Vehicle.station_id == station_id)
        for v in query.order_by(Vehicle.retired_at.desc()).all():
            result.append(
                _RetiredItem(
                    type="vehicle",
                    id=v.vehicle_id,
                    name=v.vehicle_number,
                    retired_at=v.retired_at,
                    retired_by=v.retired_by,
                    retirement_reason=v.retirement_reason,
                    station_id=v.station_id,
                )
            )

    elif type == "locations":
        query = db.query(InventoryLocation).filter(
            InventoryLocation.retired_at.isnot(None)
        )
        if station_id:
            query = query.filter(InventoryLocation.station_id == station_id)
        for loc in query.order_by(InventoryLocation.retired_at.desc()).all():
            result.append(
                _RetiredItem(
                    type="location",
                    id=loc.location_id,
                    name=loc.label,
                    retired_at=loc.retired_at,
                    retired_by=loc.retired_by,
                    retirement_reason=loc.retirement_reason,
                    station_id=loc.station_id,
                )
            )

    elif type == "stations":
        query = db.query(Station).filter(Station.retired_at.isnot(None))
        if station_id:
            query = query.filter(Station.station_id == station_id)
        for s in query.order_by(Station.retired_at.desc()).all():
            result.append(
                _RetiredItem(
                    type="station",
                    id=s.station_id,
                    name=s.name,
                    retired_at=s.retired_at,
                    retired_by=s.retired_by,
                    retirement_reason=s.retirement_reason,
                    station_id=s.station_id,
                )
            )

    return result
