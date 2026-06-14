"""
routers/admin_vehicles.py
Vehicle admin endpoints.

Routes (all prefixed /admin via router):
  PATCH /admin/vehicles/{id}/color    Set vehicle color (Supervisor+)
  PATCH /admin/vehicles/{id}/details  Update vehicle number and type (Admin only)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import ADMIN_ONLY, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.vehicle import VehicleColorUpdate, VehicleDetailsUpdate
from ems_readykit.schemas.vehicle import VehicleRead as VehicleReadSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.patch(
    "/vehicles/{vehicle_id}/color",
    response_model=VehicleReadSchema,
    summary="Set or clear a vehicle's color (ADMIN-UX1-V, Supervisor+)",
)
def update_vehicle_color(
    vehicle_id: int,
    payload: VehicleColorUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    vehicle.vehicle_color = payload.vehicle_color
    db.commit()
    db.refresh(vehicle)
    logger.info(
        "Vehicle color updated: vehicle_id=%s color=%r",
        vehicle_id,
        payload.vehicle_color,
        extra={
            "action": "VEHICLE_COLOR_UPDATED",
            "entity_type": "vehicle",
            "entity_id": str(vehicle_id),
        },
    )
    return vehicle


@router.patch(
    "/vehicles/{vehicle_id}/details",
    response_model=VehicleReadSchema,
    summary="Update vehicle number and type -- Admin only",
)
def update_vehicle_details(
    vehicle_id: int,
    payload: VehicleDetailsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*ADMIN_ONLY)),
) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    new_number = payload.vehicle_number.strip().upper()
    if new_number != vehicle.vehicle_number:
        dup = (
            db.query(Vehicle)
            .filter(
                Vehicle.station_id == vehicle.station_id,
                Vehicle.vehicle_number == new_number,
                Vehicle.vehicle_id != vehicle_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle number '{new_number}' is already in use at this station.",
            )
    vehicle.vehicle_number = new_number
    vehicle.vehicle_type = payload.vehicle_type
    db.commit()
    db.refresh(vehicle)
    logger.info(
        "Vehicle details updated: vehicle_id=%s number=%r type=%r",
        vehicle_id,
        vehicle.vehicle_number,
        vehicle.vehicle_type.value,
        extra={
            "action": "VEHICLE_DETAILS_UPDATED",
            "entity_type": "vehicle",
            "entity_id": str(vehicle_id),
        },
    )
    return vehicle
