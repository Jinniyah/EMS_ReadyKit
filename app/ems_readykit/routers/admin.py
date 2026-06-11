"""
routers/admin.py
Item catalog management endpoints (ADMIN-B1 through ADMIN-B4).
Vehicle color endpoint (ADMIN-UX1-V).
Station creation endpoint (ADMIN-B15).
Par level endpoints (ADMIN-F4, ADMIN-B6, ADMIN-B7, ADMIN-B8).

All routes prefixed /admin. Accessible to Supervisor+ — supervisors can add
and edit items; only Administrators can deactivate them or create stations.

## Route summary
  GET    /admin/items                         List items (filterable)
  POST   /admin/items                         Create item
  GET    /admin/items/{id}                    Get single item
  PATCH  /admin/items/{id}                    Edit item
  PATCH  /admin/items/{id}/deactivate         Soft-deactivate item (Admin only)
  PATCH  /admin/items/{id}/ai-fields          Update AI identification fields (Admin only, AI-B1)
  GET    /admin/items/search?q=               Typeahead search
  GET    /admin/items/{id}/assignments        List par level assignments (enriched)
  GET    /admin/items/{id}/assignments/count  Active assignment count (lightweight)
  POST   /admin/items/{id}/assign             Assign item to vehicle compartment
  PATCH  /admin/par-levels/{id}              Edit par level min/max (ADMIN-B7)
  PATCH  /admin/par-levels/{id}/deactivate   Soft-deactivate par level (ADMIN-B8)
  DELETE /admin/par-levels/{id}              Alias for deactivate (HTTP DELETE)
  GET    /admin/vehicles/{id}/compartments          List compartments for a vehicle
  GET    /admin/compartments/{id}/assignments       List item par levels for a compartment
  PATCH  /admin/vehicles/{id}/color                 Set vehicle color (ADMIN-UX1-V, Supervisor+)
  POST   /admin/stations                     Create station (ADMIN-B15, Admin only)

Bug fix (post-Block-6):
  create_station now auto-adds the creating administrator as an active
  StationMember with role "Administrator". Without this, the new station
  was invisible after creation because GET /stations/my only returns stations
  where the caller has a membership row.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import (
    ADMIN_ONLY,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.compartment import CompartmentRead
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.item import ItemCreate, ItemRead
from ems_readykit.schemas.par_level import (
    AssignItemRequest,
    ParLevelAssignment,
    UpdateParLevelRequest,
)
from ems_readykit.schemas.station import StationCreate, StationRead
from ems_readykit.schemas.vehicle import VehicleColorUpdate, VehicleDetailsUpdate
from ems_readykit.schemas.vehicle import VehicleRead as VehicleReadSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_item_or_404(item_id: int, db: Session) -> Item:
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found.",
        )
    return item


def _conflict_on_name(name: str, db: Session, exclude_id: Optional[int] = None) -> None:
    q = db.query(Item).filter(Item.name == name)
    if exclude_id is not None:
        q = q.filter(Item.item_id != exclude_id)
    if q.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item named '{name}' already exists.",
        )


def _conflict_on_barcode(
    barcode: str, db: Session, exclude_id: Optional[int] = None
) -> None:
    if not barcode:
        return
    q = db.query(Item).filter(Item.barcode == barcode)
    if exclude_id is not None:
        q = q.filter(Item.item_id != exclude_id)
    if q.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Barcode '{barcode}' is already assigned to another item.",
        )


def _get_par_or_404(par_id: int, db: Session) -> ParLevel:
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Par level {par_id} not found.",
        )
    return par


def _enrich_par(
    par: ParLevel,
    db: Session,
    item: Optional[Item] = None,
) -> ParLevelAssignment:
    """Join vehicle, location, compartment, and optionally item onto a ParLevel row."""
    location = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.location_id == par.location_id)
        .first()
    )
    vehicle = (
        db.query(Vehicle).filter(Vehicle.vehicle_id == location.vehicle_id).first()
        if location and location.vehicle_id
        else None
    )
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == par.compartment_id)
        .first()
        if par.compartment_id
        else None
    )

    return ParLevelAssignment(
        par_id=par.par_id,
        item_id=par.item_id,
        location_id=par.location_id,
        compartment_id=par.compartment_id,
        min_quantity=par.min_quantity,
        max_quantity=par.max_quantity,
        active=par.active,
        priority_check=par.priority_check,
        priority_question=par.priority_question,
        is_damaged=par.is_damaged,
        created_at=par.created_at,
        updated_at=par.updated_at,
        vehicle_id=vehicle.vehicle_id if vehicle else None,
        vehicle_number=vehicle.vehicle_number if vehicle else None,
        vehicle_type=vehicle.vehicle_type.value if vehicle else None,
        location_label=location.label if location else None,
        compartment_name=compartment.name if compartment else None,
        item_name=item.name if item else None,
        item_check_type=item.check_type.value if item and item.check_type else None,
    )


# ── ADMIN-B1: List items ──────────────────────────────────────────────────────


@router.get(
    "/items",
    response_model=List[ItemRead],
    summary="List all items in the catalog (ADMIN-B1)",
)
def list_items(
    category: Optional[ItemCategory] = Query(default=None),
    check_type: Optional[ItemCheckType] = Query(default=None),
    active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[Dict]:
    # Subquery: active par-level count per item — avoids N+1 count requests.
    count_sq = (
        db.query(ParLevel.item_id, func.count(ParLevel.par_id).label("cnt"))
        .filter(ParLevel.active.is_(True))
        .group_by(ParLevel.item_id)
        .subquery()
    )
    q = db.query(
        Item, func.coalesce(count_sq.c.cnt, 0).label("assignment_count")
    ).outerjoin(count_sq, Item.item_id == count_sq.c.item_id)
    if category is not None:
        q = q.filter(Item.category == category)
    if check_type is not None:
        q = q.filter(Item.check_type == check_type)
    if active is not None:
        q = q.filter(Item.active == active)
    rows = q.order_by(Item.category, Item.name).all()
    result = []
    for item, cnt in rows:
        d = ItemRead.model_validate(item).model_dump()
        d["assignment_count"] = int(cnt)
        result.append(d)
    return result


# ── ADMIN-B1 (search): Typeahead ──────────────────────────────────────────────


@router.get(
    "/items/search",
    response_model=List[ItemRead],
    summary="Typeahead item search (ADMIN-B1)",
)
def search_items(
    q: str = Query(..., min_length=1, max_length=100),
    active_only: bool = Query(default=True),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[Item]:
    term = f"%{q.strip()}%"
    query = db.query(Item).filter(
        or_(
            Item.name.ilike(term),
            Item.alternate_names.ilike(term),
            Item.ai_tags.ilike(term),
        )
    )
    if active_only:
        query = query.filter(Item.active.is_(True))
    return query.order_by(Item.name).limit(limit).all()


# ── ADMIN-B18: CSV template download ─────────────────────────────────────────

_CSV_HEADERS = [
    "name",
    "category",
    "check_type",
    "unit_of_measure",
    "controlled_substance",
    "measurement_minimum",
    "measurement_maximum",
    "recurrence_days",
    "alternate_names",
    "ai_tags",
    "barcode",
]

_CSV_EXAMPLES = [
    [
        "NRB Mask Adult",
        "Consumable",
        "SUPPLY",
        "each",
        "FALSE",
        "",
        "",
        "",
        "NRB,non-rebreather",
        "mask,oxygen",
        "",
    ],
    [
        "On-Board O2 PSI",
        "Equipment",
        "MEASUREMENT",
        "PSI",
        "FALSE",
        "500",
        "2200",
        "",
        "O2 pressure",
        "oxygen,PSI",
        "",
    ],
    [
        "AED Date of Last Charge",
        "Equipment",
        "DATE_RECORD",
        "N/A",
        "FALSE",
        "",
        "",
        "90",
        "AED charge",
        "AED,defibrillator",
        "",
    ],
    [
        "AED Battery OK",
        "Equipment",
        "FUNCTIONAL",
        "N/A",
        "FALSE",
        "",
        "",
        "",
        "",
        "",
        "",
    ],
    ["Morphine 10mg", "Medication", "SUPPLY", "vial", "TRUE", "", "", "", "", "", ""],
]


@router.get(
    "/items/import/template",
    summary="Download CSV import template (ADMIN-B18)",
    response_class=StreamingResponse,
)
def download_import_template(
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> StreamingResponse:
    output = io.StringIO()
    csv.writer(output).writerow(_CSV_HEADERS)
    for row in _CSV_EXAMPLES:
        csv.writer(output).writerow(row)
    content = "\ufeff" + output.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="ems_readykit_items_template.csv"'
        },
    )


# ── ADMIN-B17: CSV import ─────────────────────────────────────────────────────

MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_IMPORT_ROWS = 1_000
VALID_CATEGORIES = {c.value for c in ItemCategory}
VALID_CHECK_TYPES = {c.value for c in ItemCheckType}


def _parse_bool(value: str) -> bool:
    return value.strip().upper() in ("TRUE", "1", "YES")


def _parse_optional_float(
    value: str, field: str, row: int, errors: list
) -> Optional[float]:
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        errors.append(
            {"row": row, "name": "", "error": f"{field} must be a number, got '{v}'"}
        )
        return None


def _parse_optional_int(
    value: str, field: str, row: int, errors: list
) -> Optional[int]:
    v = value.strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        errors.append(
            {
                "row": row,
                "name": "",
                "error": f"{field} must be a whole number, got '{v}'",
            }
        )
        return None


@router.post("/items/import", summary="Bulk import items from CSV (ADMIN-B17)")
async def import_items_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Dict[str, Any]:
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File exceeds the 2 MB limit.",
        )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File must be UTF-8 encoded.",
        )
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The file appears to be empty or has no header row.",
        )
    missing = {
        h for h in ("name", "category", "unit_of_measure") if h not in reader.fieldnames
    }
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Missing required columns: {', '.join(sorted(missing))}.",
        )

    created = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []
    for row_num, row in enumerate(reader, start=2):
        if row_num - 1 > MAX_IMPORT_ROWS:
            errors.append(
                {
                    "row": row_num,
                    "name": "",
                    "error": f"Row limit of {MAX_IMPORT_ROWS} reached.",
                }
            )
            break
        name = (row.get("name") or "").strip()
        if not name:
            errors.append({"row": row_num, "name": "", "error": "name is required"})
            continue
        if db.query(Item).filter(Item.name == name).first():
            skipped += 1
            continue
        category_raw = (row.get("category") or "").strip()
        if category_raw not in VALID_CATEGORIES:
            errors.append(
                {
                    "row": row_num,
                    "name": name,
                    "error": f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
                }
            )
            continue
        check_type_raw = (row.get("check_type") or "SUPPLY").strip() or "SUPPLY"
        if check_type_raw not in VALID_CHECK_TYPES:
            errors.append(
                {
                    "row": row_num,
                    "name": name,
                    "error": f"check_type must be one of: {', '.join(sorted(VALID_CHECK_TYPES))}",
                }
            )
            continue
        unit = (row.get("unit_of_measure") or "").strip()
        if not unit:
            errors.append(
                {"row": row_num, "name": name, "error": "unit_of_measure is required"}
            )
            continue
        row_errors: List[str] = []
        meas_min = _parse_optional_float(
            row.get("measurement_minimum", ""),
            "measurement_minimum",
            row_num,
            row_errors,
        )
        meas_max = _parse_optional_float(
            row.get("measurement_maximum", ""),
            "measurement_maximum",
            row_num,
            row_errors,
        )
        recurrence = _parse_optional_int(
            row.get("recurrence_days", ""), "recurrence_days", row_num, row_errors
        )
        if check_type_raw == "MEASUREMENT" and meas_min is None:
            row_errors.append("measurement_minimum is required for MEASUREMENT items")
        if check_type_raw == "DATE_RECORD" and recurrence is None:
            row_errors.append("recurrence_days is required for DATE_RECORD items")
        if meas_min is not None and meas_max is not None and meas_max < meas_min:
            row_errors.append("measurement_maximum must be >= measurement_minimum")
        if row_errors:
            for e in row_errors:
                errors.append({"row": row_num, "name": name, "error": e})
            continue
        barcode = (row.get("barcode") or "").strip() or None
        if barcode and db.query(Item).filter(Item.barcode == barcode).first():
            errors.append(
                {
                    "row": row_num,
                    "name": name,
                    "error": f"Barcode '{barcode}' is already assigned to another item",
                }
            )
            continue
        db.add(
            Item(
                name=name,
                category=category_raw,
                check_type=check_type_raw,
                unit_of_measure=unit,
                controlled_substance=_parse_bool(row.get("controlled_substance", "")),
                measurement_minimum=meas_min,
                measurement_maximum=meas_max,
                recurrence_days=recurrence,
                alternate_names=(row.get("alternate_names") or "").strip() or None,
                ai_tags=(row.get("ai_tags") or "").strip() or None,
                barcode=barcode,
                active=True,
            )
        )
        created += 1
    db.commit()
    logger.info(
        "CSV import: created=%s skipped=%s errors=%s",
        created,
        skipped,
        len(errors),
        extra={"action": "ITEMS_IMPORTED", "entity_type": "item", "entity_id": "bulk"},
    )
    return {"created": created, "skipped": skipped, "errors": errors}


@router.get(
    "/items/{item_id}",
    response_model=ItemRead,
    summary="Get a single catalog item (ADMIN-B1)",
)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Item:
    return _get_item_or_404(item_id, db)


# ── ADMIN-B2: Create item ─────────────────────────────────────────────────────


@router.post(
    "/items",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to the catalog (ADMIN-B2)",
)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Item:
    _conflict_on_name(payload.name, db)
    _conflict_on_barcode(payload.barcode, db)
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
        ai_tags=payload.ai_tags,
        alternate_names=payload.alternate_names,
        reference_image_url=payload.reference_image_url,
        barcode=payload.barcode,
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
        "Item created: item_id=%s name=%r",
        item.item_id,
        item.name,
        extra={
            "action": "ITEM_CREATED",
            "entity_type": "item",
            "entity_id": str(item.item_id),
        },
    )
    return item


# ── ADMIN-B3: Edit item ───────────────────────────────────────────────────────


@router.patch(
    "/items/{item_id}",
    response_model=ItemRead,
    summary="Edit a catalog item (ADMIN-B3)",
)
def update_item(
    item_id: int,
    payload: ItemCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Item:
    item = _get_item_or_404(item_id, db)
    if payload.name != item.name:
        _conflict_on_name(payload.name, db, exclude_id=item_id)
    if payload.barcode and payload.barcode != item.barcode:
        _conflict_on_barcode(payload.barcode, db, exclude_id=item_id)
    item.name = payload.name
    item.category = payload.category
    item.check_type = payload.check_type
    item.controlled_substance = payload.controlled_substance
    item.unit_of_measure = payload.unit_of_measure
    item.measurement_minimum = payload.measurement_minimum
    item.measurement_maximum = payload.measurement_maximum
    item.recurrence_days = payload.recurrence_days
    item.active = payload.active
    item.ai_tags = payload.ai_tags
    item.alternate_names = payload.alternate_names
    item.reference_image_url = payload.reference_image_url
    item.barcode = payload.barcode
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Name or barcode conflicts with an existing item.",
        )
    db.refresh(item)
    logger.info(
        "Item updated: item_id=%s name=%r",
        item.item_id,
        item.name,
        extra={
            "action": "ITEM_UPDATED",
            "entity_type": "item",
            "entity_id": str(item.item_id),
        },
    )
    return item


# ── ADMIN-B4: Deactivate item ─────────────────────────────────────────────────


@router.patch(
    "/items/{item_id}/deactivate",
    response_model=ItemRead,
    summary="Soft-deactivate a catalog item — Administrator only (ADMIN-B4)",
)
def deactivate_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*ADMIN_ONLY)),
) -> Item:
    item = _get_item_or_404(item_id, db)
    if not item.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item '{item.name}' is already inactive.",
        )
    item.active = False
    db.commit()
    db.refresh(item)
    logger.info(
        "Item deactivated: item_id=%s",
        item.item_id,
        extra={
            "action": "ITEM_DEACTIVATED",
            "entity_type": "item",
            "entity_id": str(item.item_id),
        },
    )
    return item


# ── AI-B1: AI identification fields ──────────────────────────────────────────


class _AiFieldsPatch(BaseModel):
    ai_tags: Optional[str] = Field(default=None, max_length=500)
    alternate_names: Optional[str] = Field(default=None, max_length=500)
    reference_image_url: Optional[str] = Field(default=None, max_length=500)
    barcode: Optional[str] = Field(default=None, max_length=100)


@router.patch(
    "/items/{item_id}/ai-fields",
    response_model=ItemRead,
    summary="Update AI identification fields on an item — Admin only (AI-B1)",
)
def update_item_ai_fields(
    item_id: int,
    payload: _AiFieldsPatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> Item:
    item = _get_item_or_404(item_id, db)
    fields = payload.model_fields_set
    if "barcode" in fields and payload.barcode:
        _conflict_on_barcode(payload.barcode, db, exclude_id=item_id)
    if "ai_tags" in fields:
        item.ai_tags = payload.ai_tags or None
    if "alternate_names" in fields:
        item.alternate_names = payload.alternate_names or None
    if "reference_image_url" in fields:
        item.reference_image_url = payload.reference_image_url or None
    if "barcode" in fields:
        item.barcode = payload.barcode or None
    db.commit()
    db.refresh(item)
    write_audit_event(
        db,
        actor=current_user.email or current_user.name,
        action="ITEM_AI_FIELDS_UPDATED",
        entity_type="item",
        entity_id=str(item_id),
        metadata={"fields_set": sorted(fields)},
    )
    return item


# ── ADMIN-F4: Par level assignments ──────────────────────────────────────────


@router.get(
    "/items/{item_id}/assignments/count",
    summary="Active assignment count for an item — lightweight (ADMIN-F4)",
)
def count_item_assignments(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Dict[str, int]:
    _get_item_or_404(item_id, db)
    count = (
        db.query(ParLevel)
        .filter(
            ParLevel.item_id == item_id,
            ParLevel.active.is_(True),
        )
        .count()
    )
    return {"count": count}


@router.get(
    "/items/{item_id}/assignments",
    response_model=List[ParLevelAssignment],
    summary="List vehicle/compartment assignments for an item (ADMIN-F4)",
)
def list_item_assignments(
    item_id: int,
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[ParLevelAssignment]:
    _get_item_or_404(item_id, db)
    query = db.query(ParLevel).filter(ParLevel.item_id == item_id)
    if active_only:
        query = query.filter(ParLevel.active.is_(True))
    return [_enrich_par(par, db) for par in query.all()]


@router.post(
    "/items/{item_id}/assign",
    response_model=ParLevelAssignment,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an item to a vehicle compartment (ADMIN-B6)",
)
def assign_item_to_compartment(
    item_id: int,
    payload: AssignItemRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> ParLevelAssignment:
    item = _get_item_or_404(item_id, db)
    if payload.vehicle_id is not None:
        location = (
            db.query(InventoryLocation)
            .filter(InventoryLocation.vehicle_id == payload.vehicle_id)
            .first()
        )
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No inventory location found for vehicle {payload.vehicle_id}.",
            )
    else:
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
    require_station_membership(location.station_id, current_user, db)
    compartment = (
        db.query(Compartment)
        .filter(
            Compartment.compartment_id == payload.compartment_id,
            Compartment.location_id == location.location_id,
        )
        .first()
    )
    if not compartment:
        ref = (
            f"vehicle {payload.vehicle_id}"
            if payload.vehicle_id
            else f"location {payload.location_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compartment {payload.compartment_id} not found on {ref}.",
        )
    existing = (
        db.query(ParLevel)
        .filter(
            ParLevel.item_id == item_id,
            ParLevel.compartment_id == payload.compartment_id,
            ParLevel.active,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{item.name}' is already assigned to this compartment (par_id={existing.par_id}).",
        )
    par = ParLevel(
        item_id=item_id,
        location_id=location.location_id,
        compartment_id=payload.compartment_id,
        min_quantity=payload.min_quantity,
        max_quantity=payload.max_quantity,
        active=True,
    )
    db.add(par)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item is already assigned to this compartment.",
        )
    db.refresh(par)
    logger.info(
        "Par level assigned: par_id=%s item_id=%s location_id=%s compartment_id=%s",
        par.par_id,
        item_id,
        location.location_id,
        payload.compartment_id,
        extra={
            "action": "PAR_ASSIGNED",
            "entity_type": "par_level",
            "entity_id": str(par.par_id),
        },
    )
    return _enrich_par(par, db)


@router.patch(
    "/par-levels/{par_id}",
    response_model=ParLevelAssignment,
    summary="Edit a par level min/max (ADMIN-B7)",
)
def update_par_level(
    par_id: int,
    payload: UpdateParLevelRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> ParLevelAssignment:
    par = _get_par_or_404(par_id, db)
    if not par.active:
        raise HTTPException(
            status_code=409, detail="Cannot edit an inactive par level."
        )
    par.min_quantity = payload.min_quantity
    par.max_quantity = payload.max_quantity
    fields = payload.model_fields_set
    if "priority_check" in fields:
        par.priority_check = payload.priority_check
    if "priority_question" in fields:
        par.priority_question = payload.priority_question or None
    db.commit()
    db.refresh(par)
    logger.info(
        "Par level updated: par_id=%s min=%s max=%s",
        par.par_id,
        par.min_quantity,
        par.max_quantity,
        extra={
            "action": "PAR_UPDATED",
            "entity_type": "par_level",
            "entity_id": str(par.par_id),
        },
    )
    return _enrich_par(par, db)


@router.patch(
    "/par-levels/{par_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-deactivate (remove) a par level assignment (ADMIN-B8)",
)
def deactivate_par_level(
    par_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> None:
    par = _get_par_or_404(par_id, db)
    if not par.active:
        raise HTTPException(status_code=409, detail="Par level is already inactive.")
    par.active = False
    par.deactivated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(
        "Par level deactivated: par_id=%s",
        par_id,
        extra={
            "action": "PAR_DEACTIVATED",
            "entity_type": "par_level",
            "entity_id": str(par_id),
        },
    )


@router.delete(
    "/par-levels/{par_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a par level assignment — alias for PATCH /deactivate (ADMIN-F4)",
)
def remove_par_level(
    par_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> None:
    par = _get_par_or_404(par_id, db)
    if not par.active:
        raise HTTPException(status_code=409, detail="Par level is already inactive.")
    par.active = False
    par.deactivated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(
        "Par level removed (DELETE): par_id=%s",
        par_id,
        extra={
            "action": "PAR_DEACTIVATED",
            "entity_type": "par_level",
            "entity_id": str(par_id),
        },
    )


@router.get(
    "/vehicles/{vehicle_id}/compartments",
    response_model=List[CompartmentRead],
    summary="List compartments for a vehicle (ADMIN-F4)",
)
def list_vehicle_compartments(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[Compartment]:
    location = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.vehicle_id == vehicle_id)
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory location found for vehicle {vehicle_id}.",
        )
    return (
        db.query(Compartment)
        .filter(Compartment.location_id == location.location_id, Compartment.active)
        .order_by(Compartment.sort_order, Compartment.name)
        .all()
    )


@router.get(
    "/compartments/{compartment_id}/assignments",
    response_model=List[ParLevelAssignment],
    summary="List item par levels for a compartment (vehicle-centric view)",
)
def list_compartment_assignments(
    compartment_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[ParLevelAssignment]:
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
    pars = (
        db.query(ParLevel)
        .filter(ParLevel.compartment_id == compartment_id, ParLevel.active.is_(True))
        .order_by(ParLevel.item_id)
        .all()
    )
    item_ids = {p.item_id for p in pars}
    items_by_id = (
        {i.item_id: i for i in db.query(Item).filter(Item.item_id.in_(item_ids)).all()}
        if item_ids
        else {}
    )
    return [_enrich_par(par, db, item=items_by_id.get(par.item_id)) for par in pars]


# ── ADMIN-UX1-V: Vehicle color ────────────────────────────────────────────────


@router.patch(
    "/vehicles/{vehicle_id}/color",
    response_model=VehicleReadSchema,
    summary="Set or clear a vehicle's color (ADMIN-UX1-V, Supervisor+)",
)
def update_vehicle_color(
    vehicle_id: int,
    payload: VehicleColorUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    vehicle.vehicle_color = payload.vehicle_color
    db.commit()
    db.refresh(vehicle)
    logger.info(
        "Vehicle color updated: vehicle_id=%s color=%r",
        vehicle_id,
        payload.vehicle_color,
        extra={
            "action": "VEHICLE_COLOR_UPDATED",
            "entity_type": "vehicle",
            "entity_id": str(vehicle_id),
        },
    )
    return vehicle


# ── Vehicle details (number + type) ──────────────────────────────────────────


@router.patch(
    "/vehicles/{vehicle_id}/details",
    response_model=VehicleReadSchema,
    summary="Update vehicle number and type — Admin only",
)
def update_vehicle_details(
    vehicle_id: int,
    payload: VehicleDetailsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*ADMIN_ONLY)),
) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    new_number = payload.vehicle_number.strip().upper()
    if new_number != vehicle.vehicle_number:
        dup = (
            db.query(Vehicle)
            .filter(
                Vehicle.station_id == vehicle.station_id,
                Vehicle.vehicle_number == new_number,
                Vehicle.vehicle_id != vehicle_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle number '{new_number}' is already in use at this station.",
            )
    vehicle.vehicle_number = new_number
    vehicle.vehicle_type = payload.vehicle_type
    db.commit()
    db.refresh(vehicle)
    logger.info(
        "Vehicle details updated: vehicle_id=%s number=%r type=%r",
        vehicle_id,
        vehicle.vehicle_number,
        vehicle.vehicle_type.value,
        extra={
            "action": "VEHICLE_DETAILS_UPDATED",
            "entity_type": "vehicle",
            "entity_id": str(vehicle_id),
        },
    )
    return vehicle


# ── ADMIN-B15: Create station ─────────────────────────────────────────────────


@router.post(
    "/stations",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new station — Administrator only (ADMIN-B15)",
)
def create_station(
    payload: StationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> Station:
    """
    Creates a new station and immediately adds the creating administrator as
    an active StationMember with role 'Administrator'.

    Without the auto-membership step, the new station would be invisible after
    creation — GET /stations/my only returns stations where the caller has a
    membership row. The admin would have to manually add themselves, which is
    both confusing and error-prone.

    Fields:
      name          — required
      address       — required
      region        — required
      call_sign     — optional (e.g. "DFD")
      primary_color — optional #rrggbb
      active        — defaults to True
    """
    station = Station(
        name=payload.name,
        address=payload.address,
        region=payload.region,
        active=payload.active,
        call_sign=payload.call_sign,
        primary_color=payload.primary_color,
    )
    db.add(station)
    db.flush()  # get station.station_id before committing

    # Auto-add the creating admin as a member so the station is immediately
    # visible in GET /stations/my and the admin home screen.
    member = StationMember(
        station_id=station.station_id,
        user_id=current_user.email,
        role=ROLE_ADMINISTRATOR,
        assigned_by=current_user.email,
        active=True,
    )
    db.add(member)

    # Auto-create the station supply room with 4 default compartments.
    from ems_readykit.models.inventory_location import InventoryLocation as IL
    from ems_readykit.models.inventory_location import LocationType

    supply_room = IL(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label=f"{station.name} Supply Room",
    )
    db.add(supply_room)
    db.flush()

    _DEFAULT_SUPPLY_COMPARTMENTS = [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf — airway & PPE supplies", 1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf — dressings & bandages", 2),
        ("Cab 2 - Shelf 1", "Cabinet 2, top shelf — medications & controlled items", 3),
        ("Cab 2 - Shelf 2", "Cabinet 2, bottom shelf — equipment & restock items", 4),
    ]
    for comp_name, comp_desc, sort_order in _DEFAULT_SUPPLY_COMPARTMENTS:
        db.add(
            Compartment(
                location_id=supply_room.location_id,
                name=comp_name,
                location_descriptor=comp_desc,
                sort_order=sort_order,
                active=True,
            )
        )

    db.commit()
    db.refresh(station)

    logger.info(
        "Station created: station_id=%s name=%r; auto-added member=%r",
        station.station_id,
        station.name,
        current_user.email,
        extra={
            "action": "STATION_CREATED",
            "entity_type": "station",
            "entity_id": str(station.station_id),
        },
    )
    return station


# ── SS-B1: Rename an inventory location ──────────────────────────────────────


class _LocationLabelPatch(BaseModel):
    label: str = Field(..., min_length=1, max_length=150)


@router.patch(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Rename an inventory location label (SS-B1) — Admin only",
)
def rename_location(
    location_id: int,
    payload: _LocationLabelPatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> InventoryLocation:
    loc = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.location_id == location_id)
        .first()
    )
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {location_id} not found.",
        )
    require_station_membership(loc.station_id, current_user, db)
    loc.label = payload.label.strip()
    db.commit()
    db.refresh(loc)
    write_audit_event(
        db,
        actor=current_user.email or current_user.name,
        action="LOCATION_RENAMED",
        entity_type="inventory_location",
        entity_id=str(location_id),
        metadata={"new_label": loc.label},
    )
    return loc


# ── RET-B4: List retired objects ──────────────────────────────────────────────


class _RetiredItem(BaseModel):
    type: str
    id: int
    name: str
    retired_at: datetime
    retired_by: Optional[str]
    retirement_reason: Optional[str]
    station_id: Optional[int]


@router.get(
    "/retired",
    response_model=List[_RetiredItem],
    summary="List retired vehicles, locations, or stations (RET-B4) — Admin only",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def list_retired(
    type: str = Query(
        ...,
        description="One of: vehicles, locations, stations",
        pattern="^(vehicles|locations|stations)$",
    ),
    station_id: Optional[int] = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> List[_RetiredItem]:
    result: List[_RetiredItem] = []

    if type == "vehicles":
        query = db.query(Vehicle).filter(Vehicle.retired_at.isnot(None))
        if station_id:
            query = query.filter(Vehicle.station_id == station_id)
        for v in query.order_by(Vehicle.retired_at.desc()).all():
            result.append(
                _RetiredItem(
                    type="vehicle",
                    id=v.vehicle_id,
                    name=v.vehicle_number,
                    retired_at=v.retired_at,
                    retired_by=v.retired_by,
                    retirement_reason=v.retirement_reason,
                    station_id=v.station_id,
                )
            )

    elif type == "locations":
        query = db.query(InventoryLocation).filter(
            InventoryLocation.retired_at.isnot(None)
        )
        if station_id:
            query = query.filter(InventoryLocation.station_id == station_id)
        for loc in query.order_by(InventoryLocation.retired_at.desc()).all():
            result.append(
                _RetiredItem(
                    type="location",
                    id=loc.location_id,
                    name=loc.label,
                    retired_at=loc.retired_at,
                    retired_by=loc.retired_by,
                    retirement_reason=loc.retirement_reason,
                    station_id=loc.station_id,
                )
            )

    elif type == "stations":
        query = db.query(Station).filter(Station.retired_at.isnot(None))
        if station_id:
            query = query.filter(Station.station_id == station_id)
        for s in query.order_by(Station.retired_at.desc()).all():
            result.append(
                _RetiredItem(
                    type="station",
                    id=s.station_id,
                    name=s.name,
                    retired_at=s.retired_at,
                    retired_by=s.retired_by,
                    retirement_reason=s.retirement_reason,
                    station_id=s.station_id,
                )
            )

    return result
