"""
routers/inventory.py
Inventory location, compartment, stock lot, and par level endpoints.

Session C (ACC-B8): Station membership enforced on inventory endpoints.
  - GET  /inventory/locations            — requires station_id param (enforced) or Admin only
  - GET  /inventory/locations/{id}       — derives station from location, enforces membership
  - GET  /inventory/locations/{id}/stock        — same
  - GET  /inventory/locations/{id}/par-levels   — same
  - GET  /inventory/locations/{id}/compartments — same
  - POST /inventory/locations            — enforces membership on payload.station_id
  - POST /inventory/lots                 — enforces membership via location.station_id
  - POST /inventory/par-levels           — enforces membership via location.station_id
  - POST /inventory/locations/{id}/compartments — same

Design note: GET /inventory/locations without ?station_id is restricted to
Administrators. All other roles must supply a station_id they are a member of.
This protects station data while allowing the check wizard to fetch location
data by passing the known station_id.
"""

from __future__ import annotations

import csv as csv_mod
import io
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.item import Item
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.stock_transfer import StockTransfer
from ems_readykit.routers.deps import (
    ALL_ROLES,
    ADMIN_ONLY,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.compartment import CompartmentCreate, CompartmentRead
from ems_readykit.schemas.inventory_location import InventoryLocationRead, InventoryLocationCreate
from ems_readykit.schemas.par_level import ParLevelCreate, ParLevelRead
from ems_readykit.schemas.stock_lot import StockLotCreate, StockLotRead, StockLotUpdate
from ems_readykit.schemas.stock_transfer import (
    CsvReceiveResult, StockItemSummary, StockTransferRead, TransferRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _get_location_or_404(location_id: int, db: Session) -> InventoryLocation:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {location_id} not found.",
        )
    return location


# ── Inventory Locations ───────────────────────────────────────────────────────

@router.get(
    "/locations",
    response_model=List[InventoryLocationRead],
    summary="List inventory locations",
)
def list_locations(
    station_id: Optional[int] = Query(
        default=None,
        description=(
            "Filter by station. Required for non-Administrators. "
            "Membership enforced when supplied."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[InventoryLocation]:
    """
    ACC-B8: Non-Administrators must supply ?station_id= and be a member of it.
    Administrators may omit station_id to list all locations.
    """
    if station_id is not None:
        require_station_membership(station_id, current_user, db)
        return (
            db.query(InventoryLocation)
            .filter(InventoryLocation.station_id == station_id)
            .all()
        )

    # No station_id supplied — Administrator only
    if not current_user.has_role(ROLE_ADMINISTRATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Please select a station first. "
                "Supply ?station_id= to list locations for your station."
            ),
        )
    return db.query(InventoryLocation).all()


@router.get(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Get an inventory location",
)
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> InventoryLocation:
    location = _get_location_or_404(location_id, db)
    # ACC-B8: derive station from location
    require_station_membership(location.station_id, current_user, db)
    return location


@router.post(
    "/locations",
    response_model=InventoryLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a JUMP_BAG or EQUIPMENT inventory location",
)
def create_location(
    payload: InventoryLocationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> InventoryLocation:
    from ems_readykit.models.inventory_location import LocationType
    if payload.location_type in (LocationType.VEHICLE, LocationType.STATION_SUPPLY_ROOM):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"location_type '{payload.location_type.value}' is system-managed. "
                "Only JUMP_BAG and EQUIPMENT locations can be created via this endpoint."
            ),
        )
    from ems_readykit.models.station import Station
    station = db.query(Station).filter(Station.station_id == payload.station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} not found.",
        )
    # ACC-B8: membership on target station
    require_station_membership(payload.station_id, current_user, db)

    location = InventoryLocation(
        location_type=payload.location_type,
        station_id=payload.station_id,
        vehicle_id=payload.vehicle_id,
        label=payload.label,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    logger.info(
        "Inventory location created: location_id=%s type=%s station_id=%s",
        location.location_id, location.location_type, location.station_id,
        extra={
            "action":      "LOCATION_CREATED",
            "entity_type": "inventory_location",
            "entity_id":   str(location.location_id),
        },
    )
    return location


@router.get(
    "/locations/{location_id}/stock",
    response_model=List[StockLotRead],
    summary="List stock lots at a location",
)
def list_location_stock(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[StockLot]:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return db.query(StockLot).filter(StockLot.location_id == location_id).all()


@router.get(
    "/locations/{location_id}/par-levels",
    response_model=List[ParLevelRead],
    summary="List par levels at a location",
)
def list_location_par_levels(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[ParLevel]:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return db.query(ParLevel).filter(ParLevel.location_id == location_id).all()


# ── Compartments ──────────────────────────────────────────────────────────────

@router.get(
    "/locations/{location_id}/compartments",
    response_model=List[CompartmentRead],
    summary="List compartments at a location",
)
def list_compartments(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[Compartment]:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return (
        db.query(Compartment)
        .filter(Compartment.location_id == location_id)
        .order_by(Compartment.sort_order)
        .all()
    )


@router.post(
    "/locations/{location_id}/compartments",
    response_model=CompartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a compartment",
)
def create_compartment(
    location_id: int,
    payload: CompartmentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Compartment:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)

    if payload.location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Request body location_id ({payload.location_id}) does not match "
                f"path location_id ({location_id})."
            ),
        )

    compartment = Compartment(
        location_id=location_id,
        name=payload.name,
        location_descriptor=payload.location_descriptor,
        sort_order=payload.sort_order,
        parent_compartment_id=payload.parent_compartment_id,
        restriction_note=payload.restriction_note,
        als_only=payload.als_only,
        active=payload.active,
    )
    db.add(compartment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A compartment named '{payload.name}' already exists "
                f"at location {location_id}."
            ),
        )
    db.refresh(compartment)
    logger.info(
        "Compartment created: compartment_id=%s name=%r location_id=%s",
        compartment.compartment_id, compartment.name, location_id,
        extra={
            "action":      "COMPARTMENT_CREATED",
            "entity_type": "compartment",
            "entity_id":   str(compartment.compartment_id),
        },
    )
    return compartment


@router.get(
    "/compartments/{compartment_id}",
    response_model=CompartmentRead,
    summary="Get a compartment",
)
def get_compartment(
    compartment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> Compartment:
    compartment = db.query(Compartment).filter(
        Compartment.compartment_id == compartment_id
    ).first()
    if not compartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compartment {compartment_id} not found.",
        )
    location = _get_location_or_404(compartment.location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return compartment


@router.patch(
    "/compartments/{compartment_id}",
    response_model=CompartmentRead,
    summary="Edit a compartment (ADMIN-UX1-B1)",
)
def update_compartment(
    compartment_id: int,
    payload: CompartmentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Compartment:
    """
    Edit a compartment's name, descriptor, sort order, or restriction note.
    Supervisor+ with station membership required.
    """
    compartment = db.query(Compartment).filter(
        Compartment.compartment_id == compartment_id
    ).first()
    if not compartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compartment {compartment_id} not found.",
        )
    location = _get_location_or_404(compartment.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    # Check for name conflict within same location
    name_conflict = db.query(Compartment).filter(
        Compartment.location_id    == compartment.location_id,
        Compartment.name           == payload.name,
        Compartment.compartment_id != compartment_id,
    ).first()
    if name_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A compartment named '{payload.name}' already exists at this location.",
        )

    compartment.name                 = payload.name
    compartment.location_descriptor  = payload.location_descriptor
    compartment.sort_order           = payload.sort_order
    compartment.restriction_note     = payload.restriction_note
    compartment.als_only             = payload.als_only
    compartment.active               = payload.active

    db.commit()
    db.refresh(compartment)
    logger.info(
        "Compartment updated: compartment_id=%s name=%r",
        compartment.compartment_id, compartment.name,
        extra={
            "action":      "COMPARTMENT_UPDATED",
            "entity_type": "compartment",
            "entity_id":   str(compartment.compartment_id),
        },
    )
    return compartment


# ── Stock Lots ────────────────────────────────────────────────────────────────

@router.post(
    "/lots",
    response_model=StockLotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stock lot",
)
def create_stock_lot(
    payload: StockLotCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> StockLot:
    location = _get_location_or_404(payload.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    lot = StockLot(
        item_id=payload.item_id,
        location_id=payload.location_id,
        quantity=payload.quantity,
        lot_number=payload.lot_number,
        expiration_date=payload.expiration_date,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    logger.info(
        "Stock lot created: lot_id=%s item_id=%s location_id=%s",
        lot.lot_id, lot.item_id, lot.location_id,
        extra={
            "action":      "STOCK_LOT_CREATED",
            "entity_type": "stock_lot",
            "entity_id":   str(lot.lot_id),
        },
    )
    return lot


@router.get(
    "/lots/{lot_id}",
    response_model=StockLotRead,
    summary="Get a stock lot",
)
def get_stock_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> StockLot:
    lot = db.query(StockLot).filter(StockLot.lot_id == lot_id).first()
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock lot {lot_id} not found.",
        )
    location = _get_location_or_404(lot.location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return lot


@router.put(
    "/lots/{lot_id}",
    response_model=StockLotRead,
    summary="Correct expiry date or lot number on a stock lot (Supervisor+)",
)
def update_stock_lot(
    lot_id: int,
    payload: StockLotUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> StockLot:
    lot = db.query(StockLot).filter(StockLot.lot_id == lot_id).first()
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock lot {lot_id} not found.",
        )
    location = _get_location_or_404(lot.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    old_expiry = lot.expiration_date
    old_lot_number = lot.lot_number

    if "expiration_date" in payload.model_fields_set:
        lot.expiration_date = payload.expiration_date
    if "lot_number" in payload.model_fields_set:
        lot.lot_number = payload.lot_number

    db.commit()
    db.refresh(lot)

    write_audit_event(
        db=db,
        actor=current_user.email,
        action="STOCK_LOT_UPDATED",
        entity_type="stock_lot",
        entity_id=str(lot_id),
        metadata={
            "old_expiration_date": str(old_expiry) if old_expiry else None,
            "new_expiration_date": str(lot.expiration_date) if lot.expiration_date else None,
            "old_lot_number": old_lot_number,
            "new_lot_number": lot.lot_number,
        },
    )
    return lot


@router.get(
    "/expiring",
    response_model=List[StockLotRead],
    summary="List expiring stock lots (Administrator only)",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def list_expiring_lots(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> List[StockLot]:
    """
    Cross-station expiry report — Administrator only.
    For station-scoped expiry, filter GET /inventory/locations/{id}/stock by expiration_date.
    """
    cutoff = date.today() + timedelta(days=days)
    return (
        db.query(StockLot)
        .filter(
            StockLot.expiration_date.is_not(None),
            StockLot.expiration_date <= cutoff,
        )
        .order_by(StockLot.expiration_date)
        .all()
    )


# ── Par Levels ────────────────────────────────────────────────────────────────

@router.post(
    "/par-levels",
    response_model=ParLevelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a par level",
)
def create_par_level(
    payload: ParLevelCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> ParLevel:
    location = _get_location_or_404(payload.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    if payload.compartment_id is not None:
        existing = db.query(ParLevel).filter(
            ParLevel.item_id        == payload.item_id,
            ParLevel.compartment_id == payload.compartment_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A par level already exists for item {payload.item_id} "
                    f"in compartment {payload.compartment_id} (par_id={existing.par_id})."
                ),
            )
    else:
        existing = db.query(ParLevel).filter(
            ParLevel.item_id        == payload.item_id,
            ParLevel.location_id    == payload.location_id,
            ParLevel.compartment_id.is_(None),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A par level already exists for item {payload.item_id} "
                    f"at location {payload.location_id} (par_id={existing.par_id})."
                ),
            )

    par = ParLevel(
        item_id=payload.item_id,
        location_id=payload.location_id,
        compartment_id=payload.compartment_id,
        min_quantity=payload.min_quantity,
        max_quantity=payload.max_quantity,
    )
    db.add(par)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A par level already exists for this item/location/compartment combination.",
        )
    db.refresh(par)
    logger.info(
        "Par level created: par_id=%s item_id=%s location_id=%s compartment_id=%s",
        par.par_id, par.item_id, par.location_id, par.compartment_id,
        extra={
            "action":      "PAR_LEVEL_CREATED",
            "entity_type": "par_level",
            "entity_id":   str(par.par_id),
        },
    )
    return par


@router.get(
    "/par-levels/{par_id}",
    response_model=ParLevelRead,
    summary="Get a par level",
)
def get_par_level(
    par_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> ParLevel:
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Par level {par_id} not found.",
        )
    location = _get_location_or_404(par.location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return par


# ── SUPPLY-B2: Stock summary ──────────────────────────────────────────────────

@router.get(
    "/locations/{location_id}/stock-summary",
    response_model=List[StockItemSummary],
    summary="Stock vs par summary for a location (SUPPLY-B2)",
)
def get_stock_summary(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[Dict[str, Any]]:
    """
    Aggregates stock lots by item, computes total quantity, matches par levels,
    and returns a status (OK / LOW / OUT / NO_PAR) for each item.
    """
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)

    lots = (
        db.query(StockLot)
        .filter(StockLot.location_id == location_id)
        .order_by(StockLot.expiration_date.asc().nulls_last())
        .all()
    )
    if not lots:
        return []

    # Group lots by item
    lots_by_item: Dict[int, List[StockLot]] = {}
    for lot in lots:
        lots_by_item.setdefault(lot.item_id, []).append(lot)

    # Fetch par levels (any active par at this location, across compartments)
    pars = (
        db.query(ParLevel)
        .filter(ParLevel.location_id == location_id, ParLevel.active == True)
        .all()
    )
    # Lowest min_quantity for the item across all compartments
    par_by_item: Dict[int, ParLevel] = {}
    for par in pars:
        existing = par_by_item.get(par.item_id)
        if existing is None or par.min_quantity < existing.min_quantity:
            par_by_item[par.item_id] = par

    # Fetch item metadata
    item_ids = list(lots_by_item.keys())
    items_map = {
        i.item_id: i
        for i in db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    }

    today     = date.today()
    warn_date = today + timedelta(days=30)
    result    = []

    for item_id, item_lots in lots_by_item.items():
        item = items_map.get(item_id)
        if not item:
            continue

        total_qty = sum(l.quantity for l in item_lots)
        par       = par_by_item.get(item_id)

        if par:
            if total_qty >= par.min_quantity:
                status_val = "OK"
            elif total_qty > 0:
                status_val = "LOW"
            else:
                status_val = "OUT"
        else:
            status_val = "NO_PAR"

        result.append({
            "item_id":          item_id,
            "item_name":        item.name,
            "item_category":    item.category.value,
            "total_quantity":   total_qty,
            "par_min":          par.min_quantity if par else None,
            "par_max":          par.max_quantity if par else None,
            "status":           status_val,
            "is_any_expiring":  any(
                l.expiration_date and l.expiration_date <= warn_date and not l.is_expired
                for l in item_lots
            ),
            "is_any_expired":   any(l.is_expired for l in item_lots),
            "lots":             item_lots,
        })

    result.sort(key=lambda x: (x["status"] not in ("OUT", "LOW"), x["item_name"]))
    return result


# ── SUPPLY-B1: Transfer stock ─────────────────────────────────────────────────

@router.post(
    "/transfer",
    response_model=StockTransferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Transfer stock between locations (SUPPLY-B1)",
)
def transfer_stock(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> StockTransferRead:
    """
    Moves `quantity` units of an item from one location to another.
    Deducts FIFO (earliest-expiring lot first) at the source.
    Creates a new lot at the destination with the source lot's expiry/lot number.
    Records a StockTransfer for history.

    Requires Supervisor+ and membership at both station(s).
    """
    from_loc = _get_location_or_404(payload.from_location_id, db)
    to_loc   = _get_location_or_404(payload.to_location_id, db)
    require_station_membership(from_loc.station_id, current_user, db)
    if from_loc.station_id != to_loc.station_id:
        require_station_membership(to_loc.station_id, current_user, db)

    item = db.query(Item).filter(Item.item_id == payload.item_id).first()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {payload.item_id} not found.")

    # FIFO: pull from earliest-expiring lots with remaining quantity
    source_lots = (
        db.query(StockLot)
        .filter(
            StockLot.location_id == payload.from_location_id,
            StockLot.item_id     == payload.item_id,
            StockLot.quantity    >  0,
        )
        .order_by(StockLot.expiration_date.asc().nulls_last())
        .all()
    )
    total_available = sum(l.quantity for l in source_lots)
    if total_available < payload.quantity:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Insufficient stock: {total_available} available, {payload.quantity} requested.",
        )

    remaining  = payload.quantity
    first_lot  = source_lots[0] if source_lots else None
    for lot in source_lots:
        if remaining <= 0:
            break
        deduct       = min(lot.quantity, remaining)
        lot.quantity -= deduct
        remaining    -= deduct

    # Create lot at destination
    dest_lot = StockLot(
        item_id         = payload.item_id,
        location_id     = payload.to_location_id,
        quantity        = payload.quantity,
        lot_number      = first_lot.lot_number      if first_lot else None,
        expiration_date = first_lot.expiration_date if first_lot else None,
    )
    db.add(dest_lot)

    # Record transfer
    transfer = StockTransfer(
        from_location_id    = payload.from_location_id,
        to_location_id      = payload.to_location_id,
        item_id             = payload.item_id,
        quantity            = payload.quantity,
        transferred_by      = current_user.email,
        notes               = payload.notes,
        lot_number          = first_lot.lot_number      if first_lot else None,
        lot_expiration_date = first_lot.expiration_date if first_lot else None,
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)

    logger.info(
        "Stock transferred: transfer_id=%s item_id=%s qty=%s from=%s to=%s",
        transfer.transfer_id, payload.item_id, payload.quantity,
        payload.from_location_id, payload.to_location_id,
        extra={
            "action":      "STOCK_TRANSFERRED",
            "entity_type": "stock_transfer",
            "entity_id":   str(transfer.transfer_id),
        },
    )

    return StockTransferRead(
        transfer_id          = transfer.transfer_id,
        from_location_id     = transfer.from_location_id,
        to_location_id       = transfer.to_location_id,
        from_location_label  = from_loc.label,
        to_location_label    = to_loc.label,
        item_id              = transfer.item_id,
        item_name            = item.name,
        quantity             = transfer.quantity,
        transferred_by       = transfer.transferred_by,
        notes                = transfer.notes,
        lot_number           = transfer.lot_number,
        lot_expiration_date  = transfer.lot_expiration_date,
        transferred_at       = transfer.created_at,
    )


# ── Transfer history ──────────────────────────────────────────────────────────

@router.get(
    "/locations/{location_id}/transfers",
    response_model=List[StockTransferRead],
    summary="Transfer history for a location (SUPPLY-F4)",
)
def list_location_transfers(
    location_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[StockTransferRead]:
    """
    Returns inbound and outbound transfers for this location, most recent first.
    """
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)

    from sqlalchemy import or_
    transfers = (
        db.query(StockTransfer)
        .filter(
            or_(
                StockTransfer.from_location_id == location_id,
                StockTransfer.to_location_id   == location_id,
            )
        )
        .order_by(StockTransfer.created_at.desc())
        .limit(limit)
        .all()
    )

    # Gather all location and item IDs for batch fetch
    loc_ids  = set()
    item_ids = set()
    for t in transfers:
        if t.from_location_id:
            loc_ids.add(t.from_location_id)
        loc_ids.add(t.to_location_id)
        item_ids.add(t.item_id)

    locs  = {l.location_id: l for l in db.query(InventoryLocation).filter(InventoryLocation.location_id.in_(loc_ids)).all()}
    items = {i.item_id: i     for i in db.query(Item).filter(Item.item_id.in_(item_ids)).all()}

    return [
        StockTransferRead(
            transfer_id          = t.transfer_id,
            from_location_id     = t.from_location_id,
            to_location_id       = t.to_location_id,
            from_location_label  = locs[t.from_location_id].label if t.from_location_id and t.from_location_id in locs else None,
            to_location_label    = locs[t.to_location_id].label if t.to_location_id in locs else str(t.to_location_id),
            item_id              = t.item_id,
            item_name            = items[t.item_id].name if t.item_id in items else str(t.item_id),
            quantity             = t.quantity,
            transferred_by       = t.transferred_by,
            notes                = t.notes,
            lot_number           = t.lot_number,
            lot_expiration_date  = t.lot_expiration_date,
            transferred_at       = t.created_at,
        )
        for t in transfers
    ]


# ── CSV receive template ──────────────────────────────────────────────────────

@router.get(
    "/receive-stock/template",
    summary="Download CSV template for bulk stock receive",
    response_class=StreamingResponse,
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def receive_stock_template() -> StreamingResponse:
    """Returns a downloadable CSV template with headers and one example row."""
    output = io.StringIO()
    writer = csv_mod.writer(output)
    writer.writerow(["item_name", "lot_number", "expiration_date", "quantity"])
    writer.writerow(["Gauze Bandage Various Sizes", "LOT-2026-001", "2027-06-30", "24"])
    writer.writerow(["Sterile Saline Solution", "LOT-2026-002", "2027-03-15", "12"])
    writer.writerow(["Gloves Medium", "", "", "50"])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=supply_room_receive_template.csv"},
    )


# ── PATCH /inventory/items/{item_id}/status — DMG-B1 ─────────────────────────

class _ItemStatusPatch(BaseModel):
    compartment_id: int
    is_damaged: bool


@router.patch(
    "/items/{item_id}/status",
    response_model=ParLevelRead,
    summary="Mark an item damaged/unavailable at a compartment (DMG-B1)",
)
def patch_item_status(
    item_id: int,
    payload: _ItemStatusPatch,
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> ParLevel:
    par = (
        db.query(ParLevel)
        .filter(
            ParLevel.item_id == item_id,
            ParLevel.compartment_id == payload.compartment_id,
        )
        .first()
    )
    if not par:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No par level for item {item_id} in compartment {payload.compartment_id}.",
        )
    location = _get_location_or_404(par.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    par.is_damaged = payload.is_damaged
    db.commit()
    db.refresh(par)

    write_audit_event(
        db=db,
        actor=current_user.email or current_user.oid,
        action="ITEM_DAMAGED" if payload.is_damaged else "ITEM_DAMAGE_CLEARED",
        entity_type="par_level",
        entity_id=str(par.par_id),
        metadata={
            "item_id": item_id,
            "compartment_id": payload.compartment_id,
            "is_damaged": payload.is_damaged,
        },
    )
    return par


# ── CSV bulk receive ──────────────────────────────────────────────────────────

@router.post(
    "/locations/{location_id}/receive-stock/csv",
    response_model=CsvReceiveResult,
    status_code=status.HTTP_200_OK,
    summary="Bulk receive stock from CSV file (SUPPLY-F3)",
)
async def receive_stock_csv(
    location_id: int,
    file: UploadFile = File(..., description="CSV file: item_name, lot_number, expiration_date, quantity"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> CsvReceiveResult:
    """
    Parses a CSV and creates stock lots at the given location.

    Columns: item_name (required), lot_number (optional), expiration_date (YYYY-MM-DD, optional), quantity (required integer > 0).
    Items are matched by exact name (case-insensitive). Unmatched rows are skipped with an error message.
    """
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)

    content    = await file.read()
    text       = content.decode("utf-8-sig")
    reader     = csv_mod.DictReader(io.StringIO(text))
    errors: List[Dict[str, Any]] = []
    lots_created: List[StockLot] = []
    row_num    = 1

    # Case-insensitive item name → item map
    all_items  = db.query(Item).filter(Item.active == True).all()
    item_map   = {i.name.lower(): i for i in all_items}

    for row in reader:
        row_num += 1
        raw_name = (row.get("item_name") or "").strip()
        raw_qty  = (row.get("quantity")  or "").strip()
        raw_exp  = (row.get("expiration_date") or "").strip()
        raw_lot  = (row.get("lot_number") or "").strip()

        if not raw_name:
            errors.append({"row": row_num, "item_name": "(blank)", "error": "item_name is required"})
            continue
        if not raw_qty:
            errors.append({"row": row_num, "item_name": raw_name, "error": "quantity is required"})
            continue

        try:
            qty = int(raw_qty)
            if qty < 1:
                raise ValueError
        except ValueError:
            errors.append({"row": row_num, "item_name": raw_name, "error": f"Invalid quantity: {raw_qty!r}"})
            continue

        item = item_map.get(raw_name.lower())
        if not item:
            errors.append({"row": row_num, "item_name": raw_name, "error": "Item not found in catalog"})
            continue

        expiry = None
        if raw_exp:
            try:
                expiry = date.fromisoformat(raw_exp)
            except ValueError:
                errors.append({"row": row_num, "item_name": raw_name, "error": f"Invalid date {raw_exp!r} — use YYYY-MM-DD"})
                continue

        lot = StockLot(
            item_id         = item.item_id,
            location_id     = location_id,
            quantity        = qty,
            lot_number      = raw_lot or None,
            expiration_date = expiry,
        )
        db.add(lot)
        lots_created.append(lot)

    if lots_created:
        db.commit()
        for lot in lots_created:
            db.refresh(lot)

        logger.info(
            "Bulk CSV stock receive: location_id=%s rows_imported=%s rows_skipped=%s",
            location_id, len(lots_created), len(errors),
            extra={
                "action":      "STOCK_CSV_RECEIVED",
                "entity_type": "stock_lot",
                "entity_id":   str(location_id),
            },
        )

    return CsvReceiveResult(
        rows_imported = len(lots_created),
        rows_skipped  = len(errors),
        errors        = errors,
        lots_created  = lots_created,
    )
