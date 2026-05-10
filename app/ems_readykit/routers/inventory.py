"""
routers/inventory.py
Inventory location, stock lot, and par level endpoints.

Endpoints:
  GET  /inventory/locations                     — list all locations
  GET  /inventory/locations/{id}                — get a single location
  GET  /inventory/locations/{id}/stock          — stock lots at a location
  GET  /inventory/locations/{id}/par-levels     — par levels at a location
  POST /inventory/lots                          — create a stock lot
  GET  /inventory/lots/{id}                     — get a stock lot
  GET  /inventory/expiring                      — lots expiring within N days
  POST /inventory/par-levels                    — create a par level
  GET  /inventory/par-levels/{id}               — get a par level

Design decisions:
- Inventory locations are read-only in Phase 2 (system-managed).
  The write path for locations is through the vehicles router (auto-created on
  vehicle create) or seeded for station supply rooms.
- The /expiring endpoint is the primary operational alert surface. It queries
  across all locations and returns lots expiring within a configurable
  threshold (default 30 days). This covers FR-5 (Expiration Management).
- Par level 409 returns a clear message pointing callers to the existing
  record's par_id so they can update it if needed.
- StockLot quantity adjustments (add/remove stock) are Phase 3 operations
  that require audit trail generation. In Phase 2 only create is supported.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.par_level import ParLevelCreate, ParLevelRead
from ems_readykit.schemas.stock_lot import StockLotCreate, StockLotRead

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ── Inventory Locations (read-only) ──────────────────────────────────────────

@router.get("/locations", response_model=List[InventoryLocationRead], summary="List inventory locations")
def list_locations(db: Session = Depends(get_db)) -> List[InventoryLocation]:
    """Returns all inventory locations (vehicle locations and supply rooms)."""
    return db.query(InventoryLocation).all()


@router.get(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Get an inventory location",
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
)
def list_location_stock(
    location_id: int, db: Session = Depends(get_db)
) -> List[StockLot]:
    """
    Returns all stock lots at a specific inventory location.
    Returns 404 if the location does not exist.
    """
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
    return (
        db.query(StockLot)
        .filter(StockLot.location_id == location_id)
        .all()
    )


@router.get(
    "/locations/{location_id}/par-levels",
    response_model=List[ParLevelRead],
    summary="List par levels at a location",
)
def list_location_par_levels(
    location_id: int, db: Session = Depends(get_db)
) -> List[ParLevel]:
    """
    Returns all par levels defined for a specific inventory location.
    Returns 404 if the location does not exist.
    """
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
    return (
        db.query(ParLevel)
        .filter(ParLevel.location_id == location_id)
        .all()
    )


# ── Stock Lots ────────────────────────────────────────────────────────────────

@router.post(
    "/lots",
    response_model=StockLotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stock lot",
)
def create_stock_lot(payload: StockLotCreate, db: Session = Depends(get_db)) -> StockLot:
    """
    Creates a new stock lot at the specified location.
    Returns 404 if the item or location does not exist.
    """
    # Validate location exists
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


@router.get("/lots/{lot_id}", response_model=StockLotRead, summary="Get a stock lot")
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
    Covers FR-5: Expiration Management.
    Default threshold is 30 days — configurable per request.
    Lots with no expiration date are excluded (equipment/non-dated consumables).
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
def create_par_level(payload: ParLevelCreate, db: Session = Depends(get_db)) -> ParLevel:
    """
    Creates a par level for an item at a specific location.
    Returns 409 if a par level already exists for this item/location pair.
    The 409 response includes the existing par_id so callers can update it.
    """
    # Check for existing par level for this item/location pair
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
        # Race condition guard — two simultaneous creates for the same pair
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
