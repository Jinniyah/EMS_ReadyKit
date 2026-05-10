"""
routers/items.py
Item catalog CRUD endpoints.

Endpoints:
  GET  /items         — list items (filterable by active/category/controlled)
  POST /items         — create an item
  GET  /items/{id}    — get a single item

Design decisions:
- Items are the catalog layer — they define what exists, not where or how much.
  Stock quantities live in StockLot, not here.
- name uniqueness is enforced at the DB level. The router catches IntegrityError
  and converts it to a 409 with a clear message.
- Filtering by controlled_substance is provided because the CS check workflow
  needs to quickly identify which items require dual-signature tracking.
- No DELETE — items are deactivated (active=False) to preserve stock lot and
  audit history that references them.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.item import Item, ItemCategory
from ems_readykit.schemas.item import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=List[ItemRead], summary="List items")
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
    Returns items matching the supplied filters.
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
)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    """
    Creates a new item in the catalog.
    Returns 409 if an item with the same name already exists.
    """
    item = Item(
        name=payload.name,
        category=payload.category,
        controlled_substance=payload.controlled_substance,
        unit_of_measure=payload.unit_of_measure,
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


@router.get("/{item_id}", response_model=ItemRead, summary="Get an item")
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    """Returns a single item by ID. Returns 404 if not found."""
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found.",
        )
    return item
