"""
routers/items.py
Item catalog CRUD endpoints.

Refactor (Session B):
- Role constants imported from deps (REF-3)
- HTTP_422_UNPROCESSABLE_CONTENT replaces deprecated constant (REF-7)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.item import Item, ItemCategory
from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.item import ItemCreate, ItemRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["items"])


@router.get(
    "",
    response_model=List[ItemRead],
    summary="List items",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_items(
    active: bool = Query(default=True),
    category: Optional[ItemCategory] = Query(default=None),
    controlled_substance: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Item]:
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
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
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
    logger.info(
        "Item created: item_id=%s name=%r category=%s controlled_substance=%s",
        item.item_id, item.name, item.category, item.controlled_substance,
        extra={
            "action":      "ITEM_CREATED",
            "entity_type": "item",
            "entity_id":   str(item.item_id),
        },
    )
    return item


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    summary="Get an item",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found.",
        )
    return item
