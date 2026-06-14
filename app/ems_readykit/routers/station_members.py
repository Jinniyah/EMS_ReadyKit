"""
routers/station_members.py
Station membership management endpoints (B-ACCESS1 Phase 2).

Refactor (Session B):
- Role constants imported from deps (REF-3)

ACC-B6: Edit a station member's preferred_name or role (PATCH by member_id).
ACC-B7 (Option A): Multiple roles per person. Unique constraint is now
  (station_id, user_id, role) so a person can hold Responder + Supervisor rows
  simultaneously. PATCH and DELETE use member_id (not user_id) because user_id
  is no longer unique per station.
ACC-B8: CSV bulk import for station membership.
  POST /stations/{id}/members/import  -- upload CSV
  GET  /stations/{id}/members/import/template  -- download template

Role resolution for multi-role users: highest-privilege wins on the backend
(Administrator > Supervisor > Responder). The frontend role switcher lets a
user pick which role context they want to work in.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ems_readykit.core.auth import (
    ROLE_ADMINISTRATOR,
    CurrentUser,
)
from ems_readykit.core.database import get_db
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, require_role
from ems_readykit.schemas.station import StationRead
from ems_readykit.schemas.station_member import (
    VALID_ROLES,
    StationMemberCreate,
    StationMemberRead,
    StationMemberUpdate,
)

router = APIRouter(prefix="/stations", tags=["station-members"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_station_or_404(station_id: int, db: Session) -> Station:
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found.",
        )
    return station


def _get_member_by_id_or_404(
    member_id: int, station_id: int, db: Session
) -> StationMember:
    """Fetch an active StationMember by primary key, scoped to a station."""
    member = (
        db.query(StationMember)
        .filter(
            StationMember.member_id == member_id,
            StationMember.station_id == station_id,
            StationMember.active,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active membership record {member_id} found at station {station_id}.",
        )
    return member


def _enforce_role_assignment_permission(
    assigning_user: CurrentUser,
    target_role: str,
) -> None:
    if target_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid role '{target_role}'. Must be one of: {sorted(VALID_ROLES)}",
        )
    if target_role == ROLE_ADMINISTRATOR and not assigning_user.has_role(
        ROLE_ADMINISTRATOR
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Administrators can assign the Administrator role.",
        )


# ── GET /stations/my ──────────────────────────────────────────────────────────


@router.get(
    "/my",
    response_model=List[StationRead],
    summary="List stations the current user is assigned to",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_my_stations(
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[Station]:
    members = (
        db.query(StationMember)
        .filter(
            StationMember.user_id == current_user.email,
            StationMember.active,
        )
        .all()
    )
    if not members:
        return []

    station_ids = list({m.station_id for m in members})
    return (
        db.query(Station)
        .filter(Station.station_id.in_(station_ids), Station.active)
        .order_by(Station.name)
        .all()
    )


# ── GET /stations/my/roles ────────────────────────────────────────────────────


@router.get(
    "/my/roles",
    summary="List the current user's active roles at a given station (ACC-B7)",
    dependencies=[Depends(require_role(*ALL_ROLES))],
)
def list_my_roles_at_station(
    station_id: int,
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> List[str]:
    """
    Returns the list of roles the current user holds at the given station.
    Used by the frontend role switcher to populate available roles.
    Administrators always have all roles regardless of StationMember rows.
    """
    if current_user.has_role(ROLE_ADMINISTRATOR):
        return ["Administrator", "Supervisor", "Responder"]

    rows = (
        db.query(StationMember.role)
        .filter(
            StationMember.station_id == station_id,
            StationMember.user_id == current_user.email,
            StationMember.active,
        )
        .distinct()
        .all()
    )
    return [r.role for r in rows]


# ── GET /stations/{id}/members ────────────────────────────────────────────────


@router.get(
    "/{station_id}/members",
    response_model=List[StationMemberRead],
    summary="List members of a station",
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def list_station_members(
    station_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> List[StationMember]:
    _get_station_or_404(station_id, db)
    query = db.query(StationMember).filter(StationMember.station_id == station_id)
    if not include_inactive:
        query = query.filter(StationMember.active)
    return query.order_by(StationMember.user_id, StationMember.role).all()


# ── POST /stations/{id}/members ───────────────────────────────────────────────


@router.post(
    "/{station_id}/members",
    response_model=StationMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to a station with a given role (ACC-B7: one row per role)",
)
def add_station_member(
    station_id: int,
    payload: StationMemberCreate,
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> StationMember:
    """
    ACC-B7: With the new (station_id, user_id, role) constraint, a person can
    be added multiple times with different roles. Each POST creates one row.
    If an inactive row for the same (station, user, role) exists, it is
    reactivated rather than creating a duplicate.
    """
    _get_station_or_404(station_id, db)
    _enforce_role_assignment_permission(current_user, payload.role)

    # Check for existing row with same (station, user, role) -- may be inactive
    existing = (
        db.query(StationMember)
        .filter(
            StationMember.station_id == station_id,
            StationMember.user_id == payload.user_id,
            StationMember.role == payload.role,
        )
        .first()
    )

    if existing:
        if existing.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{payload.user_id}' already has the {payload.role} role "
                    f"at station {station_id}."
                ),
            )
        # Reactivate
        existing.active = True
        existing.preferred_name = payload.preferred_name
        existing.assigned_by = current_user.email
        db.commit()
        db.refresh(existing)
        return existing

    member = StationMember(
        station_id=station_id,
        user_id=payload.user_id,
        preferred_name=payload.preferred_name,
        role=payload.role,
        assigned_by=current_user.email,
        active=True,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"'{payload.user_id}' already has the {payload.role} role "
                f"at station {station_id}."
            ),
        )
    db.refresh(member)
    return member


# ── PATCH /stations/{id}/members/{member_id} ──────────────────────────────────


@router.patch(
    "/{station_id}/members/{member_id}",
    response_model=StationMemberRead,
    summary="Edit a station member's preferred name (ACC-B6)",
)
def update_station_member(
    station_id: int,
    member_id: int,
    payload: StationMemberUpdate,
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> StationMember:
    """
    ACC-B6: Update a member's preferred_name.
    Role changes are intentionally NOT supported via this endpoint -- to change
    a role, deactivate the old row and add a new one. This keeps the audit trail
    clean and prevents accidental privilege escalation via a bulk edit.
    preferred_name updates apply to all rows for this user at this station.
    """
    _get_station_or_404(station_id, db)
    member = _get_member_by_id_or_404(member_id, station_id, db)

    if payload.preferred_name is not None:
        # Apply the name update to all active rows for this user at this station
        # so display name stays consistent across multiple role rows.
        db.query(StationMember).filter(
            StationMember.station_id == station_id,
            StationMember.user_id == member.user_id,
            StationMember.active,
        ).update({"preferred_name": payload.preferred_name})

    db.commit()
    db.refresh(member)
    return member


# ── DELETE /stations/{id}/members/{member_id} ─────────────────────────────────


@router.delete(
    "/{station_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a specific role from a station member (soft delete)",
)
def remove_station_member(
    station_id: int,
    member_id: int,
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> Response:
    """
    Soft-deletes a single StationMember row by member_id.
    If the person has multiple roles, only the specified row is deactivated.
    A person cannot remove their own last active row.
    """
    _get_station_or_404(station_id, db)
    member = _get_member_by_id_or_404(member_id, station_id, db)

    _enforce_role_assignment_permission(current_user, member.role)

    # Prevent self-removal of last active row
    if member.user_id == current_user.email:
        other_active = (
            db.query(StationMember)
            .filter(
                StationMember.station_id == station_id,
                StationMember.user_id == current_user.email,
                StationMember.active,
                StationMember.member_id != member_id,
            )
            .count()
        )
        if other_active == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You cannot remove your last active role at this station. "
                    "Ask another Administrator or Supervisor."
                ),
            )

    member.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── GET /stations/{id}/members/import/template ────────────────────────────────


@router.get(
    "/{station_id}/members/import/template",
    summary="Download CSV template for bulk membership import (ACC-B8)",
    response_class=StreamingResponse,
    dependencies=[Depends(require_role(*SUPERVISOR_PLUS))],
)
def download_member_import_template(
    station_id: int, db: Session = Depends(get_db)
) -> StreamingResponse:
    _get_station_or_404(station_id, db)  # B018 fix: call the function, don't just name it
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "preferred_name", "role"])
    writer.writerow(["jsmith@newbergtownship.org", "Jennifer Smith", "Administrator"])
    writer.writerow(["ejones@newbergtownship.org", "Earl Jones", "Supervisor"])
    writer.writerow(["mwilliams@newbergtownship.org", "Mike Williams", "Responder"])
    content = "\ufeff" + output.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="station_members_template.csv"'
        },
    )


# ── POST /stations/{id}/members/import ───────────────────────────────────────


@router.post(
    "/{station_id}/members/import",
    summary="Bulk import station members from CSV (ACC-B8)",
)
async def import_station_members_csv(
    station_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_role(*SUPERVISOR_PLUS)),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Accepts a CSV with columns: email, preferred_name, role.
    - Creates a new StationMember row for each valid row.
    - Reactivates any matching inactive row rather than creating a duplicate.
    - Skips rows where the (station, email, role) combination is already active.
    - Collects per-row errors without aborting the entire import.
    - Supervisors cannot import Administrator rows; only Administrators can.
    """
    _get_station_or_404(station_id, db)

    raw = await file.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
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
    missing = {h for h in ("email", "role") if h not in reader.fieldnames}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Missing required columns: {', '.join(sorted(missing))}.",
        )

    created = 0
    reactivated = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    for row_num, row in enumerate(reader, start=2):
        email = (row.get("email") or "").strip().lower()
        preferred_name = (row.get("preferred_name") or "").strip() or None
        role = (row.get("role") or "").strip()

        if not email:
            errors.append(
                {"row": row_num, "email": "(blank)", "error": "email is required"}
            )
            continue
        if not role:
            errors.append({"row": row_num, "email": email, "error": "role is required"})
            continue
        if role not in VALID_ROLES:
            errors.append(
                {
                    "row": row_num,
                    "email": email,
                    "error": f"role must be one of: {', '.join(sorted(VALID_ROLES))}",
                }
            )
            continue
        if role == ROLE_ADMINISTRATOR and not current_user.has_role(ROLE_ADMINISTRATOR):
            errors.append(
                {
                    "row": row_num,
                    "email": email,
                    "error": "Only Administrators can import Administrator rows",
                }
            )
            continue

        existing = (
            db.query(StationMember)
            .filter(
                StationMember.station_id == station_id,
                StationMember.user_id == email,
                StationMember.role == role,
            )
            .first()
        )

        if existing:
            if existing.active:
                skipped += 1
                continue
            existing.active = True
            existing.preferred_name = preferred_name
            existing.assigned_by = current_user.email
            reactivated += 1
        else:
            db.add(
                StationMember(
                    station_id=station_id,
                    user_id=email,
                    preferred_name=preferred_name,
                    role=role,
                    assigned_by=current_user.email,
                    active=True,
                )
            )
            created += 1

    db.commit()

    return {
        "created": created,
        "reactivated": reactivated,
        "skipped": skipped,
        "errors": errors,
    }
