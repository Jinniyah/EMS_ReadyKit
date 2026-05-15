"""
routers/checks.py
Daily inventory check and controlled substance check endpoints.

Phase 4 changes:
- POST /checks/daily now accepts line_items with optional lot_id
- lot_id links to a specific StockLot — enables expiration verification
- Status computation:
    EXPIRED       — lot_id provided and lot.expiration_date <= today
    MISSING       — quantity_found == 0 and quantity_needed > 0
    SHORT         — 0 < quantity_found < quantity_needed
    OK            — quantity_found >= quantity_needed and not expired
- Overall check status worst-case:
    FAIL          — any EXPIRED or MISSING
    NEEDS_RESTOCK — any SHORT (no EXPIRED/MISSING)
    PASS          — all OK (or no line items)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_RESPONDER,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.check_line_item import CheckLineItem, LineItemStatus
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck, CheckStatus
from ems_readykit.models.item import Item
from ems_readykit.models.station import Station
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.controlled_substance_check import (
    ControlledSubstanceCheckCreate,
    ControlledSubstanceCheckRead,
)
from ems_readykit.schemas.daily_inventory_check import (
    DailyInventoryCheckCreate,
    DailyInventoryCheckRead,
)
from ems_readykit.schemas.check_line_item import CheckLineItemCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checks", tags=["checks"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)


def _get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle


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
    """
    Compute per-line-item status based on item.check_type.

    SUPPLY (default):
        Expiration takes priority over quantity — an expired lot is a
        compliance failure regardless of the count found on the truck.

    MEASUREMENT (O2 PSI, temperature, glucose):
        LOW if measurement_value < measurement_minimum.
        OK if at or above minimum.

    FUNCTIONAL (battery OK, runs & starts, lights & sirens):
        OK if functional_pass is True.
        FAIL if functional_pass is False.

    DATE_RECORD (AED last charge, LUCAS last charge):
        OVERDUE if days since date_value > recurrence_days.
        OK if within recurrence window.

    DOCUMENT (PCR form, protocol book):
        MISSING if found == 0.
        OK if found >= 1.
    """
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

    # SUPPLY and DOCUMENT both use quantity logic
    # Expiration check applies only to SUPPLY items with a lot
    if check_type == "SUPPLY":
        if lot is not None and lot.expiration_date is not None and lot.expiration_date <= today:
            return LineItemStatus.EXPIRED
    if found == 0 and needed > 0:
        return LineItemStatus.MISSING
    if found < needed:
        return LineItemStatus.SHORT
    return LineItemStatus.OK


def _compute_check_status(line_items: List[CheckLineItem]) -> CheckStatus:
    """
    Derive overall check status from all line item statuses.
    No line items → PASS (header-only check).

    Priority order (worst to best):
      FAIL     — any EXPIRED, MISSING, FAIL, or OVERDUE item
      NEEDS_RESTOCK — any SHORT or LOW item (but no FAIL-tier items)
      PASS     — all OK
    """
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


def _write_audit_event(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    severity: str = "INFO",
) -> None:
    event = AuditEvent(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        station_id=station_id,
        vehicle_id=vehicle_id,
        metadata_json=metadata,
        severity=severity,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    logger.info(
        "Audit event written",
        extra={
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "severity": severity,
        },
    )


# ── Daily Inventory Checks ────────────────────────────────────────────────────

@router.post(
    "/daily",
    response_model=DailyInventoryCheckRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a daily inventory check",
)
def create_daily_check(
    payload: DailyInventoryCheckCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> DailyInventoryCheck:
    """
    Submits a daily inventory check for a vehicle.

    Optionally include line_items to record per-compartment item counts.
    Each line item maps to one row on the paper form (Need / Have columns).

    When lot_id is provided on a line item, the router:
      - Validates the lot exists and belongs to the correct item
      - Checks the lot's expiration date
      - Sets status to EXPIRED if expiration_date <= today

    The overall check status is computed automatically from line items:
      FAIL          = any EXPIRED or MISSING items
      NEEDS_RESTOCK = any SHORT items
      PASS          = all OK (or no line items)

    performed_by is set from the authenticated user's identity.
    """
    vehicle = _get_vehicle_or_404(payload.vehicle_id, db)

    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )

    # Validate all compartment IDs up front
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

    # Validate all lot IDs up front and build a lookup map
    lot_ids = {li.lot_id for li in payload.line_items if li.lot_id is not None}
    lot_map: Dict[int, StockLot] = {}
    if lot_ids:
        lots = db.query(StockLot).filter(StockLot.lot_id.in_(lot_ids)).all()
        lot_map = {lot.lot_id: lot for lot in lots}

        # Check all lot IDs exist
        missing_lots = lot_ids - set(lot_map.keys())
        if missing_lots:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock lot(s) not found: {sorted(missing_lots)}",
            )

        # Validate each lot belongs to the correct item
        for li in payload.line_items:
            if li.lot_id is not None:
                lot = lot_map[li.lot_id]
                if lot.item_id != li.item_id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Stock lot {li.lot_id} belongs to item {lot.item_id}, "
                            f"not item {li.item_id}. "
                            "Each line item's lot_id must match its item_id."
                        ),
                    )

    performed_by = current_user.name

    # Build line item ORM objects and compute statuses
    # For each line item, look up the item's check_type and measurement
    # metadata so _compute_line_item_status can route correctly.
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
        station_id=payload.station_id,
        check_date=payload.check_date,
        performed_by=performed_by,
        timestamp=payload.timestamp,
        status=overall_status,
        notes=payload.notes,
        line_items=line_item_objects,
    )
    db.add(check)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A daily inventory check for vehicle {payload.vehicle_id} "
                f"on {payload.check_date} already exists."
            ),
        )
    db.refresh(check)

    expired_count = sum(1 for li in line_item_objects if li.status == LineItemStatus.EXPIRED)
    missing_count = sum(1 for li in line_item_objects if li.status == LineItemStatus.MISSING)
    short_count   = sum(1 for li in line_item_objects if li.status == LineItemStatus.SHORT)

    audit_severity = "INFO" if overall_status == CheckStatus.PASS else "WARNING"
    if overall_status == CheckStatus.FAIL:
        audit_severity = "HIGH"

    _write_audit_event(
        db,
        actor=performed_by,
        action="CHECK_COMPLETED",
        entity_type="DailyInventoryCheck",
        entity_id=str(check.check_id),
        station_id=payload.station_id,
        vehicle_id=payload.vehicle_id,
        metadata={
            "status": overall_status.value,
            "check_date": payload.check_date,
            "line_items_total": len(line_item_objects),
            "expired_count": expired_count,
            "missing_count": missing_count,
            "short_count": short_count,
        },
        severity=audit_severity,
    )
    return check


@router.get(
    "/daily/{check_id}",
    response_model=DailyInventoryCheckRead,
    summary="Get a daily inventory check",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_daily_check(check_id: int, db: Session = Depends(get_db)) -> DailyInventoryCheck:
    """Returns a single daily inventory check with all line items. Requires Supervisor or Administrator."""
    check = db.query(DailyInventoryCheck).filter(
        DailyInventoryCheck.check_id == check_id
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
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_vehicle_daily_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[DailyInventoryCheck]:
    """Returns all daily inventory checks for a vehicle, most recent first. All authenticated roles."""
    _get_vehicle_or_404(vehicle_id, db)
    return (
        db.query(DailyInventoryCheck)
        .filter(DailyInventoryCheck.vehicle_id == vehicle_id)
        .order_by(DailyInventoryCheck.check_date.desc())
        .all()
    )


@router.get(
    "/daily/station/{station_id}/today",
    response_model=List[DailyInventoryCheckRead],
    summary="Get today's compliance status for a station",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_station_compliance_today(
    station_id: int, db: Session = Depends(get_db)
) -> List[DailyInventoryCheck]:
    """Returns all completed daily checks for a station for today. Requires Supervisor or Administrator."""
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    today = datetime.now(timezone.utc).date().isoformat()
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.check_date == today,
        )
        .all()
    )


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
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> ControlledSubstanceCheck:
    """
    Submits a dual-signature controlled substance check for an ALS vehicle.
    primary_signer is set from the authenticated user's identity.
    secondary_signer must still be provided in the request body (dual-signature requirement).
    Returns 422 if the vehicle is not an ALS unit.
    Generates a HIGH severity audit event if discrepancy_flag=True.
    """
    vehicle = _get_vehicle_or_404(payload.vehicle_id, db)

    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Vehicle {payload.vehicle_id} is type '{vehicle.vehicle_type.value}'. "
                "Controlled substance checks are only required for ALS vehicles."
            ),
        )

    primary_signer = current_user.name

    if primary_signer.strip().lower() == payload.secondary_signer.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "primary_signer and secondary_signer must be different people. "
                "The dual-signature workflow requires two witnesses."
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
    db.commit()
    db.refresh(check)

    severity = "HIGH" if payload.discrepancy_flag else "INFO"
    action = "CS_DISCREPANCY" if payload.discrepancy_flag else "CS_CHECK_COMPLETED"

    if payload.discrepancy_flag:
        logger.warning(
            "Controlled substance discrepancy flagged",
            extra={
                "vehicle_id": payload.vehicle_id,
                "primary_signer": primary_signer,
                "cs_check_id": check.cs_check_id,
            },
        )

    _write_audit_event(
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
            "notes": payload.notes,
        },
        severity=severity,
    )
    return check


@router.get(
    "/controlled-substance/{cs_check_id}",
    response_model=ControlledSubstanceCheckRead,
    summary="Get a controlled substance check",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def get_cs_check(cs_check_id: int, db: Session = Depends(get_db)) -> ControlledSubstanceCheck:
    """Returns a single CS check by ID. Requires Supervisor or Administrator."""
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
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def list_vehicle_cs_checks(
    vehicle_id: int, db: Session = Depends(get_db)
) -> List[ControlledSubstanceCheck]:
    """Returns all CS checks for a vehicle, most recent first. Requires Supervisor or Administrator."""
    vehicle = _get_vehicle_or_404(vehicle_id, db)
    if not vehicle.requires_controlled_substance_check:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
