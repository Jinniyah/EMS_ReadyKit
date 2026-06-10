"""
routers/vehicles.py
Vehicle CRUD endpoints.

Session C (ACC-B8): Station membership enforced on vehicle endpoints.
  - GET /stations/{id}/vehicles — user must be a member of station_id
  - GET /vehicles/{id}          — user must be a member of vehicle.station_id
  - GET /vehicles               — filtered to user's assigned stations (Supervisor+)
                                   Administrator sees all
  - POST /vehicles              — user must be a member of payload.station_id (Supervisor+)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import (
    ALL_ROLES,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.vehicle import VehicleCreate, VehicleRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vehicles"])


def _get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle


def _station_ids_for_user(
    current_user: CurrentUser, db: Session
) -> Optional[List[int]]:
    """
    Returns the list of station IDs the current user is a member of.
    Returns None for Administrators (they see everything).
    """
    if current_user.has_role(ROLE_ADMINISTRATOR):
        return None
    members = (
        db.query(StationMember)
        .filter(
            StationMember.user_id == current_user.email,
            StationMember.active,
        )
        .all()
    )
    return [m.station_id for m in members]


@router.get(
    "/vehicles",
    response_model=List[VehicleRead],
    summary="List vehicles (scoped to user's stations for non-Administrators)",
)
def list_vehicles(
    active: Optional[bool] = Query(
        default=None,
        description="Filter by active status. Omit for all vehicles.",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[Vehicle]:
    """
    Supervisors see vehicles for their assigned stations only.
    Administrators see all vehicles.
    """
    query = db.query(Vehicle)

    station_ids = _station_ids_for_user(current_user, db)
    if station_ids is not None:
        query = query.filter(Vehicle.station_id.in_(station_ids))

    if active is not None:
        query = query.filter(Vehicle.active == active)

    return query.all()


@router.post(
    "/vehicles",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a vehicle",
)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Vehicle:
    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=404, detail=f"Station {payload.station_id} not found."
        )

    # ACC-B8: only create vehicles at stations you're a member of
    require_station_membership(payload.station_id, current_user, db)

    existing = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_number == payload.vehicle_number)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Vehicle number '{payload.vehicle_number}' is already in use.",
        )

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
        vehicle.vehicle_id,
        vehicle.vehicle_number,
        vehicle.vehicle_type,
        vehicle.station_id,
        extra={
            "action": "VEHICLE_CREATED",
            "entity_type": "vehicle",
            "entity_id": str(vehicle.vehicle_id),
        },
    )
    return vehicle


@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleRead,
    summary="Get a vehicle",
)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> Vehicle:
    vehicle = _get_vehicle_or_404(vehicle_id, db)
    # ACC-B8: enforce membership via vehicle's station
    require_station_membership(vehicle.station_id, current_user, db)
    return vehicle


@router.get(
    "/stations/{station_id}/vehicles",
    response_model=List[VehicleRead],
    summary="List vehicles for a station",
)
def list_station_vehicles(
    station_id: int,
    active: Optional[bool] = Query(
        default=None,
        description=(
            "Filter by active status. Omit for all vehicles (V&E Status screen). "
            "Pass active=true for check wizard (active only)."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[Vehicle]:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found.")

    # ACC-B8: station membership enforcement
    require_station_membership(station_id, current_user, db)

    query = db.query(Vehicle).filter(Vehicle.station_id == station_id)
    if active is not None:
        query = query.filter(Vehicle.active == active)
    return query.all()
