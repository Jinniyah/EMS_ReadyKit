"""
routers/check_history.py
Check history, acknowledgement, soft-delete, restore, and hard-delete endpoints.

Refactor (Session B):
- Role constants imported from deps (REF-3)
- write_audit_event imported from core.audit (REF-1)
- HTTP_422_UNPROCESSABLE_CONTENT replaces deprecated constant (REF-7)

Session W additions:
- CH-B5: GET  /checks/daily/deleted        -- list soft-deleted checks (Supervisor+)
- CH-B6: PATCH /checks/daily/{id}/restore  -- restore a soft-deleted check (Supervisor+)
- CH-B4: DELETE /checks/daily/{id}/force   -- permanent hard-delete (Admin only)
  (CH-B4 and CH-B5 were already implemented; CH-B6 restore added this session)

CQ-B6 note: check_date is now a Date column. Audit metadata must convert it to
an ISO string before passing to write_audit_event, since SQLite's JSON serializer
cannot serialize Python date objects. Use check.check_date.isoformat() throughout.
"""

from __future__ import annotations

import csv
import enum
import io
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    ROLE_SUPERVISOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import (
    ADMIN_ONLY,
    ALL_ROLES,
    SUPERVISOR_PLUS,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.daily_inventory_check import (
    AcknowledgeRequest,
    DailyInventoryCheckRead,
    SoftDeleteRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["check-history"])

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EXPORT_MAX_DAYS = 400
_FORMULA_PREFIXES = ("=", "+", "-", "@")


class ExportFormat(str, enum.Enum):
    SIMPLIFIED = "simplified"
    DETAILED = "detailed"


def _get_check_or_404(
    check_id: int, db: Session, *, include_deleted: bool = False
) -> DailyInventoryCheck:
    query = db.query(DailyInventoryCheck).filter(
        DailyInventoryCheck.check_id == check_id
    )
    if not include_deleted:
        query = query.filter(DailyInventoryCheck.deleted_at.is_(None))
    check = query.first()
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check {check_id} not found.",
        )
    return check


def _check_date_str(check: DailyInventoryCheck) -> str:
    """
    Return check_date as an ISO string regardless of column type.
    CQ-B6 changed the column from String(10) to Date, so check_date is
    now a date object at runtime. json.dumps cannot serialize date objects,
    so always convert before storing in audit metadata.
    """
    cd = check.check_date
    if isinstance(cd, date):
        return cd.isoformat()
    return str(cd)


# -- CH-B1: Responder's own check history -------------------------------------


@router.get(
    "/checks/daily/my-history",
    response_model=List[DailyInventoryCheckRead],
    summary="My submitted checks",
)
def my_check_history(
    station_id: Optional[int] = Query(
        default=None, gt=0, description="Scope to a specific station"
    ),
    from_date: Optional[str] = Query(
        default=None,
        alias="from",
        description="Start date filter YYYY-MM-DD (inclusive)",
    ),
    to_date: Optional[str] = Query(
        default=None,
        alias="to",
        description="End date filter YYYY-MM-DD (inclusive)",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> List[DailyInventoryCheck]:
    performed_by_identity = current_user.email or current_user.name
    query = db.query(DailyInventoryCheck).filter(
        DailyInventoryCheck.performed_by == performed_by_identity,
        DailyInventoryCheck.deleted_at.is_(None),
    )
    if station_id is not None:
        query = query.filter(DailyInventoryCheck.station_id == station_id)
    if from_date:
        query = query.filter(DailyInventoryCheck.check_date >= from_date)
    if to_date:
        query = query.filter(DailyInventoryCheck.check_date <= to_date)

    return query.order_by(DailyInventoryCheck.timestamp.desc()).all()


# -- CH-B2: Full check detail with RBAC scoping -------------------------------


@router.get(
    "/checks/daily/{check_id}/detail",
    response_model=DailyInventoryCheckRead,
    summary="Get full check detail",
)
def get_check_detail(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db)

    if not current_user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR):
        if check.performed_by != (current_user.email or current_user.name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own checks.",
            )

    return check


# -- B-E2: Acknowledge a FAIL check -------------------------------------------


@router.patch(
    "/checks/daily/{check_id}/acknowledge",
    response_model=DailyInventoryCheckRead,
    summary="Acknowledge a check with corrective action",
)
def acknowledge_check(
    check_id: int,
    payload: AcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db)

    # Responders can only add notes to their own checks
    if not current_user.has_role(ROLE_SUPERVISOR, ROLE_ADMINISTRATOR):
        if check.performed_by != (current_user.email or current_user.name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add notes to your own checks.",
            )

    now = datetime.now(timezone.utc)
    check.reviewed_by = current_user.user_id
    check.reviewed_at = now
    check.corrective_action = payload.corrective_action
    db.add(check)
    db.flush()

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_ACKNOWLEDGED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "check_status": check.status.value,
            "corrective_action": payload.corrective_action,
        },
        severity="INFO",
    )

    db.refresh(check)
    logger.info(
        "Check %s acknowledged by %s",
        check_id,
        current_user.user_id,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
    return check


# -- CH-B3: Soft-delete a check -----------------------------------------------


@router.delete(
    "/checks/daily/{check_id}",
    response_model=DailyInventoryCheckRead,
    summary="Soft-delete a check",
)
def soft_delete_check(
    check_id: int,
    payload: SoftDeleteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db, include_deleted=True)

    if check.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This check has already been deleted.",
        )

    now = datetime.now(timezone.utc)
    check.deleted_at = now
    check.deleted_by = current_user.user_id
    check.deletion_reason = payload.deletion_reason
    db.add(check)
    db.flush()

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_SOFT_DELETED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "deletion_reason": payload.deletion_reason,
            "check_date": _check_date_str(check),
            "check_status": check.status.value,
        },
        severity="WARNING",
    )

    db.refresh(check)
    logger.warning(
        "Check %s soft-deleted by %s -- reason: %s",
        check_id,
        current_user.user_id,
        payload.deletion_reason,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
    return check


# -- CH-B5: List soft-deleted checks for a station ----------------------------


@router.get(
    "/checks/daily/deleted",
    response_model=List[DailyInventoryCheckRead],
    summary="List soft-deleted checks for a station (CH-B5, Supervisor+)",
)
def list_deleted_checks(
    station_id: int = Query(..., gt=0, description="Station to scope the query"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> List[DailyInventoryCheck]:
    return (
        db.query(DailyInventoryCheck)
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.deleted_at.isnot(None),
        )
        .order_by(DailyInventoryCheck.deleted_at.desc())
        .all()
    )


# -- CH-B6: Restore a soft-deleted check (Supervisor+) -----------------------


@router.patch(
    "/checks/daily/{check_id}/restore",
    response_model=DailyInventoryCheckRead,
    summary="Restore a soft-deleted check (CH-B6, Supervisor+)",
)
def restore_check(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> DailyInventoryCheck:
    check = _get_check_or_404(check_id, db, include_deleted=True)

    if check.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This check is not deleted and cannot be restored.",
        )

    original_deletion_reason = check.deletion_reason

    check.deleted_at = None
    check.deleted_by = None
    check.deletion_reason = None
    db.add(check)
    db.flush()

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_RESTORED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "check_date": _check_date_str(check),
            "check_status": check.status.value,
            "original_deletion_reason": original_deletion_reason,
        },
        severity="INFO",
    )

    db.refresh(check)
    logger.info(
        "Check %s restored by %s",
        check_id,
        current_user.user_id,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )
    return check


# -- CH-B4: DELETE /checks/daily/{id}/force -- permanent hard-delete ----------


@router.delete(
    "/checks/daily/{check_id}/force",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a soft-deleted check (CH-B4, Admin only)",
)
def force_delete_check(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> None:
    check = _get_check_or_404(check_id, db, include_deleted=True)
    if check.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only soft-deleted checks can be permanently deleted. Soft-delete it first.",
        )

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_HARD_DELETED",
        entity_type="daily_inventory_check",
        entity_id=str(check_id),
        station_id=check.station_id,
        vehicle_id=check.vehicle_id,
        metadata={
            "deletion_reason": check.deletion_reason,
            "check_date": _check_date_str(check),
            "check_status": check.status.value,
        },
        severity="CRITICAL",
    )

    db.delete(check)
    db.commit()
    logger.warning(
        "Check %s permanently deleted by %s",
        check_id,
        current_user.user_id,
        extra={"check_id": check_id, "actor": current_user.user_id},
    )


# -- F-5G3a: Compliance CSV export --------------------------------------------


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "station"


def _csv_safe(value: object) -> str:
    """
    OWASP CSV-injection guard. A cell value starting with =/+/-/@ can be
    interpreted as a formula by Excel/Sheets when the file is opened. Notes
    and corrective-action fields are free text a crew member typed -- the
    only user-authored content in this export -- so prefix a leading
    apostrophe to force those cells to render as literal text.
    """
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


@router.get(
    "/checks/daily/station/{station_id}/export",
    response_class=StreamingResponse,
    summary="Download a compliance CSV export for a station (F-5G3a, Supervisor+)",
)
def export_check_history_csv(
    station_id: int,
    from_date: str = Query(..., alias="from", description="Start date, inclusive (YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="End date, inclusive (YYYY-MM-DD)"),
    format: ExportFormat = Query(..., description="'simplified' or 'detailed'"),
    whole_station: bool = Query(
        default=False,
        description="Include every vehicle and location at the station, ignoring vehicle_ids/location_ids.",
    ),
    vehicle_ids: List[int] = Query(default=[]),
    location_ids: List[int] = Query(default=[]),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
) -> StreamingResponse:
    """
    Streams a CSV of daily inventory checks for a station within a date range,
    for a compliance/license inspection. Manual download only -- the caller
    uploads the file wherever it needs to go; there is no further integration.

    Two formats:
      - simplified: one row per check (date, who, subject, pass/fail).
      - detailed: every line item checked, plus (Marcellus/Newberg currently
        have none, but the section always renders so the gap is visible
        rather than hidden) any ALS controlled-substance dual-signature
        checks for the same vehicles/date range, as a second CSV section.
    """
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    require_station_membership(station_id, current_user, db)

    if not whole_station and not vehicle_ids and not location_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Pick at least one vehicle, jump bag, or the whole station before exporting.",
        )

    for label, value in (("from", from_date), ("to", to_date)):
        if not _DATE.match(value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"'{label}' must be in YYYY-MM-DD format.",
            )
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="'from' date must be on or before 'to' date.",
        )
    d_from = date.fromisoformat(from_date)
    d_to = date.fromisoformat(to_date)
    if (d_to - d_from).days > _EXPORT_MAX_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Date range may not exceed {_EXPORT_MAX_DAYS} days.",
        )

    # "Whole station" deliberately includes retired vehicles/locations -- a
    # retired unit's historical checks are still part of the station's
    # compliance record for this date range. Retirement filtering belongs at
    # UI-selection time (the frontend only offers active entities as
    # checkboxes), never in this historical query -- see BUG-AD1 for the
    # same active-vs-retired_at distinction elsewhere in this codebase.
    if whole_station:
        vehicle_ids = [
            v.vehicle_id
            for v in db.query(Vehicle).filter(Vehicle.station_id == station_id).all()
        ]
        location_ids = [
            loc.location_id
            for loc in db.query(InventoryLocation)
            .filter(
                InventoryLocation.station_id == station_id,
                InventoryLocation.location_type != LocationType.VEHICLE,
            )
            .all()
        ]

    query = (
        db.query(DailyInventoryCheck)
        .options(
            joinedload(DailyInventoryCheck.vehicle),
            joinedload(DailyInventoryCheck.location),
        )
        .filter(
            DailyInventoryCheck.station_id == station_id,
            DailyInventoryCheck.check_date >= d_from,
            DailyInventoryCheck.check_date <= d_to,
            DailyInventoryCheck.deleted_at.is_(None),
        )
    )
    entity_filters = []
    if vehicle_ids:
        entity_filters.append(DailyInventoryCheck.vehicle_id.in_(vehicle_ids))
    if location_ids:
        entity_filters.append(DailyInventoryCheck.location_id.in_(location_ids))
    if entity_filters:
        query = query.filter(or_(*entity_filters))
    checks = query.order_by(
        DailyInventoryCheck.check_date.asc(), DailyInventoryCheck.timestamp.asc()
    ).all()

    cs_checks: List[ControlledSubstanceCheck] = []
    if format == ExportFormat.DETAILED and vehicle_ids:
        cs_from = datetime(d_from.year, d_from.month, d_from.day, tzinfo=timezone.utc)
        cs_to_exclusive = datetime(
            d_to.year, d_to.month, d_to.day, tzinfo=timezone.utc
        ) + timedelta(days=1)
        cs_checks = (
            db.query(ControlledSubstanceCheck)
            .options(joinedload(ControlledSubstanceCheck.vehicle))
            .join(Vehicle, ControlledSubstanceCheck.vehicle_id == Vehicle.vehicle_id)
            .filter(
                Vehicle.station_id == station_id,
                ControlledSubstanceCheck.vehicle_id.in_(vehicle_ids),
                ControlledSubstanceCheck.timestamp >= cs_from,
                ControlledSubstanceCheck.timestamp < cs_to_exclusive,
            )
            .order_by(ControlledSubstanceCheck.timestamp.asc())
            .all()
        )

    output = io.StringIO()
    writer = csv.writer(output)

    if format == ExportFormat.SIMPLIFIED:
        writer.writerow(["Check Date", "Performed By", "Subject", "Status", "Station"])
        for check in checks:
            writer.writerow(
                [
                    check.check_date.isoformat(),
                    check.performed_by,
                    check.subject_label,
                    check.status.value,
                    station.name,
                ]
            )
    else:
        writer.writerow(["Section: Daily Inventory Checks — Detailed"])
        writer.writerow(
            [
                "Check Date",
                "Performed By",
                "Subject",
                "Overall Check Status",
                "Item Name",
                "Check Type",
                "Line Item Status",
                "Quantity Found",
                "Quantity Needed",
                "Measurement Value",
                "Functional Pass",
                "Date Value",
                "Line Item Notes",
                "Check Notes",
                "Reviewed By",
                "Reviewed At",
                "Corrective Action",
            ]
        )
        for check in checks:
            for line_item in sorted(check.line_items, key=lambda li: li.line_item_id):
                writer.writerow(
                    [
                        check.check_date.isoformat(),
                        check.performed_by,
                        check.subject_label,
                        check.status.value,
                        line_item.item_name or "",
                        line_item.check_type or "",
                        line_item.status.value,
                        line_item.quantity_found,
                        line_item.quantity_needed,
                        line_item.measurement_value
                        if line_item.measurement_value is not None
                        else "",
                        "Yes"
                        if line_item.functional_pass is True
                        else ("No" if line_item.functional_pass is False else ""),
                        line_item.date_value.isoformat() if line_item.date_value else "",
                        _csv_safe(line_item.notes),
                        _csv_safe(check.notes),
                        check.reviewed_by or "",
                        check.reviewed_at.isoformat() if check.reviewed_at else "",
                        _csv_safe(check.corrective_action),
                    ]
                )

        writer.writerow([])
        writer.writerow(["Section: Controlled Substance Checks (ALS Drug Bag)"])
        writer.writerow(
            [
                "Vehicle",
                "Timestamp (UTC)",
                "Primary Signer",
                "Secondary Signer",
                "Discrepancy Flag",
                "Notes",
            ]
        )
        for cs_check in cs_checks:
            writer.writerow(
                [
                    cs_check.vehicle.vehicle_number if cs_check.vehicle else "",
                    cs_check.timestamp.isoformat(),
                    cs_check.primary_signer,
                    cs_check.secondary_signer,
                    "Yes" if cs_check.discrepancy_flag else "No",
                    _csv_safe(cs_check.notes),
                ]
            )

    content = "﻿" + output.getvalue()
    filename = (
        f"{_slugify(station.name)}_compliance_{format.value}_"
        f"{from_date}_to_{to_date}.csv"
    )

    write_audit_event(
        db,
        actor=current_user.user_id,
        action="CHECK_HISTORY_EXPORTED",
        entity_type="station",
        entity_id=str(station_id),
        station_id=station_id,
        metadata={
            "format": format.value,
            "from": from_date,
            "to": to_date,
            "whole_station": whole_station,
            "vehicle_count": len(vehicle_ids),
            "location_count": len(location_ids),
            "check_row_count": len(checks),
            "cs_check_row_count": len(cs_checks) if format == ExportFormat.DETAILED else None,
        },
        severity="INFO",
    )

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
