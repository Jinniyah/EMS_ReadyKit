"""
routers/usage.py
After-Call Reset — usage event endpoints.

POST /checks/usage
  Record items used during/after a call. Decrements the station supply
  room stock lots FIFO (best-effort, never blocks). Creates a UsageEvent
  audit trail for the history view.

GET /checks/usage/station/{station_id}
  Usage history for a station — most recent first. Used by the
  "Usage Log" screen in Station Supplies.

GET /checks/usage/station/{station_id}/frequent
  Top items by usage count (last 90 days, station-wide).
  Used to pre-populate the After-Call Reset item picker.
  Returns an empty list when no data exists; the frontend shows
  hardcoded defaults in that case.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCheckType
from ems_readykit.models.station import Station
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.usage_event import UsageEvent, UsageEventItem
from ems_readykit.routers.deps import (
    ALL_ROLES,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.usage_event import (
    FrequentItemRead,
    UsageEventCreate,
    UsageEventRead,
    UsageItemRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checks", tags=["usage"])

_FREQUENT_LOOKBACK_DAYS = 90
_FREQUENT_LIMIT = 10


def _decrement_supply_room_fifo(
    db: Session,
    station_id: int,
    item_decrements: Dict[int, int],
) -> None:
    """
    Deplete supply room stock lots FIFO for the given item->quantity map.
    Best-effort: depletes to zero on insufficient stock, never raises.
    """
    supply_room = db.query(InventoryLocation).filter(
        InventoryLocation.station_id    == station_id,
        InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
    ).first()
    if not supply_room:
        return

    for item_id, decrement in item_decrements.items():
        supply_lots = (
            db.query(StockLot)
            .filter(
                StockLot.location_id == supply_room.location_id,
                StockLot.item_id     == item_id,
                StockLot.quantity    >  0,
            )
            .order_by(StockLot.expiration_date.asc().nulls_last())
            .all()
        )
        available = sum(lot.quantity for lot in supply_lots)
        if available == 0:
            logger.warning(
                "usage decrement: no supply room stock for item %s (station %s)",
                item_id, station_id,
            )
            continue
        if available < decrement:
            logger.warning(
                "usage decrement: item %s needs %s but only %s available "
                "(station %s) — depleting to zero",
                item_id, decrement, available, station_id,
            )
        remaining = min(decrement, available)
        for lot in supply_lots:
            if remaining <= 0:
                break
            take          = min(lot.quantity, remaining)
            lot.quantity -= take
            remaining    -= take

    db.flush()


def _build_event_read(event: UsageEvent) -> UsageEventRead:
    return UsageEventRead(
        event_id       = event.event_id,
        station_id     = event.station_id,
        vehicle_id     = event.vehicle_id,
        vehicle_number = event.vehicle.vehicle_number if event.vehicle else None,
        performed_by   = event.performed_by,
        timestamp      = event.timestamp,
        notes          = event.notes,
        items          = [
            UsageItemRead(
                item_id       = uei.item_id,
                item_name     = uei.item.name if uei.item else f"Item {uei.item_id}",
                quantity_used = uei.quantity_used,
            )
            for uei in event.items
        ],
    )


@router.post(
    "/usage",
    response_model=UsageEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log items used after a call",
)
def create_usage_event(
    payload: UsageEventCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> UsageEventRead:
    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )

    require_station_membership(payload.station_id, current_user, db)

    item_ids = {i.item_id for i in payload.items}
    items_map: Dict[int, Item] = {
        item.item_id: item
        for item in db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    }
    missing = item_ids - set(items_map.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item(s) not found: {sorted(missing)}",
        )

    # Only SUPPLY items can have stock decremented — others are silently skipped.
    non_supply = [
        items_map[i.item_id].name
        for i in payload.items
        if items_map[i.item_id].check_type != ItemCheckType.SUPPLY
    ]
    if non_supply:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Only SUPPLY items can be logged as used. "
                f"Non-supply items submitted: {non_supply}"
            ),
        )

    performed_by = current_user.email or current_user.name

    event = UsageEvent(
        station_id   = payload.station_id,
        vehicle_id   = payload.vehicle_id,
        performed_by = performed_by,
        timestamp    = payload.timestamp,
        notes        = payload.notes,
        items        = [
            UsageEventItem(
                item_id       = i.item_id,
                quantity_used = i.quantity_used,
            )
            for i in payload.items
        ],
    )
    db.add(event)
    db.flush()

    item_decrements = {i.item_id: i.quantity_used for i in payload.items}
    _decrement_supply_room_fifo(db, payload.station_id, item_decrements)

    write_audit_event(
        db,
        actor        = performed_by,
        action       = "USAGE_LOGGED",
        entity_type  = "UsageEvent",
        entity_id    = str(event.event_id),
        station_id   = payload.station_id,
        vehicle_id   = payload.vehicle_id,
        metadata     = {
            "item_count": len(payload.items),
            "total_units": sum(i.quantity_used for i in payload.items),
        },
    )

    return _build_event_read(event)


@router.get(
    "/usage/station/{station_id}",
    response_model=List[UsageEventRead],
    summary="Usage history for a station",
)
def get_station_usage_history(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[UsageEventRead]:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

    require_station_membership(station_id, current_user, db)

    events = (
        db.query(UsageEvent)
        .filter(UsageEvent.station_id == station_id)
        .order_by(UsageEvent.timestamp.desc())
        .limit(100)
        .all()
    )
    return [_build_event_read(e) for e in events]


@router.get(
    "/usage/station/{station_id}/frequent",
    response_model=List[FrequentItemRead],
    summary="Top items used at this station (last 90 days)",
)
def get_frequent_items(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[FrequentItemRead]:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )

    require_station_membership(station_id, current_user, db)

    cutoff = datetime.now(timezone.utc) - timedelta(days=_FREQUENT_LOOKBACK_DAYS)

    rows = (
        db.query(
            UsageEventItem.item_id,
            Item.name.label("item_name"),
            func.sum(UsageEventItem.quantity_used).label("total_used"),
        )
        .join(UsageEvent, UsageEventItem.event_id == UsageEvent.event_id)
        .join(Item, UsageEventItem.item_id == Item.item_id)
        .filter(
            UsageEvent.station_id == station_id,
            UsageEvent.timestamp  >= cutoff,
        )
        .group_by(UsageEventItem.item_id, Item.name)
        .order_by(func.sum(UsageEventItem.quantity_used).desc())
        .limit(_FREQUENT_LIMIT)
        .all()
    )

    return [
        FrequentItemRead(
            item_id    = row.item_id,
            item_name  = row.item_name,
            total_used = row.total_used,
        )
        for row in rows
    ]
