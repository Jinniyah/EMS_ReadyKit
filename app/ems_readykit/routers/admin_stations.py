"""
routers/admin_stations.py
Station and location admin endpoints.

Routes (all prefixed /admin via router):
  POST  /admin/stations                  Create station (Admin only)
  PATCH /admin/locations/{id}            Rename inventory location label (Admin only)
  GET   /admin/retired                   List retired vehicles/locations/stations (Admin only)
  GET   /admin/email-alignment-check     Flag StationMember rows with malformed user_id (Admin only, LAUNCH-OPS9)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ems_readykit.core.audit import write_audit_event
from ems_readykit.core.auth import ROLE_ADMINISTRATOR, CurrentUser
from ems_readykit.core.database import get_db
from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.vehicle import Vehicle
from ems_readykit.routers.deps import (
    ADMIN_ONLY,
    require_role,
    require_station_membership,
)
from ems_readykit.schemas.inventory_location import InventoryLocationRead
from ems_readykit.schemas.station import StationCreate, StationRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# -- ADMIN-B15: Create station -------------------------------------------------


@router.post(
    "/stations",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new station -- Administrator only (ADMIN-B15)",
)
def create_station(
    payload: StationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ADMIN_ONLY)),
) -> Station:
    """
    Creates a new station and immediately adds the creating administrator as
    an active StationMember with role 'Administrator', and auto-creates the
    station supply room with 4 default shelf compartments.
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
    db.flush()

    member = StationMember(
        station_id=station.station_id,
        user_id=current_user.email,
        role=ROLE_ADMINISTRATOR,
        assigned_by=current_user.email,
        active=True,
    )
    db.add(member)

    supply_room = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label=f"{station.name} Supply Room",
    )
    db.add(supply_room)
    db.flush()

    _DEFAULT_SUPPLY_COMPARTMENTS = [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf -- airway & PPE supplies", 1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf -- dressings & bandages", 2),
        (
            "Cab 2 - Shelf 1",
            "Cabinet 2, top shelf -- medications & controlled items",
            3,
        ),
        ("Cab 2 - Shelf 2", "Cabinet 2, bottom shelf -- equipment & restock items", 4),
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


# -- SS-B1: Rename an inventory location ---------------------------------------


class _LocationLabelPatch(BaseModel):
    label: str = Field(..., min_length=1, max_length=150)


@router.patch(
    "/locations/{location_id}",
    response_model=InventoryLocationRead,
    summary="Rename an inventory location label (SS-B1) -- Admin only",
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


# -- RET-B4: List retired objects ----------------------------------------------


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
    summary="List retired vehicles, locations, or stations (RET-B4) -- Admin only",
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


# -- LAUNCH-OPS9: Email alignment check ----------------------------------------
# StationMember.user_id must be the person's Azure AD preferred_username
# (an email address) -- see station_members.py and B-ACCESS1 for why. If an
# admin enters a display name ("Earl Jones") instead of an email when adding
# or importing a member, that row will never match any JWT's preferred_username,
# and the person gets a silent "You're not listed as a member of this station"
# 403 on first login with no indication of what went wrong.
#
# This is an on-demand admin diagnostic (not a blocking check) -- the chief or
# an admin can run it any time after a CSV import or manual add to confirm
# every row looks like a real email before someone gets locked out.
_EMAIL_SHAPE_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class _EmailAlignmentIssue(BaseModel):
    member_id: int
    station_id: int
    station_name: str
    user_id: str
    role: str
    preferred_name: Optional[str]
    active: bool
    reason: str


class _EmailAlignmentReport(BaseModel):
    checked: int
    flagged: int
    issues: List[_EmailAlignmentIssue]


def _email_alignment_reason(user_id: str) -> Optional[str]:
    """Return a human-readable reason if user_id doesn't look like an email."""
    candidate = (user_id or "").strip()
    if not candidate:
        return "user_id is blank"
    if " " in candidate:
        return "contains a space -- looks like a display name, not an email"
    if not _EMAIL_SHAPE_RE.match(candidate):
        return "does not look like a valid email address"
    if candidate != candidate.lower():
        return "contains uppercase characters -- emails are stored lowercase"
    return None


@router.get(
    "/email-alignment-check",
    response_model=_EmailAlignmentReport,
    summary="Flag StationMember rows whose user_id is not a valid-looking email (LAUNCH-OPS9) -- Admin only",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def email_alignment_check(
    station_id: Optional[int] = Query(
        default=None,
        gt=0,
        description="Limit the check to a single station. Omit to check all stations.",
    ),
    include_inactive: bool = Query(
        default=False,
        description="Include soft-deleted (inactive) membership rows in the check.",
    ),
    db: Session = Depends(get_db),
) -> _EmailAlignmentReport:
    """
    Scans StationMember rows and flags any whose user_id doesn't look like a
    valid email address -- the most common cause being an admin typing a
    display name (e.g. "Earl Jones") into the email field during manual add
    or CSV import. A flagged row will never match a real JWT preferred_username,
    so that person will be silently denied access on first login.

    This does not modify any data -- it's a read-only diagnostic an admin can
    run any time, e.g. right after a bulk member import.
    """
    query = db.query(StationMember).options(joinedload(StationMember.station))
    if station_id is not None:
        query = query.filter(StationMember.station_id == station_id)
    if not include_inactive:
        query = query.filter(StationMember.active)

    rows = query.order_by(StationMember.station_id, StationMember.user_id).all()

    issues: List[_EmailAlignmentIssue] = []
    for member in rows:
        reason = _email_alignment_reason(member.user_id)
        if reason:
            issues.append(
                _EmailAlignmentIssue(
                    member_id=member.member_id,
                    station_id=member.station_id,
                    station_name=member.station.name if member.station else "",
                    user_id=member.user_id,
                    role=member.role,
                    preferred_name=member.preferred_name,
                    active=member.active,
                    reason=reason,
                )
            )

    if issues:
        logger.warning(
            "Email alignment check: %s of %s membership rows flagged",
            len(issues),
            len(rows),
            extra={
                "action": "EMAIL_ALIGNMENT_CHECK",
                "entity_type": "station_member",
                "flagged_count": len(issues),
                "checked_count": len(rows),
            },
        )

    return _EmailAlignmentReport(checked=len(rows), flagged=len(issues), issues=issues)
