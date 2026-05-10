"""
routers/vehicles.py
Vehicle CRUD endpoints.

Endpoints:
  GET  /vehicles                    — list vehicles (filterable by station/active)
  POST /vehicles                    — create a vehicle
  GET  /vehicles/{id}               — get a single vehicle
  GET  /stations/{id}/vehicles      — list vehicles for a specific station

Design decisions:
- Creating a vehicle automatically creates its InventoryLocation. A vehicle
  without a location is operationally invalid — the location is created in
  the same transaction to guarantee atomicity.
- station_id is validated on create — a vehicle cannot be created for a
  non-existent station. Returns 404 if the station is not found.
- No DELETE endpoint — vehicles are deactivated, never deleted, to preserve
  audit history and check records.
- The station-scoped list endpoint (/stations/{id}/vehicles) is provided for
  supervisor dashboards that need to see compliance by station.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.schemas.vehicle import VehicleCreate, VehicleRead

router = APIRouter(tags=["vehicles"])


def _get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    """Shared lookup used by multiple endpoints."""
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle


@router.get("/vehicles", response_model=List[VehicleRead], summary="List vehicles")
def list_vehicles(
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Vehicle]:
    """Returns all vehicles matching the active filter."""
    return db.query(Vehicle).filter(Vehicle.active == active).all()


@router.post(
    "/vehicles",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a vehicle",
)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)) -> Vehicle:
    """
    Creates a vehicle and its corresponding InventoryLocation in one transaction.
    Returns 404 if the referenced station does not exist.
    Returns 409 if the vehicle_number is already in use.
    """
    # Validate the station exists before creating the vehicle
    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )

    # Check vehicle_number uniqueness explicitly for a clear error message.
    # The DB unique constraint would catch this too, but the error would be
    # a generic IntegrityError rather than a meaningful 409 response.
    existing = (
        db.query(Vehicle).filter(Vehicle.vehicle_number == payload.vehicle_number).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle number '{payload.vehicle_number}' is already in use.",
        )

    vehicle = Vehicle(
        station_id=payload.station_id,
        vehicle_number=payload.vehicle_number,
        vehicle_type=payload.vehicle_type,
        active=payload.active,
    )
    db.add(vehicle)
    db.flush()  # flush to get vehicle_id before creating the location

    # Every vehicle gets exactly one inventory location.
    # Created atomically with the vehicle — no orphaned vehicles without locations.
    location = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=payload.station_id,
        vehicle_id=vehicle.vehicle_id,
        label=f"{payload.vehicle_number} — {payload.vehicle_type.value}",
    )
    db.add(location)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/vehicles/{vehicle_id}", response_model=VehicleRead, summary="Get a vehicle")
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> Vehicle:
    """Returns a single vehicle by ID. Returns 404 if not found."""
    return _get_vehicle_or_404(vehicle_id, db)


@router.get(
    "/stations/{station_id}/vehicles",
    response_model=List[VehicleRead],
    summary="List vehicles for a station",
)
def list_station_vehicles(
    station_id: int,
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Vehicle]:
    """
    Returns all vehicles assigned to a specific station.
    Used by supervisor compliance dashboards.
    Returns 404 if the station does not exist.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return (
        db.query(Vehicle)
        .filter(Vehicle.station_id == station_id, Vehicle.active == active)
        .all()
    )
