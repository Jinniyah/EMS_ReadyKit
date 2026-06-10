"""
routers/checks.py
Daily inventory check and controlled substance check endpoints.

Session C (ACC-B7): Station membership enforced on all check endpoints.
  - POST /checks/daily        — user must be a member of payload.station_id
  - POST /checks/controlled-substance — user must be a member of vehicle.station_id
  - GET  /checks/daily/vehicle/{id}   — user must be a member of vehicle.station_id
  - GET  /checks/daily/station/{id}/today — user must be a member of station_id;
          changed from SUPERVISOR_PLUS to ALL_ROLES (responders also need today's status)
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.core.limiter import DAILY_CHECK_RATE_LIMIT, limiter
from ems_readykit.models.check_line_item import CheckLineItem, LineItemStatus
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.daily_inventory_check import CheckStatus, DailyInventoryCheck
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station import Station
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.routers.deps import (
    ALL_ROLES,
    SUPERVISOR_PLUS,
    get_vehicle_or_404,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.controlled_substance_check import (
    ControlledSubstanceCheckCreate,
    ControlledSubstanceCheckRead,
)
from ems_readykit.schemas.daily_inventory_check import (
    DailyInventoryCheckCreate,
    DailyInventoryCheckRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checks", tags=["checks"])


class LastReadingItem(BaseModel):
    item_id:           int
    quantity_found:    Optional[int]
    measurement_value: Optional[float]
    functional_pass:   Optional[bool]
    date_value:        Optional[date]
    check_date:        str


# Frontend mirror: deriveDraftItemStatus() in frontend/src/shared/utils/statusCalc.js
# Changes to this function must be reflected there to keep draft status in sync.
def _compute_line_item_status(
    needed: int,
    found: int,
    lot: Optional[StockLot],
    *,
    check_type: str = "SUPPLY",
    measurement_value: Optional[float] = None,
    measurement_minimum: Optional[float] = None,
    functional_pass: Optional[bool] = None,
    date_value: Optional[date] = None,
    recurrence_days: Optional[int] = None,
) -> LineItemStatus:
    today = date.today()

    if check_type == "MEASUREMENT":
        if measurement_value is None:
            return LineItemStatus.MISSING
        if measurement_minimum is not None and measurement_value < measurement_minimum:
            return LineItemStatus.LOW
        return LineItemStatus.OK

    if check_type == "FUNCTIONAL":
        if functional_pass is None:
            return LineItemStatus.MISSING
        return LineItemStatus.OK if functional_pass else LineItemStatus.FAIL

    if check_type == "DATE_RECORD":
        if date_value is None:
            return LineItemStatus.MISSING
        if recurrence_days is not None:
            days_since = (today - date_value).days
            if days_since > recurrence_days:
                return LineItemStatus.OVERDUE
        return LineItemStatus.OK

    if check_type == "EXPIRY_DATE":
        if date_value is None:
            return LineItemStatus.MISSING
        if date_value < today:
            return LineItemStatus.EXPIRED
        return LineItemStatus.OK

    if check_type == "SUPPLY":
        if lot is not None and lot.expiration_date is not None and lot.expiration_date <= today:
            return LineItemStatus.EXPIRED
    if found == 0 and needed > 0:
        return LineItemStatus.MISSING
    if found < needed:
        return LineItemStatus.SHORT
    return LineItemStatus.OK


def _compute_check_status(line_items: List[CheckLineItem]) -> CheckStatus:
    if not line_items:
        return CheckStatus.PASS

    statuses = {li.status for li in line_items}

    fail_statuses = {
        LineItemStatus.EXPIRED,
        LineItemStatus.MISSING,
        LineItemStatus.FAIL,
        LineItemStatus.OVERDUE,
    }
    restock_statuses = {
        LineItemStatus.SHORT,
        LineItemStatus.LOW,
    }

    if statuses & fail_statuses:
        return CheckStatus.FAIL
    if statuses & restock_statuses:
        return CheckStatus.NEEDS_RESTOCK
    return CheckStatus.PASS


# ── SR-B4: Supply room auto-decrement helper ──────────────────────────────────

def _auto_decrement_supply_room(
    db: Session,
    station_id: int,
    vehicle_id: int,
    check_id: int,
    line_items: List[CheckLineItem],
    items_map: Dict[int, Item],
) -> None:
    """
    SR-B4: Best-effort deduction from the station supply room when a vehicle check
    shows items were topped off (quantity_found > previous check's quantity_found).
    Depletion is FIFO. Never raises — insufficient stock depletes to zero and logs a warning.
    Called after the current check is flushed but before audit/commit.
    """
    supply_room = db.query(InventoryLocation).filter(
        InventoryLocation.station_id    == station_id,
        InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
    ).first()
    if not supply_room:
        return

    prev_check = (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.vehicle_id  == vehicle_id,
            DailyInventoryCheck.deleted_at.is_(None),
            DailyInventoryCheck.check_id    != check_id,
        )
        .order_by(
            DailyInventoryCheck.check_date.desc(),
            DailyInventoryCheck.created_at.desc(),
        )
        .first()
    )
    if not prev_check:
        return  # first check — no baseline to compare against

    last_qty: Dict[tuple, Optional[int]] = {
        (li.item_id, li.compartment_id): li.quantity_found
        for li in prev_check.line_items
    }

    item_decrements: Dict[int, int] = {}
    for li in line_items:
        item = items_map.get(li.item_id)
        if not item:
            continue
        ct = item.check_type.value if hasattr(item.check_type, "value") else str(item.check_type)
        if ct != "SUPPLY":
            continue
        if li.quantity_found is None:
            continue
        prev = last_qty.get((li.item_id, li.compartment_id))
        if prev is None:
            continue
        topped_off = li.quantity_found - prev
        if topped_off <= 0:
            continue
        item_decrements[li.item_id] = item_decrements.get(li.item_id, 0) + topped_off

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
                "SR-B4 auto-decrement: no supply room stock for item %s (station %s)",
                item_id, station_id,
            )
            continue
        if available < decrement:
            logger.warning(
                "SR-B4 auto-decrement: item %s needs %s but only %s available "
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


# ── Daily Inventory Checks ────────────────────────────────────────────────────

@router.post(
    "/daily",
    response_model=DailyInventoryCheckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a daily inventory check",
)
@limiter.limit(DAILY_CHECK_RATE_LIMIT)  # per-IP: 30/min prod, unlimited in test env
async def create_daily_check(
    request: Request,
    payload: DailyInventoryCheckCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> DailyInventoryCheck:
    # Validate vehicle or portable location
    if payload.vehicle_id:
        get_vehicle_or_404(payload.vehicle_id, db)
    else:
        loc = db.query(InventoryLocation).filter(
            InventoryLocation.location_id == payload.location_id
        ).first()
        if not loc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location {payload.location_id} not found.")
        if loc.station_id != payload.station_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Location does not belong to the specified station.")

    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )

    # ACC-B7: Station membership enforcement
    require_station_membership(payload.station_id, current_user, db)

    if payload.line_items:
        compartment_ids = {li.compartment_id for li in payload.line_items}
        found_compartments = {
            c.compartment_id
            for c in db.query(Compartment).filter(
                Compartment.compartment_id.in_(compartment_ids)
            ).all()
        }
        missing_compartments = compartment_ids - found_compartments
        if missing_compartments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compartment(s) not found: {sorted(missing_compartments)}",
            )

    # SEED-GAP2: Compartments with requires_full_check=True must have every
    # active par level explicitly submitted — No Change (omitted item) is not allowed.
    _enforce_location_id: Optional[int] = None
    if payload.vehicle_id:
        veh_loc = db.query(InventoryLocation).filter(
            InventoryLocation.vehicle_id    == payload.vehicle_id,
            InventoryLocation.location_type == LocationType.VEHICLE,
        ).first()
        if veh_loc:
            _enforce_location_id = veh_loc.location_id
    else:
        _enforce_location_id = payload.location_id

    if _enforce_location_id:
        full_check_comps = db.query(Compartment).filter(
            Compartment.location_id         == _enforce_location_id,
            Compartment.requires_full_check.is_(True),
            Compartment.active.is_(True),
        ).all()
        if full_check_comps:
            submitted_pairs = {(li.compartment_id, li.item_id) for li in payload.line_items}
            for comp in full_check_comps:
                required = db.query(ParLevel).filter(
                    ParLevel.compartment_id == comp.compartment_id,
                    ParLevel.active.is_(True),
                ).all()
                missing = [p.item_id for p in required
                           if (comp.compartment_id, p.item_id) not in submitted_pairs]
                if missing:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Compartment '{comp.name}' requires a full check — "
                            "all items must be submitted. "
                            f"Missing item IDs: {sorted(missing)}"
                        ),
                    )

    lot_ids = {li.lot_id for li in payload.line_items if li.lot_id is not None}
    lot_map: Dict[int, StockLot] = {}
    if lot_ids:
        lots = db.query(StockLot).filter(StockLot.lot_id.in_(lot_ids)).all()
        lot_map = {lot.lot_id: lot for lot in lots}

        missing_lots = lot_ids - set(lot_map.keys())
        if missing_lots:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock lot(s) not found: {sorted(missing_lots)}",
            )

        for li in payload.line_items:
            if li.lot_id is not None:
                lot = lot_map[li.lot_id]
                if lot.item_id != li.item_id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Stock lot {li.lot_id} belongs to item {lot.item_id}, "
                            f"not item {li.item_id}."
                        ),
                    )

    performed_by = current_user.email or current_user.name

    # Derive check_date server-side from the submitted timestamp.
    # The client may send a check_date but we override it — this prevents
    # backdating and ensures the audit trail reflects when the check
    # actually occurred, not a client-supplied date.
    # check_date is stored as YYYY-MM-DD string in UTC.
    check_date = payload.timestamp.astimezone(timezone.utc).date().isoformat()

    item_ids = {li.item_id for li in payload.line_items}
    items_map = {
        item.item_id: item
        for item in db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    }

    missing_items = item_ids - set(items_map.keys())
    if missing_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item(s) not found: {sorted(missing_items)}",
        )

    line_item_objects: List[CheckLineItem] = []
    for li in payload.line_items:
        lot = lot_map.get(li.lot_id) if li.lot_id else None
        item = items_map[li.item_id]
        li_status = _compute_line_item_status(
            li.quantity_needed,
            li.quantity_found,
            lot,
            check_type=item.check_type.value if hasattr(item.check_type, "value") else str(item.check_type),
            measurement_value=li.measurement_value,
            measurement_minimum=item.measurement_minimum,
            functional_pass=li.functional_pass,
            date_value=li.date_value,
            recurrence_days=item.recurrence_days,
        )
        line_item_objects.append(
            CheckLineItem(
                compartment_id=li.compartment_id,
                item_id=li.item_id,
                lot_id=li.lot_id,
                quantity_needed=li.quantity_needed,
                quantity_found=li.quantity_found,
                measurement_value=li.measurement_value,
                functional_pass=li.functional_pass,
                date_value=li.date_value,
                status=li_status,
                notes=li.notes,
            )
        )

    overall_status = _compute_check_status(line_item_objects)

    check = DailyInventoryCheck(
        vehicle_id=payload.vehicle_id,
        location_id=payload.location_id,
        station_id=payload.station_id,
        check_date=check_date,
        performed_by=performed_by,
        timestamp=payload.timestamp,
        status=overall_status,
        notes=payload.notes,
        line_items=line_item_objects,
    )
    db.add(check)
    db.flush()

    # SR-B4: auto-decrement supply room for vehicle checks (best-effort, never blocks)
    if payload.vehicle_id:
        _auto_decrement_supply_room(
            db           = db,
            station_id   = payload.station_id,
            vehicle_id   = payload.vehicle_id,
            check_id     = check.check_id,
            line_items   = line_item_objects,
            items_map    = items_map,
        )

    expired_count = sum(1 for li in line_item_objects if li.status == LineItemStatus.EXPIRED)
    missing_count = sum(1 for li in line_item_objects if li.status == LineItemStatus.MISSING)
    short_count   = sum(1 for li in line_item_objects if li.status == LineItemStatus.SHORT)

    audit_severity = "INFO" if overall_status == CheckStatus.PASS else "WARNING"
    if overall_status == CheckStatus.FAIL:
        audit_severity = "HIGH"

    write_audit_event(
        db,
        actor=performed_by,
        action="CHECK_COMPLETED",
        entity_type="DailyInventoryCheck",
        entity_id=str(check.check_id),
        station_id=payload.station_id,
        vehicle_id=payload.vehicle_id,
        metadata={
            "status": overall_status.value,
            "check_date": check_date,
            "line_items_total": len(line_item_objects),
            "expired_count": expired_count,
            "missing_count": missing_count,
            "short_count": short_count,
        },
        severity=audit_severity,
    )
    return check


@router.get(
    "/daily/last-readings",
    response_model=List[LastReadingItem],
    summary="Last recorded readings for each item from the most recent check on a vehicle or location",
)
def get_last_readings(
    vehicle_id:  Optional[int] = Query(None, gt=0),
    location_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[LastReadingItem]:
    if vehicle_id is None and location_id is None:
        raise HTTPException(status_code=400, detail="vehicle_id or location_id required")

    q = db.query(DailyInventoryCheck).filter(DailyInventoryCheck.deleted_at.is_(None))
    if vehicle_id is not None:
        q = q.filter(DailyInventoryCheck.vehicle_id == vehicle_id)
    else:
        q = q.filter(DailyInventoryCheck.location_id == location_id)

    last_check = q.order_by(
        DailyInventoryCheck.check_date.desc(),
        DailyInventoryCheck.created_at.desc(),
    ).first()

    if not last_check:
        return []

    return [
        LastReadingItem(
            item_id=li.item_id,
            quantity_found=li.quantity_found,
            measurement_value=li.measurement_value,
            functional_pass=li.functional_pass,
            date_value=li.date_value,
            check_date=str(last_check.check_date),
        )
        for li in last_check.line_items
    ]


@router.get(
    "/daily/{check_id}",
    response_model=DailyInventoryCheckRead,
    summary="Get a daily inventory check",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def get_daily_check(check_id: int, db: Session = Depends(get_db)) -> DailyInventoryCheck:
    """Returns a single daily inventory check. Excludes soft-deleted records."""
    check = db.query(DailyInventoryCheck).filter(
        DailyInventoryCheck.check_id == check_id,
        DailyInventoryCheck.deleted_at.is_(None),
    ).first()
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily inventory check {check_id} not found.",
        )
    return check


@router.get(
    "/daily/vehicle/{vehicle_id}",
    response_model=List[DailyInventoryCheckRead],
    summary="List daily checks for a vehicle",
)
def list_vehicle_daily_checks(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    """Returns all non-deleted daily inventory checks for a vehicle, most recent first."""
    vehicle = get_vehicle_or_404(vehicle_id, db)
    # ACC-B7: derive station from vehicle and enforce membership
    require_station_membership(vehicle.station_id, current_user, db)
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.vehicle_id == vehicle_id,
            DailyInventoryCheck.deleted_at.is_(None),
        )
        .order_by(DailyInventoryCheck.timestamp.desc())
        .all()
    )


@router.get(
    "/daily/station/{station_id}/today",
    response_model=List[DailyInventoryCheckRead],
    summary="Get today's compliance status for a station",
)
def get_station_compliance_today(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    """
    Returns all non-deleted daily checks for a station for today.
    All roles (Responders need this for the home screen badge and supervisor view).
    Station membership enforced.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    # ACC-B7: station membership enforcement
    require_station_membership(station_id, current_user, db)

    today = datetime.now(timezone.utc).date().isoformat()
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.check_date == today,
            DailyInventoryCheck.deleted_at.is_(None),
        )
        .order_by(DailyInventoryCheck.timestamp.desc())
        .all()
    )


@router.get(
    "/daily/station/{station_id}",
    response_model=List[DailyInventoryCheckRead],
    summary="Get compliance checks for a station within a date range (B-E3)",
)
def get_station_checks_date_range(
    station_id: int,
    from_date: Optional[str] = Query(
        default=None,
        alias="from",
        description="Start date inclusive (YYYY-MM-DD). Defaults to today.",
    ),
    to_date: Optional[str] = Query(
        default=None,
        alias="to",
        description="End date inclusive (YYYY-MM-DD). Defaults to today.",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    """
    Returns all non-deleted daily checks for a station within an inclusive date range.
    All roles with station membership may query.
    Maximum range: 90 days (matches the soft-delete retention window).
    If from/to are omitted, defaults to today only.
    """
    _DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    require_station_membership(station_id, current_user, db)

    today_str = datetime.now(timezone.utc).date().isoformat()
    resolved_from = from_date or today_str
    resolved_to   = to_date   or today_str

    for label, value in (("from", resolved_from), ("to", resolved_to)):
        if not _DATE.match(value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"'{label}' must be in YYYY-MM-DD format.",
            )

    if resolved_from > resolved_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="'from' date must be on or before 'to' date.",
        )

    d_from = date.fromisoformat(resolved_from)
    d_to   = date.fromisoformat(resolved_to)
    if (d_to - d_from).days > 90:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Date range may not exceed 90 days.",
        )

    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.check_date >= resolved_from,
            DailyInventoryCheck.check_date <= resolved_to,
            DailyInventoryCheck.deleted_at.is_(None),
        )
        .order_by(DailyInventoryCheck.timestamp.desc())
        .all()
    )


# ── Portable location checks ──────────────────────────────────────────────────

@router.get(
    "/daily/location/{location_id}",
    response_model=List[DailyInventoryCheckRead],
    summary="Get checks for a portable location (jump bag / equipment)",
)
def get_location_checks(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    loc = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {location_id} not found.")
    require_station_membership(loc.station_id, current_user, db)
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.location_id == location_id,
            DailyInventoryCheck.deleted_at.is_(None),
        )
        .order_by(DailyInventoryCheck.timestamp.desc())
        .all()
    )


# ── Calendar date-range bounds ────────────────────────────────────────────────

@router.get(
    "/daily/station/{station_id}/date-range",
    summary="Earliest check date for a station — used to bound calendar navigation",
)
def get_station_check_date_range(
    station_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
):
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.")
    require_station_membership(station_id, current_user, db)
    earliest = db.query(func.min(DailyInventoryCheck.check_date)).filter(
        DailyInventoryCheck.station_id == station_id,
        DailyInventoryCheck.deleted_at.is_(None),
    ).scalar()
    return {"earliest": str(earliest) if earliest else None}


# ── Controlled Substance Checks ───────────────────────────────────────────────

@router.post(
    "/controlled-substance",
    response_model=ControlledSubstanceCheckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a controlled substance check",
)
def create_cs_check(
    payload: ControlledSubstanceCheckCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> ControlledSubstanceCheck:
    vehicle = get_vehicle_or_404(payload.vehicle_id, db)

    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Vehicle {payload.vehicle_id} is type '{vehicle.vehicle_type.value}'. "
                "Controlled substance checks are only required for ALS vehicles."
            ),
        )

    # ACC-B7: station membership enforcement
    require_station_membership(vehicle.station_id, current_user, db)

    primary_signer = current_user.name

    # OWASP A04 — Known limitation: secondary_signer is free-text and compared
    # by name string only. The structural fix is F-UX34. See backlog.md SEC-6.
    if primary_signer.strip().lower() == payload.secondary_signer.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "dual-signature requirement: primary_signer and secondary_signer "
                "must be different people."
            ),
        )

    check = ControlledSubstanceCheck(
        vehicle_id=payload.vehicle_id,
        primary_signer=primary_signer,
        secondary_signer=payload.secondary_signer,
        timestamp=payload.timestamp,
        discrepancy_flag=payload.discrepancy_flag,
        notes=payload.notes,
    )
    db.add(check)
    db.flush()

    severity = "HIGH" if payload.discrepancy_flag else "INFO"
    action = "CS_DISCREPANCY" if payload.discrepancy_flag else "CS_CHECK_COMPLETED"

    if payload.discrepancy_flag:
        logger.warning(
            "Controlled substance discrepancy flagged",
            extra={
                "vehicle_id":     payload.vehicle_id,
                "primary_signer": primary_signer,
                "cs_check_id":    check.cs_check_id,
            },
        )

    write_audit_event(
        db,
        actor=primary_signer,
        action=action,
        entity_type="ControlledSubstanceCheck",
        entity_id=str(check.cs_check_id),
        vehicle_id=payload.vehicle_id,
        station_id=vehicle.station_id,
        metadata={
            "secondary_signer": payload.secondary_signer,
            "discrepancy_flag": payload.discrepancy_flag,
            "notes":            payload.notes,
        },
        severity=severity,
    )
    return check


@router.get(
    "/controlled-substance/{cs_check_id}",
    response_model=ControlledSubstanceCheckRead,
    summary="Get a controlled substance check",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def get_cs_check(cs_check_id: int, db: Session = Depends(get_db)) -> ControlledSubstanceCheck:
    check = db.query(ControlledSubstanceCheck).filter(
        ControlledSubstanceCheck.cs_check_id == cs_check_id
    ).first()
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Controlled substance check {cs_check_id} not found.",
        )
    return check


@router.get(
    "/controlled-substance/vehicle/{vehicle_id}",
    response_model=List[ControlledSubstanceCheckRead],
    summary="List CS checks for a vehicle",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def list_vehicle_cs_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[ControlledSubstanceCheck]:
    vehicle = get_vehicle_or_404(vehicle_id, db)
    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Vehicle {vehicle_id} is type '{vehicle.vehicle_type.value}'. "
                "Only ALS vehicles have controlled substance checks."
            ),
        )
    return (
        db.query(ControlledSubstanceCheck)
        .filter(ControlledSubstanceCheck.vehicle_id == vehicle_id)
        .order_by(ControlledSubstanceCheck.timestamp.desc())
        .all()
    )
