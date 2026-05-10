"""
routers/stations.py
Station CRUD endpoints.

Endpoints:
  GET  /stations          — list all stations (active by default)
  POST /stations          — create a station
  GET  /stations/{id}     — get a single station

Design decisions:
- List endpoint filters active=True by default. Pass ?active=false to include
  inactive stations. This keeps operational views clean without losing history.
- No DELETE endpoint in Phase 2 — stations are deactivated (active=False),
  never deleted. Deletion would orphan vehicles, locations, and audit history.
- No PUT/PATCH in Phase 2 — updates are Phase 3 (RBAC-gated).
- 404 is returned for any station that does not exist, regardless of active status,
  to avoid leaking information about inactive records to unauthorized callers.
  Phase 3 will tighten this with role-based scoping.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.station import Station
from ems_readykit.schemas.station import StationCreate, StationRead

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=List[StationRead], summary="List stations")
def list_stations(
    active: bool = Query(default=True, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> List[Station]:
    """
    Returns all stations matching the active filter.
    Defaults to active=True for operational views.
    """
    return db.query(Station).filter(Station.active == active).all()


@router.post(
    "",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a station",
)
def create_station(payload: StationCreate, db: Session = Depends(get_db)) -> Station:
    """
    Creates a new station.
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


@router.get("/{station_id}", response_model=StationRead, summary="Get a station")
def get_station(station_id: int, db: Session = Depends(get_db)) -> Station:
    """
    Returns a single station by ID.
    Returns 404 if not found.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return station
