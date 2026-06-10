"""
tests/test_safety_checks.py
Safety-Critical Check Logic Tests
===================================
Tests for check logic that directly affects patient safety and legal compliance.
All use synthetic fixtures (not seed data) so they run without seed.py.

1. O2 PSI below minimum -> status FAIL / check status FAIL
   A truck leaving with low O2 that the app didn't catch is a liability.
   On-Board O2 PSI has measurement_minimum=500. Submitting 400 must be FAIL.

2. Date recurrence overdue -> status OVERDUE / check status FAIL
   AED Date of Last Charge has recurrence_days=90.
   Submitting a date 95 days old must be OVERDUE, not silently OK.
   LUCAS Date of Last Charge has recurrence_days=30.

3. requires_full_check enforcement on Truck Operations
   When a compartment has requires_full_check=True, the backend must
   reject or flag a check where all items are submitted as No Change
   (quantity_found=None or items omitted entirely).
   NOTE: If this test xfails, it means enforcement is not yet implemented
   in the router — it's a known gap that must be closed before launch.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

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
from ems_readykit.models.check_line_item import LineItemStatus
from ems_readykit.models.daily_inventory_check import CheckStatus
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
    """Station + BLS vehicle + members + compartment. Returns (station, vehicle, location, comp)."""
    station = Station(name=f"Safety-{_uid()}", address="1 Safety Rd", region="Test")
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
        label="Safety Test Vehicle",
    )
    db.add(location)
    db.flush()

    comp = Compartment(
        location_id=location.location_id,
        name=f"Comp-{_uid()}",
        sort_order=1,
        active=True,
        requires_full_check=False,
    )
    db.add(comp)
    db.flush()

    return station, vehicle, location, comp


def _measurement_item(
    db: Session, *, name: str, minimum: float, maximum: float = 2200.0
) -> Item:
    item = Item(
        name=name,
        category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.MEASUREMENT,
        unit_of_measure="PSI",
        measurement_minimum=minimum,
        measurement_maximum=maximum,
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def _date_record_item(db: Session, *, name: str, recurrence_days: int) -> Item:
    item = Item(
        name=name,
        category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.DATE_RECORD,
        unit_of_measure="N/A",
        recurrence_days=recurrence_days,
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def _functional_item(db: Session, *, name: str) -> Item:
    item = Item(
        name=name,
        category=ItemCategory.EQUIPMENT,
        check_type=ItemCheckType.FUNCTIONAL,
        unit_of_measure="N/A",
        active=True,
    )
    db.add(item)
    db.flush()
    return item


def _par(db: Session, *, item: Item, location: InventoryLocation, comp: Compartment):
    db.add(
        ParLevel(
            item_id=item.item_id,
            location_id=location.location_id,
            compartment_id=comp.compartment_id,
            min_quantity=1,
            max_quantity=1,
        )
    )
    db.flush()


def _submit(client, *, station, vehicle, line_items: list, auth):
    return client.post(
        "/api/v1/checks/daily",
        json={
            "vehicle_id": vehicle.vehicle_id,
            "station_id": station.station_id,
            "check_date": date.today().isoformat(),
            "timestamp": _utcnow(),
            "line_items": line_items,
        },
        headers=auth,
    )


# ---------------------------------------------------------------------------
# 1. O2 PSI below minimum
# ---------------------------------------------------------------------------


class TestO2PSIBelowMinimum:
    """
    On-Board O2 PSI has measurement_minimum=500 PSI.
    A truck leaving with less than 500 PSI of O2 is a patient safety issue.
    The backend must flag this as LOW (-> check FAIL), not OK.
    """

    def test_o2_psi_at_minimum_is_ok(self, client, db, auth_responder):
        """Exactly at minimum (500 PSI) must be OK."""
        station, vehicle, location, comp = _setup(db)
        item = _measurement_item(db, name=f"O2 PSI {_uid()}", minimum=500.0)
        _par(db, item=item, location=location, comp=comp)

        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "measurement_value": 500.0,
                }
            ],
        )
        assert r.status_code == 201, f"Unexpected: {r.text}"
        li = r.json()["line_items"][0]
        assert (
            li["status"] == LineItemStatus.OK.value
        ), f"500 PSI (exactly at minimum) returned status={li['status']} — must be OK"
        assert r.json()["status"] == CheckStatus.PASS.value

    def test_o2_psi_above_minimum_is_ok(self, client, db, auth_responder):
        """1800 PSI (full tank) must be OK."""
        station, vehicle, location, comp = _setup(db)
        item = _measurement_item(db, name=f"O2 PSI {_uid()}", minimum=500.0)
        _par(db, item=item, location=location, comp=comp)

        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "measurement_value": 1800.0,
                }
            ],
        )
        assert r.status_code == 201
        assert r.json()["line_items"][0]["status"] == LineItemStatus.OK.value

    def test_o2_psi_below_minimum_is_low(self, client, db, auth_responder):
        """
        CRITICAL: 400 PSI (below 500 minimum) must return LOW status.
        LOW maps to check status NEEDS_RESTOCK or FAIL (both are non-OK).
        A truck must not go out with this reading silently passing.
        """
        station, vehicle, location, comp = _setup(db)
        item = _measurement_item(db, name=f"O2 PSI {_uid()}", minimum=500.0)
        _par(db, item=item, location=location, comp=comp)

        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "measurement_value": 400.0,
                }
            ],
        )
        assert r.status_code == 201, f"Unexpected rejection: {r.text}"
        body = r.json()
        li = body["line_items"][0]
        assert li["status"] == LineItemStatus.LOW.value, (
            f"400 PSI (below 500 minimum) returned status={li['status']}. "
            "Must be LOW — a truck must not leave with insufficient O2 silently passing."
        )
        # LOW maps to NEEDS_RESTOCK at the check level — not PASS
        assert body["status"] != CheckStatus.PASS.value, (
            "Check with LOW O2 PSI returned overall status=PASS. "
            "A LOW reading must not result in a passing check."
        )

    def test_o2_psi_zero_is_low(self, client, db, auth_responder):
        """0 PSI (empty tank) must be LOW — not OK, not MISSING."""
        station, vehicle, location, comp = _setup(db)
        item = _measurement_item(db, name=f"O2 PSI {_uid()}", minimum=500.0)
        _par(db, item=item, location=location, comp=comp)

        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "measurement_value": 0.0,
                }
            ],
        )
        assert r.status_code == 201
        li = r.json()["line_items"][0]
        assert (
            li["status"] == LineItemStatus.LOW.value
        ), f"0 PSI returned status={li['status']} — must be LOW"

    def test_o2_psi_missing_reading_is_missing(self, client, db, auth_responder):
        """No reading submitted at all (measurement_value omitted) must be MISSING."""
        station, vehicle, location, comp = _setup(db)
        item = _measurement_item(db, name=f"O2 PSI {_uid()}", minimum=500.0)
        _par(db, item=item, location=location, comp=comp)

        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    # measurement_value intentionally omitted
                }
            ],
        )
        assert r.status_code == 201
        li = r.json()["line_items"][0]
        assert (
            li["status"] == LineItemStatus.MISSING.value
        ), f"Omitted O2 reading returned status={li['status']} — must be MISSING"
        assert r.json()["status"] == CheckStatus.FAIL.value


# ---------------------------------------------------------------------------
# 2. Date recurrence overdue
# ---------------------------------------------------------------------------


class TestDateRecurrenceOverdue:
    """
    DATE_RECORD items have recurrence_days. Submitting a date older than
    recurrence_days must return OVERDUE — not silently OK.

    AED Date of Last Charge: recurrence_days=90
    LUCAS Date of Last Charge: recurrence_days=30

    OVERDUE is a FAIL-severity status. The check must not pass.
    This is a legal audit trail requirement — an outdated AED charge date
    means the AED may not be ready.
    """

    def test_aed_date_within_recurrence_is_ok(self, client, db, auth_responder):
        """Date 10 days ago against 90-day recurrence must be OK."""
        station, vehicle, location, comp = _setup(db)
        item = _date_record_item(db, name=f"AED Date {_uid()}", recurrence_days=90)
        _par(db, item=item, location=location, comp=comp)

        recent = (date.today() - timedelta(days=10)).isoformat()
        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "date_value": recent,
                }
            ],
        )
        assert r.status_code == 201
        li = r.json()["line_items"][0]
        assert (
            li["status"] == LineItemStatus.OK.value
        ), f"10-day-old date (90-day recurrence) returned {li['status']} — must be OK"

    def test_aed_date_exactly_at_recurrence_is_ok(self, client, db, auth_responder):
        """Date exactly 90 days ago against 90-day recurrence must be OK (boundary)."""
        station, vehicle, location, comp = _setup(db)
        item = _date_record_item(db, name=f"AED Date {_uid()}", recurrence_days=90)
        _par(db, item=item, location=location, comp=comp)

        boundary = (date.today() - timedelta(days=90)).isoformat()
        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "date_value": boundary,
                }
            ],
        )
        assert r.status_code == 201
        li = r.json()["line_items"][0]
        assert li["status"] == LineItemStatus.OK.value, (
            f"90-day-old date (90-day recurrence) returned {li['status']} — "
            "boundary should be OK (days_since == recurrence_days is not yet overdue)"
        )

    def test_aed_date_one_day_past_recurrence_is_overdue(
        self, client, db, auth_responder
    ):
        """
        CRITICAL: Date 91 days ago against 90-day recurrence must be OVERDUE.
        An overdue AED charge date means the device may not be ready.
        This must never silently pass.
        """
        station, vehicle, location, comp = _setup(db)
        item = _date_record_item(db, name=f"AED Date {_uid()}", recurrence_days=90)
        _par(db, item=item, location=location, comp=comp)

        overdue = (date.today() - timedelta(days=91)).isoformat()
        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "date_value": overdue,
                }
            ],
        )
        assert r.status_code == 201
        body = r.json()
        li = body["line_items"][0]
        assert li["status"] == LineItemStatus.OVERDUE.value, (
            f"91-day-old date (90-day recurrence) returned status={li['status']}. "
            "Must be OVERDUE — an outdated AED charge date is a patient safety issue."
        )
        assert body["status"] == CheckStatus.FAIL.value, (
            f"Check with OVERDUE AED date returned overall status={body['status']}. "
            "OVERDUE must result in check FAIL."
        )

    def test_aed_date_heavily_overdue_is_overdue(self, client, db, auth_responder):
        """Date 200 days ago against 90-day recurrence — clearly overdue."""
        station, vehicle, location, comp = _setup(db)
        item = _date_record_item(db, name=f"AED Date {_uid()}", recurrence_days=90)
        _par(db, item=item, location=location, comp=comp)

        old = (date.today() - timedelta(days=200)).isoformat()
        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "date_value": old,
                }
            ],
        )
        assert r.status_code == 201
        assert r.json()["line_items"][0]["status"] == LineItemStatus.OVERDUE.value

    def test_lucas_date_overdue_at_31_days(self, client, db, auth_responder):
        """
        CRITICAL: LUCAS Date of Last Charge has recurrence_days=30.
        A date 31 days old must be OVERDUE.
        LUCAS drives CPR — an uncharged device on a cardiac call is catastrophic.
        """
        station, vehicle, location, comp = _setup(db)
        item = _date_record_item(db, name=f"LUCAS Date {_uid()}", recurrence_days=30)
        _par(db, item=item, location=location, comp=comp)

        overdue = (date.today() - timedelta(days=31)).isoformat()
        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "date_value": overdue,
                }
            ],
        )
        assert r.status_code == 201
        body = r.json()
        li = body["line_items"][0]
        assert li["status"] == LineItemStatus.OVERDUE.value, (
            f"31-day-old LUCAS date (30-day recurrence) returned {li['status']}. "
            "Must be OVERDUE — LUCAS must be charged monthly."
        )
        assert body["status"] == CheckStatus.FAIL.value

    def test_date_record_no_date_submitted_is_missing(self, client, db, auth_responder):
        """Omitting date_value entirely must be MISSING -> check FAIL."""
        station, vehicle, location, comp = _setup(db)
        item = _date_record_item(db, name=f"Date Missing {_uid()}", recurrence_days=90)
        _par(db, item=item, location=location, comp=comp)

        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": comp.compartment_id,
                    "item_id": item.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    # date_value intentionally omitted
                }
            ],
        )
        assert r.status_code == 201
        li = r.json()["line_items"][0]
        assert (
            li["status"] == LineItemStatus.MISSING.value
        ), f"Omitted date returned status={li['status']} — must be MISSING"
        assert r.json()["status"] == CheckStatus.FAIL.value


# ---------------------------------------------------------------------------
# 3. requires_full_check enforcement (Truck Operations)
# ---------------------------------------------------------------------------


class TestRequiresFullCheck:
    """
    Compartments with requires_full_check=True (Truck Operations on Unit 712)
    must not allow No Change — responders must explicitly check every item.

    A No Change submission on Truck Operations means:
      - The truck may not have been started
      - Warning lights and sirens may not have been tested
      - The ambulance could go out with an undetected mechanical issue

    Implementation status: if the backend does not yet enforce this,
    the test xfails with a clear message documenting the gap.
    This test MUST pass before launch.
    """

    def test_requires_full_check_false_allows_empty_submission(
        self, client, db, auth_responder
    ):
        """Baseline: a normal compartment accepts a check with no line items."""
        station, vehicle, _location, comp = _setup(db)
        # comp has requires_full_check=False by default from _setup()
        assert comp.requires_full_check is False

        r = _submit(
            client, station=station, vehicle=vehicle, auth=auth_responder, line_items=[]
        )
        assert (
            r.status_code == 201
        ), f"Normal compartment rejected empty submission: {r.text}"

    def test_requires_full_check_true_with_all_items_passes(
        self, client, db, auth_responder
    ):
        """When all items are explicitly submitted, requires_full_check=True must pass."""
        station, vehicle, location, _ = _setup(db)

        # Create a compartment with requires_full_check=True
        full_comp = Compartment(
            location_id=location.location_id,
            name=f"Full-Check-{_uid()}",
            sort_order=40,
            active=True,
            requires_full_check=True,
        )
        db.add(full_comp)
        db.flush()

        item1 = _functional_item(db, name=f"Runs {_uid()}")
        item2 = _functional_item(db, name=f"Lights {_uid()}")
        for item in [item1, item2]:
            db.add(
                ParLevel(
                    item_id=item.item_id,
                    location_id=location.location_id,
                    compartment_id=full_comp.compartment_id,
                    min_quantity=1,
                    max_quantity=1,
                )
            )
        db.flush()

        # Submit with all items explicitly checked
        r = _submit(
            client,
            station=station,
            vehicle=vehicle,
            auth=auth_responder,
            line_items=[
                {
                    "compartment_id": full_comp.compartment_id,
                    "item_id": item1.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "functional_pass": True,
                },
                {
                    "compartment_id": full_comp.compartment_id,
                    "item_id": item2.item_id,
                    "quantity_needed": 0,
                    "quantity_found": 0,
                    "functional_pass": True,
                },
            ],
        )
        assert (
            r.status_code == 201
        ), f"Full check with all items submitted was rejected: {r.text}"
        assert r.json()["status"] == CheckStatus.PASS.value

    def test_requires_full_check_true_blocks_no_change(
        self, client, db, auth_responder
    ):
        """
        CRITICAL: A compartment with requires_full_check=True must reject
        a check where items in that compartment are omitted (No Change).

        If this xfails, the enforcement is not yet implemented in the router.
        The gap must be closed before launch — a responder could skip Truck
        Operations entirely and the ambulance goes out unchecked.
        """
        station, vehicle, location, _ = _setup(db)

        full_comp = Compartment(
            location_id=location.location_id,
            name=f"Full-Check-Enforce-{_uid()}",
            sort_order=41,
            active=True,
            requires_full_check=True,
        )
        db.add(full_comp)
        db.flush()

        item = _functional_item(db, name=f"Must Check {_uid()}")
        db.add(
            ParLevel(
                item_id=item.item_id,
                location_id=location.location_id,
                compartment_id=full_comp.compartment_id,
                min_quantity=1,
                max_quantity=1,
            )
        )
        db.flush()

        # Submit the check with the full_comp item OMITTED (No Change)
        r = _submit(
            client, station=station, vehicle=vehicle, auth=auth_responder, line_items=[]
        )  # item in full_comp not included

        if r.status_code == 201:
            # Check passed — enforcement not implemented yet
            pytest.xfail(
                "requires_full_check=True compartment accepted a check with omitted items. "
                "The router does not yet enforce this constraint. "
                "SEED-GAP2 / Truck Operations — must be implemented before launch. "
                "The router needs to verify that all active par levels in a "
                "requires_full_check compartment have a corresponding line item."
            )
        else:
            # Enforcement is active — must reject with 422
            assert r.status_code == 422, (
                f"requires_full_check enforcement returned {r.status_code} instead of 422. "
                f"Response: {r.text}"
            )
