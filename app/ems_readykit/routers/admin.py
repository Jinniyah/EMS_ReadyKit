"""
routers/admin.py
Item catalog management endpoints (ADMIN-B1 through ADMIN-B4).

All routes prefixed /admin. Accessible to Supervisor+ — supervisors can add
and edit items; only Administrators can deactivate them.

## Route summary
  GET    /admin/items                    List items (filterable)
  POST   /admin/items                    Create item
  GET    /admin/items/{id}               Get single item
  PATCH  /admin/items/{id}               Edit item
  PATCH  /admin/items/{id}/deactivate    Soft-deactivate item (Admin only)
  GET    /admin/items/search?q=          Typeahead search — used by ItemSearchCombobox

## AI fields
The four AI identification fields (ai_tags, alternate_names, reference_image_url,
barcode) are accepted on create and edit but otherwise dormant. They are stored
and returned but not acted on until the AI image recognition module is built.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.database import get_db
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.inventory_location import InventoryLocation
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import ADMIN_ONLY, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.item import ItemCreate, ItemRead
from ems_readykit.schemas.par_level import (
    AssignItemRequest, ParLevelAssignment, UpdateParLevelRequest
)
from ems_readykit.schemas.compartment import CompartmentRead

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
    """Raise 409 if another item already uses this name."""
    q = db.query(Item).filter(Item.name == name)
    if exclude_id is not None:
        q = q.filter(Item.item_id != exclude_id)
    if q.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item named '{name}' already exists.",
        )


def _conflict_on_barcode(barcode: str, db: Session, exclude_id: Optional[int] = None) -> None:
    """Raise 409 if another item already uses this barcode."""
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


# ── ADMIN-B1: List items ──────────────────────────────────────────────────────

@router.get(
    "/items",
    response_model=List[ItemRead],
    summary="List all items in the catalog (ADMIN-B1)",
)
def list_items(
    category:   Optional[ItemCategory]  = Query(default=None, description="Filter by category"),
    check_type: Optional[ItemCheckType] = Query(default=None, description="Filter by check type"),
    active:     Optional[bool]          = Query(default=True,  description="Filter by active status"),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[Item]:
    q = db.query(Item)
    if category   is not None: q = q.filter(Item.category   == category)
    if check_type is not None: q = q.filter(Item.check_type == check_type)
    if active     is not None: q = q.filter(Item.active     == active)
    return q.order_by(Item.category, Item.name).all()


# ── ADMIN-B1 (search): Typeahead ──────────────────────────────────────────────

@router.get(
    "/items/search",
    response_model=List[ItemRead],
    summary="Typeahead item search — used by ItemSearchCombobox (ADMIN-B1)",
)
def search_items(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search term matched against name, alternate_names, and ai_tags",
    ),
    active_only: bool = Query(
        default=True,
        description="When true, only active items are returned",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[Item]:
    """
    Returns up to `limit` items whose name, alternate_names, or ai_tags
    contain the search term (case-insensitive). Used by ItemSearchCombobox
    on the par level form and item catalog filter bar.

    The three-column search is intentional:
      - name          — the canonical item name ("NRB Mask")
      - alternate_names — crew shorthand ("NRB", "non-rebreather")
      - ai_tags       — AI classifier labels for future image recognition
    """
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


# ── ADMIN-B18: CSV template download ───────────────────────────────────────

_CSV_HEADERS = [
    "name", "category", "check_type", "unit_of_measure",
    "controlled_substance", "measurement_minimum", "measurement_maximum",
    "recurrence_days", "alternate_names", "ai_tags", "barcode",
]

_CSV_EXAMPLES = [
    # SUPPLY example
    ["NRB Mask Adult", "Consumable", "SUPPLY", "each", "FALSE", "", "", "", "NRB,non-rebreather", "mask,oxygen", ""],
    # MEASUREMENT example
    ["On-Board O2 PSI", "Equipment", "MEASUREMENT", "PSI", "FALSE", "500", "2200", "", "O2 pressure", "oxygen,PSI", ""],
    # DATE_RECORD example
    ["AED Date of Last Charge", "Equipment", "DATE_RECORD", "N/A", "FALSE", "", "", "90", "AED charge", "AED,defibrillator", ""],
    # FUNCTIONAL example
    ["AED Battery OK", "Equipment", "FUNCTIONAL", "N/A", "FALSE", "", "", "", "", "", ""],
    # Controlled substance example
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
    """
    Returns a downloadable CSV template with correct headers and
    5 example rows covering all check types.
    BOM-prefixed (UTF-8 with BOM) so Excel opens it correctly without
    needing an import wizard.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_CSV_HEADERS)
    writer.writerows(_CSV_EXAMPLES)

    # UTF-8 BOM prefix so Excel opens without requiring import wizard
    content = "\ufeff" + output.getvalue()

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="ems_readykit_items_template.csv"'
        },
    )


# ── ADMIN-B17: CSV import ───────────────────────────────────────────

MAX_IMPORT_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_IMPORT_ROWS  = 1_000

VALID_CATEGORIES  = {c.value for c in ItemCategory}
VALID_CHECK_TYPES = {c.value for c in ItemCheckType}


def _parse_bool(value: str) -> bool:
    return value.strip().upper() in ("TRUE", "1", "YES")


def _parse_optional_float(value: str, field: str, row: int, errors: list) -> Optional[float]:
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        errors.append({"row": row, "name": "", "error": f"{field} must be a number, got '{v}'"})
        return None


def _parse_optional_int(value: str, field: str, row: int, errors: list) -> Optional[int]:
    v = value.strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        errors.append({"row": row, "name": "", "error": f"{field} must be a whole number, got '{v}'"})
        return None


@router.post(
    "/items/import",
    summary="Bulk import items from CSV (ADMIN-B17)",
)
async def import_items_csv(
    file: UploadFile = File(..., description="CSV file. Max 2 MB, 1000 rows."),
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> Dict[str, Any]:
    """
    Bulk-import items from a CSV file.
    - Rows with a new name are created.
    - Rows whose name already exists are skipped (not updated).
    - Rows with validation errors are recorded and import continues.
    - BOM-prefixed files (Excel default) are handled automatically.
    Returns: { created, skipped, errors: [{row, name, error}] }
    """
    # ─ File size guard ───────────────────────────────────────────────
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File exceeds the 2 MB limit. Split it into smaller batches.",
        )

    # ─ Decode — utf-8-sig strips BOM automatically ───────────────────────
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File must be UTF-8 encoded. Re-save as CSV UTF-8 from Excel.",
        )

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The file appears to be empty or has no header row.",
        )

    # Normalise header names (strip whitespace, lowercase for comparison)
    missing = {h for h in ("name", "category", "unit_of_measure") if h not in reader.fieldnames}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. Download the template for the correct format.",
        )

    created = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    for row_num, row in enumerate(reader, start=2):  # row 1 = headers
        if row_num - 1 > MAX_IMPORT_ROWS:
            errors.append({
                "row": row_num,
                "name": "",
                "error": f"Row limit of {MAX_IMPORT_ROWS} reached. Remaining rows ignored.",
            })
            break

        name = (row.get("name") or "").strip()
        if not name:
            errors.append({"row": row_num, "name": "", "error": "name is required"})
            continue

        # Skip duplicates gracefully
        if db.query(Item).filter(Item.name == name).first():
            skipped += 1
            continue

        # ─ Category ───────────────────────────────────────────────────
        category_raw = (row.get("category") or "").strip()
        if category_raw not in VALID_CATEGORIES:
            errors.append({"row": row_num, "name": name,
                "error": f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}"})
            continue

        # ─ Check type ──────────────────────────────────────────────
        check_type_raw = (row.get("check_type") or "SUPPLY").strip() or "SUPPLY"
        if check_type_raw not in VALID_CHECK_TYPES:
            errors.append({"row": row_num, "name": name,
                "error": f"check_type must be one of: {', '.join(sorted(VALID_CHECK_TYPES))}"})
            continue

        # ─ Unit of measure ──────────────────────────────────────────
        unit = (row.get("unit_of_measure") or "").strip()
        if not unit:
            errors.append({"row": row_num, "name": name, "error": "unit_of_measure is required"})
            continue

        # ─ Conditional fields ─────────────────────────────────────────
        row_errors: List[str] = []

        meas_min = _parse_optional_float(row.get("measurement_minimum", ""), "measurement_minimum", row_num, row_errors)
        meas_max = _parse_optional_float(row.get("measurement_maximum", ""), "measurement_maximum", row_num, row_errors)
        recurrence = _parse_optional_int(row.get("recurrence_days", ""), "recurrence_days", row_num, row_errors)

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

        # ─ Barcode uniqueness ─────────────────────────────────────────
        barcode = (row.get("barcode") or "").strip() or None
        if barcode and db.query(Item).filter(Item.barcode == barcode).first():
            errors.append({"row": row_num, "name": name,
                "error": f"Barcode '{barcode}' is already assigned to another item"})
            continue

        # ─ Create ─────────────────────────────────────────────────────
        item = Item(
            name                = name,
            category            = category_raw,
            check_type          = check_type_raw,
            unit_of_measure     = unit,
            controlled_substance= _parse_bool(row.get("controlled_substance", "")),
            measurement_minimum = meas_min,
            measurement_maximum = meas_max,
            recurrence_days     = recurrence,
            alternate_names     = (row.get("alternate_names") or "").strip() or None,
            ai_tags             = (row.get("ai_tags") or "").strip() or None,
            barcode             = barcode,
            active              = True,
        )
        db.add(item)
        created += 1

    db.commit()
    logger.info(
        "CSV import complete: created=%s skipped=%s errors=%s",
        created, skipped, len(errors),
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
        name                = payload.name,
        category            = payload.category,
        check_type          = payload.check_type,
        controlled_substance= payload.controlled_substance,
        unit_of_measure     = payload.unit_of_measure,
        measurement_minimum = payload.measurement_minimum,
        measurement_maximum = payload.measurement_maximum,
        recurrence_days     = payload.recurrence_days,
        active              = payload.active,
        # AI fields — stored now, used when AI module is built
        ai_tags             = payload.ai_tags,
        alternate_names     = payload.alternate_names,
        reference_image_url = payload.reference_image_url,
        barcode             = payload.barcode,
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
        "Item created: item_id=%s name=%r category=%s",
        item.item_id, item.name, item.category,
        extra={
            "action":      "ITEM_CREATED",
            "entity_type": "item",
            "entity_id":   str(item.item_id),
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

    item.name                 = payload.name
    item.category             = payload.category
    item.check_type           = payload.check_type
    item.controlled_substance = payload.controlled_substance
    item.unit_of_measure      = payload.unit_of_measure
    item.measurement_minimum  = payload.measurement_minimum
    item.measurement_maximum  = payload.measurement_maximum
    item.recurrence_days      = payload.recurrence_days
    item.active               = payload.active
    item.ai_tags              = payload.ai_tags
    item.alternate_names      = payload.alternate_names
    item.reference_image_url  = payload.reference_image_url
    item.barcode              = payload.barcode

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
        item.item_id, item.name,
        extra={
            "action":      "ITEM_UPDATED",
            "entity_type": "item",
            "entity_id":   str(item.item_id),
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
    """
    Soft-deactivate: the item is hidden from operational views (check wizard,
    par level forms) but retained in full for audit history and check line items.
    Cannot deactivate an item that is already inactive.
    """
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
        "Item deactivated: item_id=%s name=%r",
        item.item_id, item.name,
        extra={
            "action":      "ITEM_DEACTIVATED",
            "entity_type": "item",
            "entity_id":   str(item.item_id),
        },
    )
    return item


# ── ADMIN-F4: Par level assignments ───────────────────────────────────────

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
    """
    Returns all par levels for this item enriched with vehicle number,
    vehicle type, location label, and compartment name.
    Used by the item assignments panel in ItemCatalog.
    """
    item = _get_item_or_404(item_id, db)

    query = db.query(ParLevel).filter(ParLevel.item_id == item_id)
    if active_only:
        query = query.filter(ParLevel.active.is_(True))
    par_levels = query.all()

    results = []
    for par in par_levels:
        location  = db.query(InventoryLocation).filter(
            InventoryLocation.location_id == par.location_id
        ).first()
        vehicle   = db.query(Vehicle).filter(
            Vehicle.vehicle_id == location.vehicle_id
        ).first() if location and location.vehicle_id else None
        compartment = db.query(Compartment).filter(
            Compartment.compartment_id == par.compartment_id
        ).first() if par.compartment_id else None

        results.append(ParLevelAssignment(
            par_id           = par.par_id,
            item_id          = par.item_id,
            location_id      = par.location_id,
            compartment_id   = par.compartment_id,
            min_quantity     = par.min_quantity,
            max_quantity     = par.max_quantity,
            active           = par.active,
            created_at       = par.created_at,
            updated_at       = par.updated_at,
            vehicle_id       = vehicle.vehicle_id      if vehicle    else None,
            vehicle_number   = vehicle.vehicle_number  if vehicle    else None,
            vehicle_type     = vehicle.vehicle_type.value if vehicle else None,
            location_label   = location.label          if location   else None,
            compartment_name = compartment.name        if compartment else None,
        ))
    return results


@router.post(
    "/items/{item_id}/assign",
    response_model=ParLevelAssignment,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an item to a vehicle compartment (ADMIN-F4)",
)
def assign_item_to_compartment(
    item_id: int,
    payload: AssignItemRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> ParLevelAssignment:
    """
    Creates a par level linking item → vehicle compartment.
    Frontend supplies vehicle_id + compartment_id; backend derives location_id
    so the UI never needs to know about inventory_locations.
    """
    item = _get_item_or_404(item_id, db)

    # Derive location from vehicle
    location = db.query(InventoryLocation).filter(
        InventoryLocation.vehicle_id == payload.vehicle_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory location found for vehicle {payload.vehicle_id}.",
        )

    # Verify compartment belongs to this location
    compartment = db.query(Compartment).filter(
        Compartment.compartment_id == payload.compartment_id,
        Compartment.location_id    == location.location_id,
    ).first()
    if not compartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Compartment {payload.compartment_id} not found "
                f"on vehicle {payload.vehicle_id}."
            ),
        )

    # Check for existing active assignment
    existing = db.query(ParLevel).filter(
        ParLevel.item_id        == item_id,
        ParLevel.compartment_id == payload.compartment_id,
        ParLevel.active         == True,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"'{item.name}' is already assigned to this compartment "
                f"(par_id={existing.par_id}). Edit the existing assignment instead."
            ),
        )

    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == payload.vehicle_id).first()

    par = ParLevel(
        item_id        = item_id,
        location_id    = location.location_id,
        compartment_id = payload.compartment_id,
        min_quantity   = payload.min_quantity,
        max_quantity   = payload.max_quantity,
        active         = True,
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
        "Par level assigned: par_id=%s item_id=%s vehicle_id=%s compartment_id=%s",
        par.par_id, item_id, payload.vehicle_id, payload.compartment_id,
        extra={
            "action":      "PAR_ASSIGNED",
            "entity_type": "par_level",
            "entity_id":   str(par.par_id),
        },
    )
    return ParLevelAssignment(
        par_id           = par.par_id,
        item_id          = par.item_id,
        location_id      = par.location_id,
        compartment_id   = par.compartment_id,
        min_quantity     = par.min_quantity,
        max_quantity     = par.max_quantity,
        active           = par.active,
        created_at       = par.created_at,
        updated_at       = par.updated_at,
        vehicle_id       = vehicle.vehicle_id        if vehicle     else None,
        vehicle_number   = vehicle.vehicle_number    if vehicle     else None,
        vehicle_type     = vehicle.vehicle_type.value if vehicle    else None,
        location_label   = location.label,
        compartment_name = compartment.name,
    )


@router.patch(
    "/par-levels/{par_id}",
    response_model=ParLevelAssignment,
    summary="Edit a par level min/max (ADMIN-F4)",
)
def update_par_level(
    par_id: int,
    payload: UpdateParLevelRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> ParLevelAssignment:
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(status_code=404, detail=f"Par level {par_id} not found.")
    if not par.active:
        raise HTTPException(status_code=409, detail="Cannot edit an inactive par level.")

    par.min_quantity = payload.min_quantity
    par.max_quantity = payload.max_quantity
    db.commit()
    db.refresh(par)

    location    = db.query(InventoryLocation).filter(InventoryLocation.location_id == par.location_id).first()
    vehicle     = db.query(Vehicle).filter(Vehicle.vehicle_id == location.vehicle_id).first() if location and location.vehicle_id else None
    compartment = db.query(Compartment).filter(Compartment.compartment_id == par.compartment_id).first() if par.compartment_id else None

    logger.info(
        "Par level updated: par_id=%s min=%s max=%s",
        par.par_id, par.min_quantity, par.max_quantity,
        extra={"action": "PAR_UPDATED", "entity_type": "par_level", "entity_id": str(par.par_id)},
    )
    return ParLevelAssignment(
        par_id           = par.par_id,
        item_id          = par.item_id,
        location_id      = par.location_id,
        compartment_id   = par.compartment_id,
        min_quantity     = par.min_quantity,
        max_quantity     = par.max_quantity,
        active           = par.active,
        created_at       = par.created_at,
        updated_at       = par.updated_at,
        vehicle_id       = vehicle.vehicle_id        if vehicle     else None,
        vehicle_number   = vehicle.vehicle_number    if vehicle     else None,
        vehicle_type     = vehicle.vehicle_type.value if vehicle    else None,
        location_label   = location.label            if location    else None,
        compartment_name = compartment.name          if compartment else None,
    )


@router.delete(
    "/par-levels/{par_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item assignment from a compartment (ADMIN-F4)",
)
def remove_par_level(
    par_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_role(*SUPERVISOR_PLUS)),
) -> None:
    """
    Soft-deactivate: sets active=False. The assignment is retained for
    audit history and will not appear in the check wizard or admin UI.
    """
    par = db.query(ParLevel).filter(ParLevel.par_id == par_id).first()
    if not par:
        raise HTTPException(status_code=404, detail=f"Par level {par_id} not found.")
    if not par.active:
        raise HTTPException(status_code=409, detail="Par level is already removed.")

    par.active = False
    db.commit()
    logger.info(
        "Par level removed: par_id=%s",
        par_id,
        extra={"action": "PAR_REMOVED", "entity_type": "par_level", "entity_id": str(par_id)},
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
    """
    Returns active compartments for a vehicle's inventory location.
    Used by the assignment form vehicle → compartment picker cascade.
    """
    location = db.query(InventoryLocation).filter(
        InventoryLocation.vehicle_id == vehicle_id
    ).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory location found for vehicle {vehicle_id}.",
        )
    return (
        db.query(Compartment)
        .filter(
            Compartment.location_id == location.location_id,
            Compartment.active      == True,
        )
        .order_by(Compartment.sort_order, Compartment.name)
        .all()
    )
