"""
routers/inventory.py
Inventory location, stock lot, and par level endpoints.

Endpoints:
  GET  /inventory/locations                     — list all locations (all roles)
  GET  /inventory/locations/{id}                — get a single location (all roles)
  GET  /inventory/locations/{id}/stock          — stock lots at a location (all roles)
  GET  /inventory/locations/{id}/par-levels     — par levels at a location (all roles)
  POST /inventory/lots                          — create a stock lot (Supervisor, Administrator)
  GET  /inventory/lots/{id}                     — get a stock lot (all roles)
  GET  /inventory/expiring                      — expiring lots (all roles)
  POST /inventory/par-levels                    — create a par level (Supervisor, Administrator)
  GET  /inventory/par-levels/{id}               — get a par level (all roles)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_RESPONDER, ROLE_SUPERVISOR
from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.par_level import ParLevelCreate, ParLevelRead
from ems_readykit.schemas.stock_lot import StockLotCreate, StockLotRead

router = APIRouter(prefix="/inventory", tags=["inventory"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)


# ── Inventory Locations (read-only) ──────────────────────────────────────────

@router.get(
    "/locations",
    response_model=List[InventoryLocationRead],
    summary="List inventory locations",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_locations(db: Session = Depends(get_db)) -> List[InventoryLocation]:
    """Returns all inventory locations. All authenticated roles."""
    return db.query(InventoryLocation).all()


@router.get(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Get an inventory location",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def get_location(location_id: int, db: Session = Depends(get_db)) -> InventoryLocation:
    """Returns a single inventory location by ID. Returns 404 if not found."""
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


@router.get(
    "/locations/{location_id}/stock",
    response_model=List[StockLotRead],
    summary="List stock lots at a location",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_location_stock(
    location_id: int, db: Session = Depends(get_db)
) -> List[StockLot]:
    """Returns all stock lots at a specific inventory location."""
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
    return db.query(StockLot).filter(StockLot.location_id == location_id).all()


@router.get(
    "/locations/{location_id}/par-levels",
    response_model=List[ParLevelRead],
    summary="List par levels at a location",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_location_par_levels(
    location_id: int, db: Session = Depends(get_db)
) -> List[ParLevel]:
    """Returns all par levels defined for a specific inventory location."""
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
    return db.query(ParLevel).filter(ParLevel.location_id == location_id).all()


# ── Stock Lots ────────────────────────────────────────────────────────────────

@router.post(
    "/lots",
    response_model=StockLotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stock lot",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def create_stock_lot(payload: StockLotCreate, db: Session = Depends(get_db)) -> StockLot:
    """
    Creates a new stock lot at the specified location.
    Returns 404 if the item or location does not exist.
    Requires Supervisor or Administrator.
    """
    location = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.location_id == payload.location_id)
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {payload.location_id} not found.",
        )

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
    return lot


@router.get(
    "/lots/{lot_id}",
    response_model=StockLotRead,
    summary="Get a stock lot",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def get_stock_lot(lot_id: int, db: Session = Depends(get_db)) -> StockLot:
    """Returns a single stock lot by ID. Returns 404 if not found."""
    lot = db.query(StockLot).filter(StockLot.lot_id == lot_id).first()
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock lot {lot_id} not found.",
        )
    return lot


@router.get(
    "/expiring",
    response_model=List[StockLotRead],
    summary="List expiring stock lots",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_expiring_lots(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Return lots expiring within this many days (1-365)",
    ),
    db: Session = Depends(get_db),
) -> List[StockLot]:
    """
    Returns all stock lots with an expiration date within the specified window.
    Covers FR-5: Expiration Management. All authenticated roles.
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
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def create_par_level(payload: ParLevelCreate, db: Session = Depends(get_db)) -> ParLevel:
    """
    Creates a par level for an item at a specific location.
    Returns 409 if a par level already exists for this item/location pair.
    Requires Supervisor or Administrator.
    """
    existing = (
        db.query(ParLevel)
        .filter(
            ParLevel.item_id == payload.item_id,
            ParLevel.location_id == payload.location_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A par level already exists for item {payload.item_id} "
                f"at location {payload.location_id} (par_id={existing.par_id}). "
                "Delete the existing par level before creating a new one."
            ),
        )

    par = ParLevel(
        item_id=payload.item_id,
        location_id=payload.location_id,
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
            detail=(
                f"A par level already exists for item {payload.item_id} "
                f"at location {payload.location_id}."
            ),
        )
    db.refresh(par)
    return par


@router.get(
    "/par-levels/{par_id}",
    response_model=ParLevelRead,
    summary="Get a par level",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def get_par_level(par_id: int, db: Session = Depends(get_db)) -> ParLevel:
    """Returns a single par level by ID. Returns 404 if not found."""
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Par level {par_id} not found.",
        )
    return par
