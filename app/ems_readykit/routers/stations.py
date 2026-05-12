"""
routers/stations.py
Station CRUD endpoints.

Endpoints:
  GET  /stations          — list all stations (Supervisor, Administrator)
  POST /stations          — create a station (Administrator only)
  GET  /stations/{id}     — get a single station (Supervisor, Administrator)
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_SUPERVISOR
from ems_readykit.core.database import get_db
from ems_readykit.models.station import Station
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.station import StationCreate, StationRead

router = APIRouter(prefix="/stations", tags=["stations"])

_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_ADMIN_ONLY      = (ROLE_ADMINISTRATOR,)


@router.get(
    "",
    response_model=List[StationRead],
    summary="List stations",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def list_stations(
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Station]:
    """
    Returns all stations matching the active filter.
    Defaults to active=True for operational views.
    Requires Supervisor or Administrator role.
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
    """
    Creates a new station. Requires Administrator role.
    Returns 201 Created with the persisted station on success.
    """
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
    "/{station_id}",
    response_model=StationRead,
    summary="Get a station",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_station(station_id: int, db: Session = Depends(get_db)) -> Station:
    """
    Returns a single station by ID.
    Returns 404 if not found. Requires Supervisor or Administrator role.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return station
