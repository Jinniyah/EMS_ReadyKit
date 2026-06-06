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
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.stock_lot import StockLot
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


# ── POST /stations/{station_id}/supply-room — create supply room ─────────────

@router.post(
    "/{station_id}/supply-room",
    response_model=InventoryLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create supply room for a station (get-or-create)",
)
def create_supply_room(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> InventoryLocation:
    """
    Creates the STATION_SUPPLY_ROOM inventory location for this station if it
    does not already exist, along with 4 default shelf compartments.
    Returns the existing location unchanged if one already exists.
    """
    _get_station_or_404(station_id, db)
    require_station_membership(station_id, current_user, db)

    location = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id    == station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if location:
        return location

    location = InventoryLocation(
        station_id    = station_id,
        vehicle_id    = None,
        location_type = LocationType.STATION_SUPPLY_ROOM,
        label         = "Station Supply Room",
    )
    db.add(location)
    db.flush()

    has_compartments = (
        db.query(Compartment)
        .filter(Compartment.location_id == location.location_id)
        .count()
    ) > 0

    if not has_compartments:
        for sort_order, name in enumerate(["Shelf 1", "Shelf 2", "Shelf 3", "Shelf 4"], start=1):
            db.add(Compartment(
                location_id = location.location_id,
                name        = name,
                sort_order  = sort_order,
                active      = True,
            ))

    db.commit()
    db.refresh(location)

    logger.info(
        "Supply room created for station %s by %s",
        station_id, current_user.email,
    )
    return location


# ── GET /stations/{station_id}/expiring-soon — SUP-F3 ───────────────────────

class _ExpiringLot(BaseModel):
    lot_id: int
    item_name: str
    lot_number: Optional[str]
    expiration_date: date
    days_until_expiry: int
    quantity: int

class _ExpiringGroup(BaseModel):
    location_id: int
    location_label: str
    vehicle_number: Optional[str]
    lots: List[_ExpiringLot]

@router.get(
    "/{station_id}/expiring-soon",
    response_model=List[_ExpiringGroup],
    summary="Stock lots expiring within N days at this station (SUP-F3)",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def get_expiring_soon(
    station_id: int,
    days: int = Query(default=30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> List[_ExpiringGroup]:
    _get_station_or_404(station_id, db)
    require_station_membership(station_id, current_user, db)

    today   = date.today()
    cutoff  = today + timedelta(days=days)

    lots = (
        db.query(StockLot)
        .join(StockLot.location)
        .join(StockLot.item)
        .filter(
            InventoryLocation.station_id == station_id,
            StockLot.expiration_date.is_not(None),
            StockLot.expiration_date >= today,
            StockLot.expiration_date <= cutoff,
            StockLot.quantity > 0,
        )
        .order_by(StockLot.expiration_date)
        .all()
    )

    groups: dict[int, _ExpiringGroup] = {}
    for lot in lots:
        loc = lot.location
        if loc.location_id not in groups:
            vehicle_number = loc.vehicle.vehicle_number if loc.vehicle else None
            groups[loc.location_id] = _ExpiringGroup(
                location_id=loc.location_id,
                location_label=loc.label,
                vehicle_number=vehicle_number,
                lots=[],
            )
        days_left = (lot.expiration_date - today).days
        groups[loc.location_id].lots.append(_ExpiringLot(
            lot_id=lot.lot_id,
            item_name=lot.item.name,
            lot_number=lot.lot_number,
            expiration_date=lot.expiration_date,
            days_until_expiry=days_left,
            quantity=lot.quantity,
        ))

    return list(groups.values())


# ── GET /stations/{station_id}/supply-alerts — SR-B3 ─────────────────────────

class _SupplyAlertItem(BaseModel):
    item_name: str
    on_hand:   int
    par_min:   int
    unit:      str


@router.get(
    "/{station_id}/supply-alerts",
    response_model=List[_SupplyAlertItem],
    summary="Items below par in the station supply room (SR-B3)",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def get_supply_alerts(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> List[_SupplyAlertItem]:
    """
    Returns items in the station supply room where on-hand < par minimum.
    Returns an empty list if the station has no supply room or nothing is low.
    """
    _get_station_or_404(station_id, db)
    require_station_membership(station_id, current_user, db)

    supply_room = db.query(InventoryLocation).filter(
        InventoryLocation.station_id    == station_id,
        InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
    ).first()
    if not supply_room:
        return []

    # Par minimums per item at supply room
    par_levels = (
        db.query(ParLevel)
        .filter(
            ParLevel.location_id == supply_room.location_id,
            ParLevel.active      == True,
        )
        .all()
    )
    if not par_levels:
        return []

    # Lowest par_min per item (item may span multiple compartments)
    par_min_by_item: dict[int, int] = {}
    for par in par_levels:
        existing = par_min_by_item.get(par.item_id)
        if existing is None or par.min_quantity < existing:
            par_min_by_item[par.item_id] = par.min_quantity

    item_ids = list(par_min_by_item.keys())

    # On-hand totals per item at supply room
    lots = (
        db.query(StockLot)
        .filter(
            StockLot.location_id == supply_room.location_id,
            StockLot.item_id.in_(item_ids),
            StockLot.quantity    >  0,
        )
        .all()
    )
    on_hand_by_item: dict[int, int] = {}
    for lot in lots:
        on_hand_by_item[lot.item_id] = on_hand_by_item.get(lot.item_id, 0) + lot.quantity

    # Items
    items = {
        i.item_id: i
        for i in db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    }

    alerts = []
    for item_id, par_min in par_min_by_item.items():
        on_hand = on_hand_by_item.get(item_id, 0)
        if on_hand < par_min:
            item = items.get(item_id)
            alerts.append(_SupplyAlertItem(
                item_name = item.name if item else str(item_id),
                on_hand   = on_hand,
                par_min   = par_min,
                unit      = item.unit_of_measure if item else "each",
            ))

    alerts.sort(key=lambda a: a.item_name)
    return alerts


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
