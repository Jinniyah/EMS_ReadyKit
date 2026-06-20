"""
routers/inventory.py
Inventory location, compartment, stock lot, and par level endpoints.

Session C (ACC-B8): Station membership enforced on inventory endpoints.
  - GET  /inventory/locations            -- requires station_id param (enforced) or Admin only
  - GET  /inventory/locations/{id}       -- derives station from location, enforces membership
  - GET  /inventory/locations/{id}/stock        -- same
  - GET  /inventory/locations/{id}/par-levels   -- same
  - GET  /inventory/locations/{id}/compartments -- same
  - POST /inventory/locations            -- enforces membership on payload.station_id
  - POST /inventory/lots                 -- enforces membership via location.station_id
  - POST /inventory/par-levels           -- enforces membership via location.station_id
  - POST /inventory/locations/{id}/compartments -- same

Design note: GET /inventory/locations without ?station_id is restricted to
Administrators. All other roles must supply a station_id they are a member of.
This protects station data while allowing the check wizard to fetch location
data by passing the known station_id.

CQ-B4: _ItemStatusPatch moved to schemas/inventory.py as ItemStatusPatch.
CQ-B7: create_par_level pre-check refined.
  When compartment_id is set, rely on the DB unique constraint + IntegrityError
  (eliminates TOCTOU race). When compartment_id is NULL, a pre-check is still
  required because most SQL databases do not consider NULL==NULL in unique
  constraints, so two location-level pars for the same item would both succeed
  without a pre-check.

PAR-B1 (Session AF): create_par_level reactivates a matching soft-deactivated
row instead of inserting a duplicate, for the same reason as
assign_item_to_compartment in admin_items.py -- the uq_par_item_compartment
unique constraint has no concept of `active`, so re-creating a par level for
an (item_id, compartment_id) pair that was previously removed always hit the
IntegrityError fallback and reported "already assigned" even with no active
duplicate present. See admin_items.py for the parallel fix and full rationale.
"""

from __future__ import annotations

import csv as csv_mod
import io
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCheckType
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.stock_transfer import StockTransfer
from ems_readykit.routers.deps import (
    ADMIN_ONLY,
    ALL_ROLES,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.compartment import CompartmentCreate, CompartmentRead
from ems_readykit.schemas.inventory import ItemStatusPatch
from ems_readykit.schemas.inventory_location import (
    InventoryLocationCreate,
    InventoryLocationRead,
    LocationRetire,
)
from ems_readykit.schemas.par_level import ParLevelCreate, ParLevelRead
from ems_readykit.schemas.stock_lot import (
    LotRetire,
    StockLotCreate,
    StockLotRead,
    StockLotUpdate,
)
from ems_readykit.schemas.stock_transfer import (
    CsvReceiveResult,
    StockItemSummary,
    StockTransferRead,
)
from ems_readykit.schemas.supply_catalog import (
    SupplyCatalogCountPatch,
    SupplyCatalogItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _get_location_or_404(location_id: int, db: Session) -> InventoryLocation:
    location = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.location_id == location_id)
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {location_id} not found.",
        )
    return location


# -- Inventory Locations -------------------------------------------------------


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
            .filter(
                InventoryLocation.station_id == station_id,
                InventoryLocation.retired_at.is_(None),
            )
            .all()
        )

    # No station_id supplied -- Administrator only
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
    if payload.location_type in (
        LocationType.VEHICLE,
        LocationType.STATION_SUPPLY_ROOM,
    ):
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
        location.location_id,
        location.location_type,
        location.station_id,
        extra={
            "action": "LOCATION_CREATED",
            "entity_type": "inventory_location",
            "entity_id": str(location.location_id),
        },
    )
    return location


@router.patch(
    "/locations/{location_id}/retire",
    response_model=InventoryLocationRead,
    summary="Permanently retire a location (RET-B2) -- Administrator only",
)
def retire_location(
    location_id: int,
    payload: LocationRetire,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> InventoryLocation:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)
    if location.retired_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location {location_id} is already retired.",
        )
    actor = current_user.email or current_user.name
    location.retired_at = datetime.now(timezone.utc)
    location.retired_by = actor
    location.retirement_reason = payload.retirement_reason
    db.commit()
    db.refresh(location)
    write_audit_event(
        db,
        actor=actor,
        action="LOCATION_RETIRED",
        entity_type="inventory_location",
        entity_id=str(location_id),
        metadata={"reason": payload.retirement_reason, "label": location.label},
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
    return (
        db.query(ParLevel)
        .filter(
            ParLevel.location_id == location_id,
            ParLevel.active,
        )
        .all()
    )


# -- Compartments --------------------------------------------------------------


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
        compartment.compartment_id,
        compartment.name,
        location_id,
        extra={
            "action": "COMPARTMENT_CREATED",
            "entity_type": "compartment",
            "entity_id": str(compartment.compartment_id),
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
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )
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
    """Edit a compartment's name, descriptor, sort order, or restriction note."""
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )
    if not compartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compartment {compartment_id} not found.",
        )
    location = _get_location_or_404(compartment.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    name_conflict = (
        db.query(Compartment)
        .filter(
            Compartment.location_id == compartment.location_id,
            Compartment.name == payload.name,
            Compartment.compartment_id != compartment_id,
        )
        .first()
    )
    if name_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A compartment named '{payload.name}' already exists at this location.",
        )

    compartment.name = payload.name
    compartment.location_descriptor = payload.location_descriptor
    compartment.sort_order = payload.sort_order
    compartment.restriction_note = payload.restriction_note
    compartment.als_only = payload.als_only
    compartment.active = payload.active

    db.commit()
    db.refresh(compartment)
    logger.info(
        "Compartment updated: compartment_id=%s name=%r",
        compartment.compartment_id,
        compartment.name,
        extra={
            "action": "COMPARTMENT_UPDATED",
            "entity_type": "compartment",
            "entity_id": str(compartment.compartment_id),
        },
    )
    return compartment


# -- Stock Lots ----------------------------------------------------------------


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

    transfer = StockTransfer(
        from_location_id=None,
        to_location_id=payload.location_id,
        item_id=payload.item_id,
        quantity=payload.quantity,
        transferred_by=current_user.email or current_user.name,
        lot_number=payload.lot_number,
        lot_expiration_date=payload.expiration_date,
        notes="Received into supply room",
    )
    db.add(transfer)

    db.commit()
    db.refresh(lot)
    logger.info(
        "Stock lot created: lot_id=%s item_id=%s location_id=%s",
        lot.lot_id,
        lot.item_id,
        lot.location_id,
        extra={
            "action": "STOCK_LOT_CREATED",
            "entity_type": "stock_lot",
            "entity_id": str(lot.lot_id),
        },
    )
    return lot


@router.get(
    "/lots/retired",
    response_model=List[StockLotRead],
    summary="List retired stock lots at a location (RET-B6) -- Supervisor+",
)
def list_retired_lots(
    location_id: int = Query(..., gt=0, description="Location to query"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[StockLot]:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)
    return (
        db.query(StockLot)
        .filter(
            StockLot.location_id == location_id,
            StockLot.retired_at.isnot(None),
        )
        .order_by(StockLot.retired_at.desc())
        .all()
    )


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
            "new_expiration_date": (
                str(lot.expiration_date) if lot.expiration_date else None
            ),
            "old_lot_number": old_lot_number,
            "new_lot_number": lot.lot_number,
        },
    )
    return lot


@router.patch(
    "/lots/{lot_id}/retire",
    response_model=StockLotRead,
    summary="Retire (dispose) a stock lot (RET-B5) -- Supervisor+",
)
def retire_stock_lot(
    lot_id: int,
    payload: LotRetire,
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
    if lot.retired_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock lot {lot_id} is already retired.",
        )
    actor = current_user.email or current_user.name
    lot.retired_at = datetime.now(timezone.utc)
    lot.retired_by = actor
    lot.retirement_reason = payload.retirement_reason
    lot.quantity = 0
    db.commit()
    db.refresh(lot)
    write_audit_event(
        db,
        actor=actor,
        action="STOCK_LOT_RETIRED",
        entity_type="stock_lot",
        entity_id=str(lot_id),
        metadata={
            "reason": payload.retirement_reason,
            "item_id": lot.item_id,
            "location_id": lot.location_id,
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
    """Cross-station expiry report. For station-scoped expiry, filter /locations/{id}/stock."""
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


# -- Par Levels ----------------------------------------------------------------


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
    """
    CQ-B7: Duplicate detection strategy depends on whether compartment_id is set.

    Compartment-scoped pars (compartment_id set):
      The DB unique constraint uq_par_item_compartment on (item_id, compartment_id)
      catches duplicates at INSERT time. We rely on IntegrityError → 409, which
      eliminates the TOCTOU race between a pre-check query and the INSERT.

    Location-level pars (compartment_id NULL):
      SQL NULL != NULL in unique constraints, so two rows with the same item_id
      and compartment_id=NULL are not considered duplicates by the DB. A pre-check
      query is required here to detect the duplicate before attempting the INSERT.

    PAR-B1: Before inserting a compartment-scoped par, check for a matching
    soft-deactivated row and reactivate it instead. Without this, re-adding an
    item that was previously removed from this exact compartment always fails
    with the IntegrityError "already exists" fallback below, even though no
    active duplicate exists -- the unique constraint doesn't know about `active`.
    """
    location = _get_location_or_404(payload.location_id, db)
    require_station_membership(location.station_id, current_user, db)

    # Pre-check only for location-level pars (NULL compartment_id): the DB
    # unique constraint does not catch NULL=NULL duplicates.
    if payload.compartment_id is None:
        existing = (
            db.query(ParLevel)
            .filter(
                ParLevel.item_id == payload.item_id,
                ParLevel.location_id == payload.location_id,
                ParLevel.compartment_id.is_(None),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A par level already exists for item {payload.item_id} "
                    f"at location {payload.location_id} (par_id={existing.par_id})."
                ),
            )
    else:
        # PAR-B1: reactivate a previously-removed compartment-scoped par
        # rather than inserting a duplicate the unique constraint would reject.
        inactive_match = (
            db.query(ParLevel)
            .filter(
                ParLevel.item_id == payload.item_id,
                ParLevel.compartment_id == payload.compartment_id,
                ParLevel.active.is_(False),
            )
            .first()
        )
        if inactive_match:
            inactive_match.location_id = payload.location_id
            inactive_match.min_quantity = payload.min_quantity
            inactive_match.max_quantity = payload.max_quantity
            inactive_match.active = True
            inactive_match.deactivated_at = None
            inactive_match.deactivation_reason = None
            inactive_match.priority_check = payload.priority_check
            inactive_match.priority_question = payload.priority_question
            inactive_match.is_damaged = False
            db.commit()
            db.refresh(inactive_match)
            write_audit_event(
                db,
                actor=current_user.email or current_user.user_id,
                action="PAR_REACTIVATED",
                entity_type="par_level",
                entity_id=str(inactive_match.par_id),
                metadata={
                    "item_id": payload.item_id,
                    "compartment_id": payload.compartment_id,
                    "min_quantity": payload.min_quantity,
                    "max_quantity": payload.max_quantity,
                },
            )
            logger.info(
                "Par level reactivated: par_id=%s item_id=%s location_id=%s compartment_id=%s",
                inactive_match.par_id,
                inactive_match.item_id,
                inactive_match.location_id,
                inactive_match.compartment_id,
                extra={
                    "action": "PAR_REACTIVATED",
                    "entity_type": "par_level",
                    "entity_id": str(inactive_match.par_id),
                },
            )
            return inactive_match

    par = ParLevel(
        item_id=payload.item_id,
        location_id=payload.location_id,
        compartment_id=payload.compartment_id,
        min_quantity=payload.min_quantity,
        max_quantity=payload.max_quantity,
        priority_check=payload.priority_check,
        priority_question=payload.priority_question,
    )
    db.add(par)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A par level already exists for item {payload.item_id} "
                "at this location/compartment combination."
            ),
        )
    db.refresh(par)
    logger.info(
        "Par level created: par_id=%s item_id=%s location_id=%s compartment_id=%s",
        par.par_id,
        par.item_id,
        par.location_id,
        par.compartment_id,
        extra={
            "action": "PAR_LEVEL_CREATED",
            "entity_type": "par_level",
            "entity_id": str(par.par_id),
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


class _ParLevelDeactivate(BaseModel):
    reason: Optional[str] = None


@router.patch(
    "/par-levels/{par_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-deactivate a par level (B-E9) -- Supervisor+",
)
def deactivate_par_level(
    par_id: int,
    payload: _ParLevelDeactivate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> None:
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Par level {par_id} not found.",
        )
    location = _get_location_or_404(par.location_id, db)
    require_station_membership(location.station_id, current_user, db)
    if not par.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Par level is already inactive.",
        )
    par.active = False
    par.deactivated_at = datetime.now(timezone.utc)
    par.deactivation_reason = payload.reason or None
    db.commit()
    write_audit_event(
        db,
        actor=current_user.email or current_user.user_id,
        action="PAR_DEACTIVATED",
        entity_type="par_level",
        entity_id=str(par_id),
        metadata={
            "item_id": par.item_id,
            "compartment_id": par.compartment_id,
            "reason": payload.reason,
        },
    )


# -- SUPPLY-B2: Stock summary --------------------------------------------------


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

    lots_by_item: Dict[int, List[StockLot]] = {}
    for lot in lots:
        lots_by_item.setdefault(lot.item_id, []).append(lot)

    pars = (
        db.query(ParLevel)
        .filter(ParLevel.location_id == location_id, ParLevel.active)
        .all()
    )
    par_by_item: Dict[int, ParLevel] = {}
    for par in pars:
        existing = par_by_item.get(par.item_id)
        if existing is None or par.min_quantity < existing.min_quantity:
            par_by_item[par.item_id] = par

    item_ids = list(lots_by_item.keys())
    items_map = {
        i.item_id: i for i in db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    }

    today = date.today()
    warn_date = today + timedelta(days=30)
    result = []

    for item_id, item_lots in lots_by_item.items():
        item = items_map.get(item_id)
        if not item:
            continue

        total_qty = sum(lot.quantity for lot in item_lots)
        par = par_by_item.get(item_id)

        if par:
            if total_qty >= par.min_quantity:
                status_val = "OK"
            elif total_qty > 0:
                status_val = "LOW"
            else:
                status_val = "OUT"
        else:
            status_val = "NO_PAR"

        result.append(
            {
                "item_id": item_id,
                "item_name": item.name,
                "item_category": item.category.value,
                "total_quantity": total_qty,
                "par_min": par.min_quantity if par else None,
                "par_max": par.max_quantity if par else None,
                "status": status_val,
                "is_any_expiring": any(
                    lot.expiration_date
                    and lot.expiration_date <= warn_date
                    and not lot.is_expired
                    for lot in item_lots
                ),
                "is_any_expired": any(lot.is_expired for lot in item_lots),
                "lots": item_lots,
            }
        )

    result.sort(key=lambda x: (x["status"] not in ("OUT", "LOW"), x["item_name"]))
    return result


# -- Transfer history ----------------------------------------------------------
# SR-B5: POST /inventory/transfer (restock-vehicle action) removed.
# Supply room stock is decremented automatically when a vehicle check is
# submitted (SR-B4). The transfers table is retained for the audit trail.


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
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)

    transfers = (
        db.query(StockTransfer)
        .filter(
            or_(
                StockTransfer.from_location_id == location_id,
                StockTransfer.to_location_id == location_id,
            )
        )
        .order_by(StockTransfer.created_at.desc())
        .limit(limit)
        .all()
    )

    loc_ids = set()
    item_ids = set()
    for t in transfers:
        if t.from_location_id:
            loc_ids.add(t.from_location_id)
        loc_ids.add(t.to_location_id)
        item_ids.add(t.item_id)

    locs = {
        loc.location_id: loc
        for loc in db.query(InventoryLocation)
        .filter(InventoryLocation.location_id.in_(loc_ids))
        .all()
    }
    items = {
        i.item_id: i for i in db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    }

    return [
        StockTransferRead(
            transfer_id=t.transfer_id,
            from_location_id=t.from_location_id,
            to_location_id=t.to_location_id,
            from_location_label=(
                locs[t.from_location_id].label
                if t.from_location_id and t.from_location_id in locs
                else None
            ),
            to_location_label=(
                locs[t.to_location_id].label
                if t.to_location_id in locs
                else str(t.to_location_id)
            ),
            item_id=t.item_id,
            item_name=items[t.item_id].name if t.item_id in items else str(t.item_id),
            quantity=t.quantity,
            transferred_by=t.transferred_by,
            notes=t.notes,
            lot_number=t.lot_number,
            lot_expiration_date=t.lot_expiration_date,
            transferred_at=t.created_at,
        )
        for t in transfers
    ]


# -- CSV receive template ------------------------------------------------------


@router.get(
    "/receive-stock/template",
    summary="Download CSV template for bulk stock receive",
    response_class=StreamingResponse,
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def receive_stock_template() -> StreamingResponse:
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
        headers={
            "Content-Disposition": "attachment; filename=supply_room_receive_template.csv"
        },
    )


# -- DMG-B1: Mark/clear item damaged at compartment ---------------------------


@router.patch(
    "/items/{item_id}/status",
    response_model=ParLevelRead,
    summary="Mark an item damaged/unavailable at a compartment (DMG-B1)",
)
def patch_item_status(
    item_id: int,
    payload: ItemStatusPatch,
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
        actor=current_user.email or current_user.user_id,
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


# -- CSV bulk receive ----------------------------------------------------------


@router.post(
    "/locations/{location_id}/receive-stock/csv",
    response_model=CsvReceiveResult,
    status_code=status.HTTP_200_OK,
    summary="Bulk receive stock from CSV file (SUPPLY-F3)",
)
async def receive_stock_csv(
    location_id: int,
    file: UploadFile = File(
        ..., description="CSV file: item_name, lot_number, expiration_date, quantity"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> CsvReceiveResult:
    location = _get_location_or_404(location_id, db)
    require_station_membership(location.station_id, current_user, db)

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv_mod.DictReader(io.StringIO(text))
    errors: List[Dict[str, Any]] = []
    lots_created: List[StockLot] = []
    row_num = 1

    all_items = db.query(Item).filter(Item.active).all()
    item_map = {i.name.lower(): i for i in all_items}

    for row in reader:
        row_num += 1
        raw_name = (row.get("item_name") or "").strip()
        raw_qty = (row.get("quantity") or "").strip()
        raw_exp = (row.get("expiration_date") or "").strip()
        raw_lot = (row.get("lot_number") or "").strip()

        if not raw_name:
            errors.append(
                {
                    "row": row_num,
                    "item_name": "(blank)",
                    "error": "item_name is required",
                }
            )
            continue
        if not raw_qty:
            errors.append(
                {"row": row_num, "item_name": raw_name, "error": "quantity is required"}
            )
            continue

        try:
            qty = int(raw_qty)
            if qty < 1:
                raise ValueError
        except ValueError:
            errors.append(
                {
                    "row": row_num,
                    "item_name": raw_name,
                    "error": f"Invalid quantity: {raw_qty!r}",
                }
            )
            continue

        item = item_map.get(raw_name.lower())
        if not item:
            errors.append(
                {
                    "row": row_num,
                    "item_name": raw_name,
                    "error": "Item not found in catalog",
                }
            )
            continue

        expiry = None
        if raw_exp:
            try:
                expiry = date.fromisoformat(raw_exp)
            except ValueError:
                errors.append(
                    {
                        "row": row_num,
                        "item_name": raw_name,
                        "error": f"Invalid date {raw_exp!r} -- use YYYY-MM-DD",
                    }
                )
                continue

        lot = StockLot(
            item_id=item.item_id,
            location_id=location_id,
            quantity=qty,
            lot_number=raw_lot or None,
            expiration_date=expiry,
        )
        db.add(lot)
        lots_created.append(lot)

    if lots_created:
        db.commit()
        for lot in lots_created:
            db.refresh(lot)

        for lot in lots_created:
            db.add(
                StockTransfer(
                    from_location_id=None,
                    to_location_id=location_id,
                    item_id=lot.item_id,
                    quantity=lot.quantity,
                    transferred_by=current_user.email or current_user.name,
                    lot_number=lot.lot_number,
                    lot_expiration_date=lot.expiration_date,
                    notes="Received via CSV import",
                )
            )
        db.commit()

        logger.info(
            "Bulk CSV stock receive: location_id=%s rows_imported=%s rows_skipped=%s",
            location_id,
            len(lots_created),
            len(errors),
            extra={
                "action": "STOCK_CSV_RECEIVED",
                "entity_type": "stock_lot",
                "entity_id": str(location_id),
            },
        )

    return CsvReceiveResult(
        rows_imported=len(lots_created),
        rows_skipped=len(errors),
        errors=errors,
        lots_created=lots_created,
    )


# -- SR-B1: Station supply catalog ---------------------------------------------


@router.get(
    "/supply-catalog",
    response_model=List[SupplyCatalogItem],
    summary="Station supply catalog with on-hand counts (SR-B1)",
)
def get_supply_catalog(
    station_id: int = Query(
        ..., gt=0, description="Station to retrieve supply catalog for"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[SupplyCatalogItem]:
    """
    Returns all station-supply items (station_supply=True, check_type != FUNCTIONAL)
    with their on-hand quantity at the station's supply room.
    """
    require_station_membership(station_id, current_user, db)

    supply_room = (
        db.query(InventoryLocation)
        .filter(
            InventoryLocation.station_id == station_id,
            InventoryLocation.location_type == LocationType.STATION_SUPPLY_ROOM,
        )
        .first()
    )
    if not supply_room:
        return []

    items = (
        db.query(Item)
        .filter(
            Item.station_supply,
            Item.check_type != ItemCheckType.FUNCTIONAL,
            Item.active,
        )
        .order_by(Item.name.asc())
        .all()
    )
    if not items:
        return []

    item_ids = [i.item_id for i in items]

    lots = (
        db.query(StockLot)
        .filter(
            StockLot.location_id == supply_room.location_id,
            StockLot.item_id.in_(item_ids),
            StockLot.retired_at.is_(None),
        )
        .order_by(StockLot.expiration_date.asc().nulls_last())
        .all()
    )
    lots_by_item: Dict[int, List[StockLot]] = {}
    for lot in lots:
        lots_by_item.setdefault(lot.item_id, []).append(lot)

    par_rows = (
        db.query(ParLevel, Compartment)
        .outerjoin(Compartment, Compartment.compartment_id == ParLevel.compartment_id)
        .filter(
            ParLevel.location_id == supply_room.location_id,
            ParLevel.item_id.in_(item_ids),
            ParLevel.active.is_(True),
        )
        .order_by(
            Compartment.sort_order.asc().nulls_last(), ParLevel.min_quantity.asc()
        )
        .all()
    )

    par_min_by_item: Dict[int, int] = {}
    compartment_by_item: Dict[int, tuple] = {}
    for par, comp in par_rows:
        if (
            par.item_id not in par_min_by_item
            or par.min_quantity < par_min_by_item[par.item_id]
        ):
            par_min_by_item[par.item_id] = par.min_quantity
        if par.item_id not in compartment_by_item and comp is not None:
            compartment_by_item[par.item_id] = (comp.compartment_id, comp.name)

    vehicle_location_ids = db.query(InventoryLocation.location_id).filter(
        InventoryLocation.station_id == station_id,
        InventoryLocation.location_type == LocationType.VEHICLE,
        InventoryLocation.retired_at.is_(None),
    )
    damaged_pars = (
        db.query(ParLevel.item_id)
        .filter(
            ParLevel.location_id.in_(vehicle_location_ids),
            ParLevel.item_id.in_(item_ids),
            ParLevel.is_damaged.is_(True),
        )
        .distinct()
        .all()
    )
    damaged_items: set = {row.item_id for row in damaged_pars}

    return [
        SupplyCatalogItem(
            item_id=item.item_id,
            item_name=item.name,
            unit_of_measure=item.unit_of_measure,
            check_type=item.check_type.value,
            on_hand=sum(lot.quantity for lot in lots_by_item.get(item.item_id, [])),
            par_min=par_min_by_item.get(item.item_id),
            lots=lots_by_item.get(item.item_id, []),
            compartment_id=compartment_by_item.get(item.item_id, (None, None))[0],
            compartment_name=compartment_by_item.get(item.item_id, (None, None))[1],
            is_damaged=item.item_id in damaged_items,
        )
        for item in items
    ]


# -- SR-B2: Correct supply room on-hand count ----------------------------------


@router.patch(
    "/supply-catalog/items/{item_id}/count",
    response_model=SupplyCatalogItem,
    summary="Correct on-hand count for a supply-room item (SR-B2)",
)
def patch_supply_catalog_count(
    item_id: int,
    payload: SupplyCatalogCountPatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> SupplyCatalogItem:
    """
    Sets the absolute on-hand count for an item in a supply room.
    Deducts FIFO (oldest lot first) for decreases.
    Creates an adjustment lot (no lot number, no expiry) for increases.
    """
    location = _get_location_or_404(payload.location_id, db)
    if location.location_type != LocationType.STATION_SUPPLY_ROOM:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="location_id must reference a STATION_SUPPLY_ROOM.",
        )
    require_station_membership(location.station_id, current_user, db)

    item = db.query(Item).filter(Item.item_id == item_id, Item.active).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found.",
        )

    current_lots = (
        db.query(StockLot)
        .filter(
            StockLot.location_id == payload.location_id,
            StockLot.item_id == item_id,
            StockLot.quantity > 0,
        )
        .order_by(StockLot.expiration_date.asc().nulls_last())
        .all()
    )
    old_qty = sum(lot.quantity for lot in current_lots)
    new_qty = payload.quantity

    if new_qty < old_qty:
        to_deduct = old_qty - new_qty
        for lot in current_lots:
            if to_deduct <= 0:
                break
            take = min(lot.quantity, to_deduct)
            lot.quantity -= take
            to_deduct -= take
    elif new_qty > old_qty:
        db.add(
            StockLot(
                item_id=item_id,
                location_id=payload.location_id,
                quantity=new_qty - old_qty,
                lot_number=None,
                expiration_date=None,
            )
        )

    db.flush()

    write_audit_event(
        db=db,
        actor=current_user.email,
        action="SUPPLY_COUNT_CORRECTED",
        entity_type="item",
        entity_id=str(item_id),
        metadata={
            "location_id": payload.location_id,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "comment": payload.comment,
        },
    )
    db.commit()

    updated_lots = (
        db.query(StockLot)
        .filter(
            StockLot.location_id == payload.location_id,
            StockLot.item_id == item_id,
            StockLot.quantity > 0,
        )
        .order_by(StockLot.expiration_date.asc().nulls_last())
        .all()
    )
    par_levels = (
        db.query(ParLevel)
        .filter(
            ParLevel.location_id == payload.location_id,
            ParLevel.item_id == item_id,
            ParLevel.active,
        )
        .all()
    )
    par_min = min((p.min_quantity for p in par_levels), default=None)

    return SupplyCatalogItem(
        item_id=item.item_id,
        item_name=item.name,
        unit_of_measure=item.unit_of_measure,
        check_type=item.check_type.value,
        on_hand=sum(lot.quantity for lot in updated_lots),
        par_min=par_min,
        lots=updated_lots,
    )
