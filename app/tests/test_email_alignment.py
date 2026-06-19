"""
tests/test_email_alignment.py
LAUNCH-OPS9 — GET /admin/email-alignment-check

Flags StationMember rows whose user_id doesn't look like a valid email
address (e.g. an admin typed a display name instead of an email during
manual add or CSV import). Read-only diagnostic, Admin only.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def alignment_station(db: Session):
    station = Station(name=f"Alignment-{_uid()}", address="1 Main St", region="R")
    db.add(station)
    db.flush()
    return station


def _add_member(
    db: Session,
    station_id: int,
    user_id: str,
    role: str = "Responder",
    active: bool = True,
):
    member = StationMember(
        station_id=station_id,
        user_id=user_id,
        role=role,
        assigned_by="test-administrator@ems.local",
        active=active,
    )
    db.add(member)
    db.flush()
    return member


# ── Happy path: all valid emails -> nothing flagged ────────────────────────────


def test_all_valid_emails_flags_nothing(client, db, auth_admin, alignment_station):
    _add_member(db, alignment_station.station_id, "jsmith@newbergtownship.org")
    _add_member(
        db,
        alignment_station.station_id,
        "ejones@newbergtownship.org",
        role="Supervisor",
    )
    db.commit()

    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 2
    assert body["flagged"] == 0
    assert body["issues"] == []


# ── Display name instead of email ──────────────────────────────────────────────


def test_display_name_is_flagged(client, db, auth_admin, alignment_station):
    _add_member(db, alignment_station.station_id, "Earl Jones")
    db.commit()

    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 1
    assert body["flagged"] == 1
    assert "space" in body["issues"][0]["reason"]
    assert body["issues"][0]["user_id"] == "Earl Jones"
    assert body["issues"][0]["station_name"] == alignment_station.name


# ── Missing @ or domain ─────────────────────────────────────────────────────────


def test_malformed_email_shapes_are_flagged(client, db, auth_admin, alignment_station):
    _add_member(db, alignment_station.station_id, "ejonesnewbergtownship.org")  # no @
    _add_member(db, alignment_station.station_id, "ejones@newbergtownship")  # no TLD
    db.commit()

    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 2
    assert body["flagged"] == 2


# ── Uppercase email is flagged (storage convention is lowercase) ───────────────


def test_uppercase_email_is_flagged(client, db, auth_admin, alignment_station):
    _add_member(db, alignment_station.station_id, "EJones@NewbergTownship.org")
    db.commit()

    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["flagged"] == 1
    assert "lowercase" in body["issues"][0]["reason"]


# ── Inactive rows excluded by default, included when requested ────────────────


def test_inactive_rows_excluded_unless_requested(
    client, db, auth_admin, alignment_station
):
    _add_member(db, alignment_station.station_id, "Earl Jones", active=False)
    db.commit()

    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    assert resp.json()["checked"] == 0

    resp2 = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id, "include_inactive": True},
        headers=auth_admin,
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["checked"] == 1
    assert body2["flagged"] == 1
    assert body2["issues"][0]["active"] is False


# ── No station_id filter -> checks across all stations ─────────────────────────


def test_no_station_filter_checks_all_stations(client, db, auth_admin):
    station_a = Station(name=f"A-{_uid()}", address="1 Main St", region="R")
    station_b = Station(name=f"B-{_uid()}", address="2 Main St", region="R")
    db.add_all([station_a, station_b])
    db.flush()
    _add_member(db, station_a.station_id, "valid@newbergtownship.org")
    _add_member(db, station_b.station_id, "Bad Name")
    db.commit()

    resp = client.get("/api/v1/admin/email-alignment-check", headers=auth_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] >= 2
    flagged_ids = [issue["user_id"] for issue in body["issues"]]
    assert "Bad Name" in flagged_ids


# ── RBAC: Supervisor and Responder are forbidden ───────────────────────────────


def test_supervisor_forbidden(client, db, auth_supervisor, alignment_station):
    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_supervisor,
    )
    assert resp.status_code == 403


def test_responder_forbidden(client, db, auth_responder, alignment_station):
    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_responder,
    )
    assert resp.status_code == 403


def test_unauthenticated_rejected(client, alignment_station):
    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
    )
    assert resp.status_code in (401, 403)


# ── Blank user_id is flagged ────────────────────────────────────────────────────


def test_blank_user_id_is_flagged(client, db, auth_admin, alignment_station):
    _add_member(db, alignment_station.station_id, "   ")
    db.commit()

    resp = client.get(
        "/api/v1/admin/email-alignment-check",
        params={"station_id": alignment_station.station_id},
        headers=auth_admin,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["flagged"] == 1
    assert "blank" in body["issues"][0]["reason"]
