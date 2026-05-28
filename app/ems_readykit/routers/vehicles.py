"""
routers/vehicles.py
Vehicle CRUD endpoints.

Refactor (Session B):
- Role constants imported from deps (REF-3)
- HTTP_422_UNPROCESSABLE_CONTENT replaces deprecated constant (REF-7)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_RESPONDER, ROLE_SUPERVISOR
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.vehicle import VehicleCreate, VehicleRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vehicles"])


def _get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    """Local helper — vehicles.py uses this internally only. get_vehicle_or_404
    in deps.py is used by checks.py and repair_requests.py."""
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle


@router.get(
    "/vehicles",
    response_model=List[VehicleRead],
    summary="List all vehicles",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def list_vehicles(
    active: Optional[bool] = Query(
        default=None,
        description="Filter by active status. Omit for all vehicles.",
    ),
    db: Session = Depends(get_db),
) -> List[Vehicle]:
    query = db.query(Vehicle)
    if active is not None:
        query = query.filter(Vehicle.active == active)
    return query.all()


@router.post(
    "/vehicles",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a vehicle",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)) -> Vehicle:
    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {payload.station_id} not found.")

    existing = db.query(Vehicle).filter(Vehicle.vehicle_number == payload.vehicle_number).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Vehicle number '{payload.vehicle_number}' is already in use.")

    vehicle = Vehicle(
        station_id=payload.station_id,
        vehicle_number=payload.vehicle_number,
        vehicle_type=payload.vehicle_type,
        active=payload.active,
    )
    db.add(vehicle)
    db.flush()

    location = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=payload.station_id,
        vehicle_id=vehicle.vehicle_id,
        label=f"{payload.vehicle_number} — {payload.vehicle_type.value}",
    )
    db.add(location)
    db.commit()
    db.refresh(vehicle)
    logger.info(
        "Vehicle created: vehicle_id=%s number=%r type=%s station_id=%s",
        vehicle.vehicle_id, vehicle.vehicle_number,
        vehicle.vehicle_type, vehicle.station_id,
        extra={
            "action":      "VEHICLE_CREATED",
            "entity_type": "vehicle",
            "entity_id":   str(vehicle.vehicle_id),
        },
    )
    return vehicle


@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleRead,
    summary="Get a vehicle",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> Vehicle:
    return _get_vehicle_or_404(vehicle_id, db)


@router.get(
    "/stations/{station_id}/vehicles",
    response_model=List[VehicleRead],
    summary="List vehicles for a station",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_station_vehicles(
    station_id: int,
    active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Vehicle]:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found.")
    query = db.query(Vehicle).filter(Vehicle.station_id == station_id)
    if active is not None:
        query = query.filter(Vehicle.active == active)
    return query.all()
