"""
routers/inventory.py
Inventory location, compartment, stock lot, and par level endpoints.

Refactor (Session B):
- Role constants imported from deps (REF-3)
- HTTP_422_UNPROCESSABLE_CONTENT replaces deprecated constant (REF-7)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_RESPONDER, ROLE_SUPERVISOR
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.compartment import CompartmentCreate, CompartmentRead
from ems_readykit.schemas.inventory_location import InventoryLocationRead, InventoryLocationCreate
from ems_readykit.schemas.par_level import ParLevelCreate, ParLevelRead
from ems_readykit.schemas.stock_lot import StockLotCreate, StockLotRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ── Inventory Locations ───────────────────────────────────────────────────────

@router.get(
    "/locations",
    response_model=List[InventoryLocationRead],
    summary="List inventory locations",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_locations(db: Session = Depends(get_db)) -> List[InventoryLocation]:
    return db.query(InventoryLocation).all()


@router.get(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Get an inventory location",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def get_location(location_id: int, db: Session = Depends(get_db)) -> InventoryLocation:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {location_id} not found.",
        )
    return location


@router.post(
    "/locations",
    response_model=InventoryLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a JUMP_BAG or EQUIPMENT inventory location",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def create_location(
    payload: InventoryLocationCreate,
    db: Session = Depends(get_db),
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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_location_stock(location_id: int, db: Session = Depends(get_db)) -> List[StockLot]:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_location_par_levels(location_id: int, db: Session = Depends(get_db)) -> List[ParLevel]:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {location_id} not found.",
        )
    return db.query(ParLevel).filter(ParLevel.location_id == location_id).all()


# ── Compartments ──────────────────────────────────────────────────────────────

@router.get(
    "/locations/{location_id}/compartments",
    response_model=List[CompartmentRead],
    summary="List compartments at a location",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_compartments(location_id: int, db: Session = Depends(get_db)) -> List[Compartment]:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {location_id} not found.",
        )
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
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def create_compartment(
    location_id: int,
    payload: CompartmentCreate,
    db: Session = Depends(get_db),
) -> Compartment:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == location_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory location {location_id} not found.",
        )

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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def get_compartment(compartment_id: int, db: Session = Depends(get_db)) -> Compartment:
    compartment = db.query(Compartment).filter(
        Compartment.compartment_id == compartment_id
    ).first()
    if not compartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compartment {compartment_id} not found.",
        )
    return compartment


# ── Stock Lots ────────────────────────────────────────────────────────────────

@router.post(
    "/lots",
    response_model=StockLotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stock lot",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def create_stock_lot(payload: StockLotCreate, db: Session = Depends(get_db)) -> StockLot:
    location = db.query(InventoryLocation).filter(
        InventoryLocation.location_id == payload.location_id
    ).first()
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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def get_stock_lot(lot_id: int, db: Session = Depends(get_db)) -> StockLot:
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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_expiring_lots(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> List[StockLot]:
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
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def create_par_level(payload: ParLevelCreate, db: Session = Depends(get_db)) -> ParLevel:
    if payload.compartment_id is not None:
        existing = db.query(ParLevel).filter(
            ParLevel.item_id       == payload.item_id,
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
            ParLevel.item_id       == payload.item_id,
            ParLevel.location_id   == payload.location_id,
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
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def get_par_level(par_id: int, db: Session = Depends(get_db)) -> ParLevel:
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Par level {par_id} not found.",
        )
    return par
