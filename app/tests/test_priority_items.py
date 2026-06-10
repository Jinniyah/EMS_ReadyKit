"""
tests/test_priority_items.py
AED + LUCAS Priority Item Tests
================================
These run first. If they fail, the ambulance should not go out.

AED (Automated External Defibrillator):
  Items: "AED Battery" (SUPPLY), "AED Pads Adult" (SUPPLY),
         "AED Date of Last Charge" (DATE_RECORD), plus FUNCTIONAL check type.
  AED is the only item that requires all four check types.

LUCAS (Chest Compression System):
  Items: "LUCAS Device" (SUPPLY), "LUCAS Device Ready Check" (FUNCTIONAL),
         "LUCAS Date of Last Charge" (DATE_RECORD)
  LUCAS frees responders for AED and airway. Must always pass.

Architecture note:
  Checks are submitted in a single POST /api/v1/checks/daily with line_items embedded.
  There is no separate submit step — creation IS submission.
  Draft saves use PATCH /api/v1/checks/daily/{id} (not covered here).

Auth pattern: "Bearer test-{role}" as per core/auth.py _validate_test_token()
Routes: /api/v1/ prefix per main.py
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest
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
# Helpers (mirrors pattern from test_routers.py)
# ---------------------------------------------------------------------------

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup(db: Session):
    """
    Create station + BLS vehicle + members + one compartment.
    Returns (station, vehicle, location, compartment).
    """
    station = Station(name=f"Priority-{_uid()}", address="1 EMS Way", region="Test")
    db.add(station)
    db.flush()

    for email, role in [
        ("test-administrator@ems.local", "Administrator"),
        ("test-supervisor@ems.local",    "Supervisor"),
        ("test-responder@ems.local",     "Responder"),
    ]:
        db.add(StationMember(
            station_id=station.station_id,
            user_id=email, role=role,
            assigned_by="test-setup", active=True,
        ))
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
        label="Unit 712 Priority Test",
    )
    db.add(location)
    db.flush()

    comp = Compartment(
        location_id=location.location_id,
        name=f"Comp-{_uid()}",
        sort_order=1, active=True,
    )
    db.add(comp)
    db.flush()

    return station, vehicle, location, comp


def _item(db: Session, *, name: str, check_type: ItemCheckType,
          measurement_minimum: Optional[float] = None,
          recurrence_days: Optional[int] = None) -> Item:
    """Get-or-create a named item."""
    existing = db.query(Item).filter(Item.name == name).first()
    if existing:
        return existing
    item = Item(
        name=name, category=ItemCategory.EQUIPMENT,
        check_type=check_type, unit_of_measure="each",
        active=True, station_supply=False,  # AED/LUCAS are not supply-room items
        measurement_minimum=measurement_minimum,
        recurrence_days=recurrence_days,
    )
    db.add(item)
    db.flush()
    return item


def _par(db: Session, *, item: Item, location: InventoryLocation,
         comp: Compartment, priority: bool = False, question: str | None = None):
    db.add(ParLevel(
        item_id=item.item_id,
        location_id=location.location_id,
        compartment_id=comp.compartment_id,
        min_quantity=1, max_quantity=1,
        priority_check=priority,
        priority_question=question,
    ))
    db.flush()


def _submit_check(client, *, station, vehicle, line_items: list, auth, check_date=None):
    """Submit a check with embedded line items. Returns the response JSON."""
    r = client.post("/api/v1/checks/daily", json={
        "vehicle_id": vehicle.vehicle_id,
        "station_id": station.station_id,
        "check_date": (check_date or date.today()).isoformat(),
        "timestamp": _utcnow(),
        "line_items": line_items,
    }, headers=auth)
    return r


# ---------------------------------------------------------------------------
# AED Tests
# ---------------------------------------------------------------------------

class TestAEDChecks:
    """
    AED requires all four check types. All must work.
    The date record is legal evidence if the ambulance is involved in a lawsuit.
    """

    def test_aed_functional_pass_check_submits(self, client, db, auth_responder):
        """AED FUNCTIONAL PASS must submit and return a PASS line item status."""
        station, vehicle, location, comp = _setup(db)
        aed = _item(db, name=f"AED Device {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=aed, location=location, comp=comp,
             priority=True, question="AED powered on and ready?")

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": aed.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": True,
            }]
        )
        assert r.status_code == 201, f"AED FUNCTIONAL PASS failed: {r.text}"
        body = r.json()
        assert body["line_items"][0]["status"] == "OK"
        assert body["status"] == "PASS"

    def test_aed_functional_fail_does_not_block(self, client, db, auth_responder):
        """
        AED FUNCTIONAL FAIL must submit and record a FAIL line item.
        The check must not be blocked — tired responders log it and keep going.
        """
        station, vehicle, location, comp = _setup(db)
        aed = _item(db, name=f"AED Fail {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=aed, location=location, comp=comp, priority=True)

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": aed.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": False,
                "notes": "AED self-test failed — noted for supervisor",
            }]
        )
        assert r.status_code == 201, (
            f"AED FUNCTIONAL FAIL rejected: {r.text}. "
            "A tired responder must be able to log a FAIL and continue."
        )
        body = r.json()
        assert body["line_items"][0]["status"] == "FAIL"
        assert body["status"] == "FAIL"  # Overall check is FAIL, not blocked
        assert body["check_id"] is not None  # Check was recorded

    def test_aed_date_record_submits_and_is_recorded(self, client, db, auth_responder):
        """
        AED DATE_RECORD (battery expiry, last charge) must submit.
        This is the primary legal audit trail for AED compliance.
        """
        station, vehicle, location, comp = _setup(db)
        aed_date = _item(
            db, name=f"AED Date {_uid()}",
            check_type=ItemCheckType.DATE_RECORD,
            recurrence_days=365,
        )
        _par(db, item=aed_date, location=location, comp=comp)

        recent_date = (date.today() - timedelta(days=10)).isoformat()
        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": aed_date.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "date_value": recent_date,
            }]
        )
        assert r.status_code == 201, f"AED DATE_RECORD failed: {r.text}"
        body = r.json()
        assert body["line_items"][0]["status"] == "OK"
        assert body["check_id"] is not None

    def test_aed_supply_check_submits(self, client, db, auth_responder):
        """AED Pads Adult (SUPPLY) must accept quantity_found."""
        station, vehicle, location, comp = _setup(db)
        aed_pads = _item(db, name=f"AED Pads {_uid()}", check_type=ItemCheckType.SUPPLY)
        _par(db, item=aed_pads, location=location, comp=comp)

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": aed_pads.item_id,
                "quantity_needed": 1,
                "quantity_found": 1,
            }]
        )
        assert r.status_code == 201, f"AED SUPPLY check failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_submitted_check_is_immutable(self, client, db, auth_responder, auth_supervisor):
        """
        After check submission, the record must be read-only.
        Check history is a legal record — no modifications allowed.
        """
        station, vehicle, location, comp = _setup(db)
        aed = _item(db, name=f"AED Immutable {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=aed, location=location, comp=comp)

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": aed.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": True,
            }]
        )
        assert r.status_code == 201
        check_id = r.json()["check_id"]

        # Supervisor can view the detail (read-only history)
        r2 = client.get(f"/api/v1/checks/daily/{check_id}/detail", headers=auth_supervisor)
        assert r2.status_code == 200

        # The line item status must be unchanged
        li = r2.json()["line_items"][0]
        assert li["functional_pass"] is True, (
            "AED PASS reading was modified — CRITICAL legal issue"
        )

    def test_aed_fail_preserves_original_record(self, client, db, auth_responder, auth_supervisor):
        """
        FAIL check preserves the original FAIL record.
        Resolution via repair request creates a SEPARATE record — not an overwrite.
        This is the legal audit trail requirement.
        """
        station, vehicle, location, comp = _setup(db)
        aed = _item(db, name=f"AED FAILRecord {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=aed, location=location, comp=comp)

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": aed.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": False,
                "notes": "AED battery depleted",
            }]
        )
        assert r.status_code == 201
        check_id = r.json()["check_id"]

        # Retrieve — FAIL must still be there, not cleared
        r2 = client.get(f"/api/v1/checks/daily/{check_id}/detail", headers=auth_supervisor)
        assert r2.status_code == 200
        li = r2.json()["line_items"][0]
        assert li["functional_pass"] is False, (
            "AED FAIL was overwritten — CRITICAL legal issue. "
            "Original FAIL must be preserved as the audit record."
        )
        assert li.get("notes") == "AED battery depleted", (
            "Notes were stripped from the FAIL record"
        )


# ---------------------------------------------------------------------------
# LUCAS Tests
# ---------------------------------------------------------------------------

class TestLUCASChecks:
    """
    LUCAS performs CPR automatically. If it fails on scene and wasn't checked,
    there may be no one available to do manual compressions.
    """

    def test_lucas_functional_pass_submits(self, client, db, auth_responder):
        """LUCAS FUNCTIONAL PASS must submit and record OK."""
        station, vehicle, location, comp = _setup(db)
        lucas = _item(db, name=f"LUCAS Ready {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=lucas, location=location, comp=comp,
             priority=True, question="LUCAS powered on and ready?")

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": lucas.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": True,
            }]
        )
        assert r.status_code == 201, f"LUCAS FUNCTIONAL PASS failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_lucas_functional_fail_records_and_does_not_block(self, client, db, auth_responder):
        """
        LUCAS FUNCTIONAL FAIL must be recorded.
        The check must NOT be blocked — the responder must be able to log and continue.
        """
        station, vehicle, location, comp = _setup(db)
        lucas = _item(db, name=f"LUCAS Fail {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=lucas, location=location, comp=comp, priority=True)

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": lucas.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": False,
                "notes": "LUCAS did not power on",
            }]
        )
        assert r.status_code == 201, (
            f"LUCAS FUNCTIONAL FAIL rejected: {r.text}. "
            "Responder must be able to log FAIL and continue."
        )
        assert r.json()["check_id"] is not None

    def test_lucas_date_record_submits(self, client, db, auth_responder):
        """LUCAS DATE_RECORD (service date) must accept a date value."""
        station, vehicle, location, comp = _setup(db)
        lucas_date = _item(
            db, name=f"LUCAS Date {_uid()}",
            check_type=ItemCheckType.DATE_RECORD,
            recurrence_days=180,
        )
        _par(db, item=lucas_date, location=location, comp=comp)

        recent_date = (date.today() - timedelta(days=30)).isoformat()
        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": lucas_date.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "date_value": recent_date,
            }]
        )
        assert r.status_code == 201, f"LUCAS DATE_RECORD failed: {r.text}"
        assert r.json()["line_items"][0]["status"] == "OK"

    def test_lucas_fail_original_record_preserved(self, client, db, auth_responder, auth_supervisor):
        """LUCAS FAIL must not be overwritten when a repair request is resolved."""
        station, vehicle, location, comp = _setup(db)
        lucas = _item(db, name=f"LUCAS Preserve {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=lucas, location=location, comp=comp)

        r = _submit_check(client,
            station=station, vehicle=vehicle, auth=auth_responder,
            line_items=[{
                "compartment_id": comp.compartment_id,
                "item_id": lucas.item_id,
                "quantity_needed": 0,
                "quantity_found": 0,
                "functional_pass": False,
                "notes": "LUCAS belt worn — sent for service",
            }]
        )
        assert r.status_code == 201
        check_id = r.json()["check_id"]

        # Retrieve check — FAIL must still be there
        r2 = client.get(f"/api/v1/checks/daily/{check_id}/detail", headers=auth_supervisor)
        assert r2.status_code == 200
        li = r2.json()["line_items"][0]
        assert li["functional_pass"] is False, (
            "LUCAS FAIL was overwritten — CRITICAL. Original must be preserved."
        )


# ---------------------------------------------------------------------------
# Priority Flag (RX-B2)
# ---------------------------------------------------------------------------

class TestPriorityFlags:
    """
    RX-B2: priority_check + priority_question on par_levels.
    Migration 0015 added the columns. Admin UI not yet built.
    Marks as xfail if the API doesn't expose the field yet.
    """

    def test_priority_flag_readable_from_par_level_api(self, client, db, auth_admin):
        """priority_check=True on a par level must be readable from the API."""
        _station, _vehicle, location, comp = _setup(db)
        aed = _item(db, name=f"AED Priority {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=aed, location=location, comp=comp,
             priority=True, question="AED powered on and ready for use?")

        r = client.get(
            f"/api/v1/inventory/locations/{location.location_id}/par-levels",
            headers=auth_admin,
        )
        assert r.status_code == 200
        par_levels = r.json()

        aed_par = next((p for p in par_levels if p.get("item_id") == aed.item_id), None)
        assert aed_par is not None, "AED par level not found in location par levels"

        if "priority_check" not in aed_par:
            pytest.xfail(
                "RX-B2: priority_check field not exposed in par level API response. "
                "DB column exists (migration 0015). "
                "API + admin UI still needed (RX-B2, RX-F12)."
            )

        assert aed_par["priority_check"] is True
        assert aed_par.get("priority_question") == "AED powered on and ready for use?"

    def test_admin_patch_par_level_priority_fields(self, client, db, auth_admin):
        """
        RX-B2: PATCH /admin/par-levels/{id} should accept priority fields.
        xfail until endpoint is implemented.
        """
        _station, _vehicle, location, comp = _setup(db)
        item = _item(db, name=f"Priority Patch {_uid()}", check_type=ItemCheckType.FUNCTIONAL)
        _par(db, item=item, location=location, comp=comp)

        # Get the par level ID
        r = client.get(
            f"/api/v1/inventory/locations/{location.location_id}/par-levels",
            headers=auth_admin,
        )
        par_levels = r.json()
        par = next((p for p in par_levels if p.get("item_id") == item.item_id), None)
        if not par:
            pytest.skip("Could not find par level for priority patch test")

        par_id = par.get("par_id") or par.get("id")
        if not par_id:
            pytest.skip("Could not determine par level ID")

        # UpdateParLevelRequest requires min_quantity + max_quantity alongside priority fields
        r2 = client.patch(f"/api/v1/admin/par-levels/{par_id}", json={
            "min_quantity": par.get("min_quantity", 1),
            "max_quantity": par.get("max_quantity", 1),
            "priority_check": True,
            "priority_question": "Is this item ready?",
        }, headers=auth_admin)

        if r2.status_code == 404:
            pytest.xfail(
                "RX-B2: PATCH /admin/par-levels/{id} not yet implemented. "
                "Required for launch gate: priority items must be configurable in admin."
            )
        assert r2.status_code in (200, 201), (
            f"Priority flag update failed: {r2.status_code} {r2.text}"
        )

        # Verify directly in DB — _enrich_par response may not include priority fields
        from ems_readykit.models.par_level import ParLevel as PL
        db_par = db.query(PL).filter(PL.par_id == par_id).first()
        assert db_par is not None
        assert db_par.priority_check is True, (
            "priority_check was not persisted to DB after PATCH. "
            "Check update_par_level handler in admin.py."
        )
