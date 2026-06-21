"""
tests/test_persona_responder.py
Persona 1: Jamie — Tired Responder (Hour 11 of 12)
====================================================
Verifies the core check wizard flow from a Responder's perspective.
Every test here represents something that must work even when Jamie is
stressed, exhausted, and operating on autopilot.

Architecture: checks submitted as single POST /api/v1/checks/daily
with line_items embedded. No separate submit step.

Auth: "Bearer test-responder"
"""

from __future__ import annotations

import json as _json
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ems_readykit.models import (
    Compartment,
    InventoryLocation,
    Item,
    ItemCategory,
    ItemCheckType,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station_member import StationMember

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup(db: Session):
    """
    Create station + BLS vehicle + members + compartment + one item per check type.
    Returns (station, vehicle, location, comp, items_by_check_type).
    """
    station = Station(name=f"Responder-{_uid()}", address="1 EMS Rd", region="Test")
    db.add(station)
    db.flush()

    for email, role in [
        ("test-responder@ems.local", "Responder"),
        ("test-supervisor@ems.local", "Supervisor"),
        ("test-administrator@ems.local", "Administrator"),
    ]:
        db.add(
            StationMember(
                station_id=station.station_id,
                user_id=email,
                role=role,
                assigned_by="test-setup",
                active=True,
            )
        )
    db.flush()

    vehicle = Vehicle(
        station_id=station.station_id,
        vehicle_number=f"712-{_uid()}",
        vehicle_type=VehicleType.BLS,
    )
    db.add(vehicle)
    db.flush()

    location = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station.station_id,
        vehicle_id=vehicle.vehicle_id,
        label="Unit 712 Responder Test",
    )
    db.add(location)
    db.flush()

    comp = Compartment(
        location_id=location.location_id,
        name=f"Comp-{_uid()}",
        sort_order=1,
        active=True,
    )
    db.add(comp)
    db.flush()

    items = {}
    for ct in [
        ItemCheckType.SUPPLY,
        ItemCheckType.MEASUREMENT,
        ItemCheckType.FUNCTIONAL,
        ItemCheckType.DATE_RECORD,
        ItemCheckType.DOCUMENT,
    ]:
        item = Item(
            name=f"{ct.value}-{_uid()}",
            station_id=station.station_id,
            category=ItemCategory.EQUIPMENT,
            check_type=ct,
            unit_of_measure="each",
            active=True,
            measurement_minimum=500.0 if ct == ItemCheckType.MEASUREMENT else None,
            recurrence_days=90 if ct == ItemCheckType.DATE_RECORD else None,
        )
        db.add(item)
        db.flush()
        db.add(
            ParLevel(
                item_id=item.item_id,
                location_id=location.location_id,
                compartment_id=comp.compartment_id,
                min_quantity=2,
                max_quantity=2,
            )
        )
        items[ct] = item

    db.flush()
    return station, vehicle, location, comp, items


def _line_item_for(
    item: Item, comp: Compartment, *, fail: bool = False, notes: str | None = None
) -> dict:
    """Build a line item dict for the given item with sensible defaults."""
    base = {
        "compartment_id": comp.compartment_id,
        "item_id": item.item_id,
        "quantity_needed": 2,
        "quantity_found": 2,
    }
    if item.check_type == ItemCheckType.MEASUREMENT:
        base["quantity_needed"] = 0
        base["quantity_found"] = 0
        base["measurement_value"] = 200.0 if fail else 1800.0
    elif item.check_type == ItemCheckType.FUNCTIONAL:
        base["quantity_needed"] = 0
        base["quantity_found"] = 0
        base["functional_pass"] = False if fail else True
    elif item.check_type == ItemCheckType.DATE_RECORD:
        base["quantity_needed"] = 0
        base["quantity_found"] = 0
        if fail:
            base["date_value"] = (date.today() - timedelta(days=100)).isoformat()
        else:
            base["date_value"] = (date.today() - timedelta(days=10)).isoformat()
    elif item.check_type == ItemCheckType.DOCUMENT:
        base["quantity_found"] = 0 if fail else 2
    if notes:
        base["notes"] = notes
    return base


# ---------------------------------------------------------------------------
# Core wizard — all five check types
# ---------------------------------------------------------------------------


class TestResponderAllCheckTypes:
    """Jamie must be able to submit every check type without confusion."""

    def test_supply_check_submits_ok(self, client, db, auth_responder):
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.SUPPLY]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [_line_item_for(item, comp)],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, f"SUPPLY check failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_measurement_check_submits_ok(self, client, db, auth_responder):
        """O2 PSI MEASUREMENT check — numeric reading accepted."""
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.MEASUREMENT]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [_line_item_for(item, comp)],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, f"MEASUREMENT check failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_functional_check_pass_submits(self, client, db, auth_responder):
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.FUNCTIONAL]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [_line_item_for(item, comp)],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, f"FUNCTIONAL PASS failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_date_record_check_submits(self, client, db, auth_responder):
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.DATE_RECORD]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [_line_item_for(item, comp)],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, f"DATE_RECORD check failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_document_check_submits(self, client, db, auth_responder):
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.DOCUMENT]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [_line_item_for(item, comp)],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, f"DOCUMENT check failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"


# ---------------------------------------------------------------------------
# FAIL + comment — the core tired-responder scenario
# ---------------------------------------------------------------------------


class TestResponderFailAndContinue:
    """
    The most important responder UX test:
    Jamie submits a FAIL, adds a short comment, and the check records it.
    The check is not blocked — it still submits with status FAIL.
    """

    def test_functional_fail_with_comment_submits(self, client, db, auth_responder):
        """
        CRITICAL: FAIL + short comment must submit.
        Status will be FAIL — but that's correct and expected.
        The check must not be rejected.
        """
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.FUNCTIONAL]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [
                    _line_item_for(
                        item, comp, fail=True, notes="Not working, noted for supervisor"
                    ),
                ],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, (
            f"FAIL with comment was rejected: {r.text}. "
            "Tired responder must be able to log FAIL and continue."
        )
        body = r.json()
        assert body["status"] == "FAIL"  # Correctly recorded
        assert body["check_id"] is not None
        assert body["line_items"][0]["functional_pass"] is False

    def test_check_with_mixed_pass_and_fail_submits(self, client, db, auth_responder):
        """A check with some PASS and one FAIL must submit — overall status is FAIL."""
        station, vehicle, _, comp, items = _setup(db)

        line_items = [
            _line_item_for(items[ItemCheckType.SUPPLY], comp),  # OK
            _line_item_for(
                items[ItemCheckType.FUNCTIONAL],
                comp,
                fail=True,
                notes="Test fail — automated",
            ),  # FAIL
        ]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": line_items,
            },
            headers=auth_responder,
        )
        assert r.status_code == 201, f"Mixed PASS/FAIL check failed to submit: {r.text}"
        assert r.json()["status"] == "FAIL"

    def test_submitted_check_appears_in_my_history(self, client, db, auth_responder):
        """Submitted check must appear in GET /checks/daily/my-history."""
        station, vehicle, _, comp, items = _setup(db)
        item = items[ItemCheckType.SUPPLY]

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
                "line_items": [_line_item_for(item, comp)],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201
        check_id = r.json()["check_id"]

        history_r = client.get(
            "/api/v1/checks/daily/my-history", headers=auth_responder
        )
        assert history_r.status_code == 200
        ids = [c.get("check_id") for c in history_r.json()]
        assert check_id in ids, "Submitted check not in responder history"


# ---------------------------------------------------------------------------
# Multiple checks per day
# ---------------------------------------------------------------------------


class TestMultipleChecksPerDay:

    def test_two_checks_same_day_allowed(self, client, db, auth_responder):
        """
        Multiple checks per vehicle per calendar day must be allowed.
        Shift-start + post-call + shift-end = multiple legal checks per day.
        """
        station, vehicle, _, _, _ = _setup(db)

        today = date.today().isoformat()

        r1 = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": today,
                "timestamp": _utcnow(),
            },
            headers=auth_responder,
        )
        assert r1.status_code == 201

        r2 = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": today,
                "timestamp": _utcnow(),
            },
            headers=auth_responder,
        )
        assert r2.status_code == 201, (
            f"Second check same day rejected: {r2.text}. "
            "Multiple checks per day are legally required."
        )
        assert r1.json()["check_id"] != r2.json()["check_id"]


# ---------------------------------------------------------------------------
# Role boundary
# ---------------------------------------------------------------------------


class TestResponderRoleBoundary:

    def test_responder_cannot_create_item(self, client, auth_responder):
        """Responder gets 403 on admin item creation — not a 500, not a 200."""
        r = client.post(
            "/api/v1/items",
            json={
                "name": f"Unauthorized-{_uid()}",
                "category": "Equipment",
                "unit_of_measure": "each",
            },
            headers=auth_responder,
        )
        assert r.status_code == 403, (
            f"Responder not denied item creation. "
            f"Expected 403, got {r.status_code}."
        )

    def test_responder_cannot_view_all_stations(self, client, auth_responder):
        """GET /stations is Admin only. Responder gets 403."""
        r = client.get("/api/v1/stations", headers=auth_responder)
        assert r.status_code == 403

    def test_responder_can_view_own_stations(self, client, auth_responder):
        """Responder can use GET /stations/my."""
        r = client.get("/api/v1/stations/my", headers=auth_responder)
        assert r.status_code == 200

    def test_responder_cannot_soft_delete_check(self, client, auth_responder):
        """Soft-delete is Supervisor+ only. Responder gets 403."""
        r = client.request(
            "DELETE",
            "/api/v1/checks/daily/99999",
            content=_json.dumps({"deletion_reason": "Unauthorized attempt"}),
            headers={**auth_responder, "Content-Type": "application/json"},
        )
        assert r.status_code in (403, 404)

    def test_responder_cannot_access_audit_log(self, client, auth_responder):
        """Audit log is Supervisor+ only."""
        r = client.get("/api/v1/audit", headers=auth_responder)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Draft station scoping (shift handoff)
# ---------------------------------------------------------------------------


class TestDraftStationScope:

    def test_station_today_visible_to_supervisor_at_same_station(
        self, client, db, auth_responder, auth_supervisor
    ):
        """
        A check submitted by a responder must be visible to supervisors
        at the same station when querying today's station checks.
        Supports shift handoff.
        """
        station, vehicle, _, _, _ = _setup(db)

        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": date.today().isoformat(),
                "timestamp": _utcnow(),
            },
            headers=auth_responder,
        )
        assert r.status_code == 201
        check_id = r.json()["check_id"]

        r2 = client.get(
            f"/api/v1/checks/daily/station/{station.station_id}/today",
            headers=auth_supervisor,
        )
        assert r2.status_code == 200
        ids = [c.get("check_id") for c in r2.json()]
        assert check_id in ids, (
            "Responder check not visible to supervisor in station today view. "
            "Station-scoped visibility required for shift handoff."
        )
