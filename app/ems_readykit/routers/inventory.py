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

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.stock_lot import StockLot
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
from ems_readykit.schemas.stock_lot import StockLotCreate, StockLotRead

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
