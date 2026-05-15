"""
routers/items.py
Item catalog CRUD endpoints.

Endpoints:
  GET  /items         — list items (all authenticated roles)
  POST /items         — create an item (Supervisor, Administrator)
  GET  /items/{id}    — get a single item (all authenticated roles)
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_RESPONDER, ROLE_SUPERVISOR
from ems_readykit.core.database import get_db
from ems_readykit.models.item import Item, ItemCategory
from ems_readykit.routers.deps import require_role
from ems_readykit.schemas.item import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])

_ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
_SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)


@router.get(
    "",
    response_model=List[ItemRead],
    summary="List items",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def list_items(
    active: bool = Query(default=True, description="Filter by active status"),
    category: Optional[ItemCategory] = Query(
        default=None, description="Filter by category (Medication, Consumable, Equipment)"
    ),
    controlled_substance: Optional[bool] = Query(
        default=None, description="Filter by controlled substance status"
    ),
    db: Session = Depends(get_db),
) -> List[Item]:
    """
    Returns items matching the supplied filters. All authenticated roles.
    Multiple filters are ANDed together.
    """
    query = db.query(Item).filter(Item.active == active)
    if category is not None:
        query = query.filter(Item.category == category)
    if controlled_substance is not None:
        query = query.filter(Item.controlled_substance == controlled_substance)
    return query.order_by(Item.name).all()


@router.post(
    "",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
    dependencies=[Depends(require_role(*_SUPERVISOR_PLUS))],
)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    """
    Creates a new item in the catalog. Requires Supervisor or Administrator.
    Returns 409 if an item with the same name already exists.
    """
    item = Item(
        name=payload.name,
        category=payload.category,
        check_type=payload.check_type,
        controlled_substance=payload.controlled_substance,
        unit_of_measure=payload.unit_of_measure,
        measurement_minimum=payload.measurement_minimum,
        measurement_maximum=payload.measurement_maximum,
        recurrence_days=payload.recurrence_days,
        active=payload.active,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item named '{payload.name}' already exists.",
        )
    db.refresh(item)
    return item


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    summary="Get an item",
    dependencies=[Depends(require_role(*_ALL_ROLES))],
)
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    """Returns a single item by ID. Returns 404 if not found. All authenticated roles."""
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found.",
        )
    return item
