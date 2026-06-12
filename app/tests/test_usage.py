"""
tests/test_usage.py
After-Call Reset -- POST /checks/usage and GET /checks/usage/* endpoints.

Covers:
  - POST /checks/usage happy path (creates event, does NOT touch supply room)
  - POST /checks/usage with location_id for portable locations (USAGE-B2)
  - POST /checks/usage rejects both vehicle_id and location_id set
  - POST /checks/usage rejects non-SUPPLY items
  - POST /checks/usage rejects unknown item_ids
  - POST /checks/usage non-member gets 403
  - POST /checks/usage unknown location gets 404
  - POST /checks/usage location from wrong station gets 422
  - GET /checks/usage/station/{id} returns history
  - GET /checks/usage/station/{id}/frequent returns aggregated data
  - GET /checks/usage/station/{id}/frequent returns empty list with no data
  - GET /checks/daily/last-readings subtracts post-check usage (USAGE-B1)
  - GET /checks/daily/last-readings floors at 0, never returns negative
  - GET /checks/daily/last-readings ignores usage before the check
  - GET /checks/daily/last-readings does not subtract for non-SUPPLY items
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.usage_event import UsageEvent, UsageEventItem
from ems_readykit.models.vehicle import Vehicle, VehicleType

# -- Fixtures ------------------------------------------------------------------


@pytest.fixture
def station(db):
    s = Station(
        name="Usage Test Station", address="1 Main St", region="Test", active=True
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def membership(db, station, auth_responder):
    # auth_responder token maps to test-responder@ems.local
    m = StationMember(
        station_id=station.station_id,
        user_id="test-responder@ems.local",
        role="RESPONDER",
        assigned_by="test-setup",
        active=True,
    )
    db.add(m)
    db.flush()
    return m


@pytest.fixture
def vehicle(db, station):
    v = db.query(Vehicle).filter(Vehicle.vehicle_number == "U-USAGE").first()
    if v is None:
        v = Vehicle(
            station_id=station.station_id,
            vehicle_number="U-USAGE",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v)
        db.flush()
    else:
        v.station_id = station.station_id
        db.flush()
    return v


@pytest.fixture
def portable_location(db, station):
    loc = InventoryLocation(
        location_type=LocationType.JUMP_BAG,
        station_id=station.station_id,
        label="Usage Test Jump Bag",
    )
    db.add(loc)
    db.flush()
    return loc


@pytest.fixture
def supply_room(db, station):
    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Usage Test Supply Room",
    )
    db.add(loc)
    db.flush()
    db.add(
        Compartment(
            location_id=loc.location_id,
            name="Shelf 1",
            location_descriptor="Shelf 1",
            sort_order=1,
            active=True,
        )
    )
    db.flush()
    return loc


@pytest.fixture
def supply_item(db):
    item = db.query(Item).filter(Item.name == "Usage Test Gauze").first()
    if item is None:
        item = Item(
            name="Usage Test Gauze",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            station_supply=True,
        )
        db.add(item)
        db.flush()
    return item


@pytest.fixture
def functional_item(db):
    item = db.query(Item).filter(Item.name == "Usage Test Functional").first()
    if item is None:
        item = Item(
            name="Usage Test Functional",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.FUNCTIONAL,
            unit_of_measure="N/A",
            station_supply=False,
        )
        db.add(item)
        db.flush()
    return item


@pytest.fixture
def stock_lot(db, supply_room, supply_item):
    lot = StockLot(
        item_id=supply_item.item_id,
        location_id=supply_room.location_id,
        quantity=20,
    )
    db.add(lot)
    db.flush()
    return lot


def _payload(station_id, items, vehicle_id=None, location_id=None):
    return {
        "station_id": station_id,
        "vehicle_id": vehicle_id,
        "location_id": location_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


# -- Tests: POST /checks/usage -------------------------------------------------


class TestCreateUsageEvent:
    def test_happy_path_creates_event(
        self,
        client,
        db,
        station,
        supply_room,
        supply_item,
        stock_lot,
        membership,
        auth_responder,
    ):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 3}],
            ),
            headers=auth_responder,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["event_id"] > 0
        assert data["station_id"] == station.station_id
        assert len(data["items"]) == 1
        assert data["items"][0]["item_name"] == supply_item.name
        assert data["items"][0]["quantity_used"] == 3

    def test_does_not_decrement_supply_room(
        self,
        client,
        db,
        station,
        supply_room,
        supply_item,
        stock_lot,
        membership,
        auth_responder,
    ):
        """
        USAGE-B1: Usage logging must NOT touch supply room stock.
        Items were used from the vehicle/jump bag, not the supply room.
        Supply room is only decremented during check wizard reconcile (SR-B4).
        """
        initial_qty = stock_lot.quantity
        client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 5}],
            ),
            headers=auth_responder,
        )
        db.expire(stock_lot)
        assert stock_lot.quantity == initial_qty, (
            f"Supply room stock was decremented by usage logging. "
            f"Expected {initial_qty}, got {stock_lot.quantity}. "
            "Usage logging must only record the event -- SR-B4 decrements supply during reconcile."
        )

    def test_with_vehicle_id(
        self,
        client,
        db,
        station,
        supply_room,
        supply_item,
        stock_lot,
        vehicle,
        membership,
        auth_responder,
    ):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 2}],
                vehicle_id=vehicle.vehicle_id,
            ),
            headers=auth_responder,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["vehicle_id"] == vehicle.vehicle_id
        assert data["vehicle_number"] == vehicle.vehicle_number
        assert data["location_id"] is None

    def test_with_location_id_portable(
        self,
        client,
        db,
        station,
        supply_room,
        supply_item,
        stock_lot,
        portable_location,
        membership,
        auth_responder,
    ):
        """USAGE-B2: Items used from a jump bag log against location_id, not vehicle_id."""
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 1}],
                location_id=portable_location.location_id,
            ),
            headers=auth_responder,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["location_id"] == portable_location.location_id
        assert data["vehicle_id"] is None
        assert data["location_label"] == portable_location.label

    def test_rejects_both_vehicle_and_location(
        self,
        client,
        db,
        station,
        supply_room,
        supply_item,
        stock_lot,
        vehicle,
        portable_location,
        membership,
        auth_responder,
    ):
        """Providing both vehicle_id and location_id should be rejected."""
        res = client.post(
            "/api/v1/checks/usage",
            json={
                "station_id": station.station_id,
                "vehicle_id": vehicle.vehicle_id,
                "location_id": portable_location.location_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "items": [{"item_id": supply_item.item_id, "quantity_used": 1}],
            },
            headers=auth_responder,
        )
        assert res.status_code == 422

    def test_rejects_location_from_wrong_station(
        self,
        client,
        db,
        station,
        supply_item,
        membership,
        auth_responder,
    ):
        """Location belonging to a different station is rejected."""
        other_station = Station(
            name="Other Station", address="2 Other St", region="Test", active=True
        )
        db.add(other_station)
        db.flush()
        other_loc = InventoryLocation(
            location_type=LocationType.JUMP_BAG,
            station_id=other_station.station_id,
            label="Other Jump Bag",
        )
        db.add(other_loc)
        db.flush()

        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 1}],
                location_id=other_loc.location_id,
            ),
            headers=auth_responder,
        )
        assert res.status_code == 422

    def test_unknown_location_gets_404(
        self, client, station, supply_item, membership, auth_responder
    ):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 1}],
                location_id=99999,
            ),
            headers=auth_responder,
        )
        assert res.status_code == 404

    def test_rejects_non_supply_items(
        self, client, station, supply_room, functional_item, membership, auth_responder
    ):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": functional_item.item_id, "quantity_used": 1}],
            ),
            headers=auth_responder,
        )
        assert res.status_code == 422
        assert (
            "Non-supply" in res.json()["detail"]
            or "non-supply" in res.json()["detail"].lower()
        )

    def test_rejects_unknown_item(
        self, client, station, supply_room, membership, auth_responder
    ):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": 99999, "quantity_used": 1}]),
            headers=auth_responder,
        )
        assert res.status_code == 404

    def test_non_member_gets_403(self, client, station, supply_item, stock_lot):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id,
                [{"item_id": supply_item.item_id, "quantity_used": 1}],
            ),
            headers={"Authorization": "Bearer test-responder"},
        )
        assert res.status_code == 403

    def test_unknown_station_gets_404(self, client, auth_admin):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(99999, [{"item_id": 1, "quantity_used": 1}]),
            headers=auth_admin,
        )
        assert res.status_code == 404


# -- Tests: GET /checks/usage/* ------------------------------------------------


class TestUsageHistory:
    def test_returns_history(
        self,
        client,
        db,
        station,
        supply_room,
        supply_item,
        stock_lot,
        membership,
        auth_responder,
    ):
        for _ in range(2):
            client.post(
                "/api/v1/checks/usage",
                json=_payload(
                    station.station_id,
                    [{"item_id": supply_item.item_id, "quantity_used": 1}],
                ),
                headers=auth_responder,
            )
        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}",
            headers=auth_responder,
        )
        assert res.status_code == 200
        events = res.json()
        assert len(events) >= 2
        # Most recent first
        assert events[0]["timestamp"] >= events[1]["timestamp"]

    def test_non_member_gets_403(self, client, station):
        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}",
            headers={"Authorization": "Bearer test-responder"},
        )
        assert res.status_code == 403

    def test_unknown_station_gets_404(self, client, auth_admin):
        res = client.get(
            "/api/v1/checks/usage/station/99999",
            headers=auth_admin,
        )
        assert res.status_code == 404


class TestFrequentItems:
    def test_empty_when_no_history(
        self, client, db, station, supply_room, membership, auth_responder
    ):
        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}/frequent",
            headers=auth_responder,
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_frequent_items_sorted_by_total(
        self, client, db, station, supply_room, membership, auth_responder
    ):
        item_a = Item(
            name="Freq Test Item A",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            station_supply=True,
        )
        item_b = Item(
            name="Freq Test Item B",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            station_supply=True,
        )
        db.add_all([item_a, item_b])
        db.flush()
        # Stock lots no longer needed for usage logging (USAGE-B1: no supply decrement)

        for _ in range(3):
            client.post(
                "/api/v1/checks/usage",
                json=_payload(
                    station.station_id,
                    [{"item_id": item_a.item_id, "quantity_used": 1}],
                ),
                headers=auth_responder,
            )
        client.post(
            "/api/v1/checks/usage",
            json=_payload(
                station.station_id, [{"item_id": item_b.item_id, "quantity_used": 1}]
            ),
            headers=auth_responder,
        )

        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}/frequent",
            headers=auth_responder,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 2
        item_a_entry = next((d for d in data if d["item_id"] == item_a.item_id), None)
        item_b_entry = next((d for d in data if d["item_id"] == item_b.item_id), None)
        assert item_a_entry is not None
        assert item_b_entry is not None
        assert item_a_entry["total_used"] == 3
        assert item_b_entry["total_used"] == 1
        assert data.index(item_a_entry) < data.index(item_b_entry)

    def test_non_member_gets_403(self, client, station):
        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}/frequent",
            headers={"Authorization": "Bearer test-responder"},
        )
        assert res.status_code == 403


# -- Tests: USAGE-B1 last-readings with usage subtraction ----------------------


class TestLastReadingsUsageSubtraction:
    """
    USAGE-B1: get_last_readings must subtract usage events logged after the
    last check so the check wizard pre-fills the post-call on-hand quantity
    and automatically flags items as short.
    """

    def _make_setup(self, db, station):
        """Create vehicle + location + compartment + SUPPLY item + par level."""
        vehicle = Vehicle(
            station_id=station.station_id,
            vehicle_number=f"LR-{id(station)}",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(vehicle)
        db.flush()

        location = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=station.station_id,
            vehicle_id=vehicle.vehicle_id,
            label="Last Readings Test Vehicle",
        )
        db.add(location)
        db.flush()

        comp = Compartment(
            location_id=location.location_id,
            name="Compartment 1",
            sort_order=1,
            active=True,
        )
        db.add(comp)
        db.flush()

        item = Item(
            name=f"LR-Supply-Item-{id(vehicle)}",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            station_supply=True,
        )
        db.add(item)
        db.flush()

        return vehicle, location, comp, item

    def _submit_check(
        self, client, station, vehicle, comp, item, quantity, auth, ts=None
    ):
        if ts is None:
            ts = datetime.now(timezone.utc).isoformat()
        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": datetime.now(timezone.utc).date().isoformat(),
                "timestamp": ts,
                "line_items": [
                    {
                        "compartment_id": comp.compartment_id,
                        "item_id": item.item_id,
                        "quantity_needed": 10,
                        "quantity_found": quantity,
                        "functional_pass": None,
                        "notes": None,
                    }
                ],
            },
            headers=auth,
        )
        assert r.status_code == 201, f"Check submission failed: {r.text}"
        return r

    def _log_usage(self, client, station, vehicle, item, quantity_used, auth, ts=None):
        if ts is None:
            ts = datetime.now(timezone.utc).isoformat()
        r = client.post(
            "/api/v1/checks/usage",
            json={
                "station_id": station.station_id,
                "vehicle_id": vehicle.vehicle_id,
                "timestamp": ts,
                "items": [{"item_id": item.item_id, "quantity_used": quantity_used}],
            },
            headers=auth,
        )
        assert r.status_code == 201, f"Usage log failed: {r.text}"
        return r

    def test_subtracts_post_check_usage(
        self, client, db, station, membership, auth_responder
    ):
        """
        Check recorded 10 present. Responder logs 3 used after the call.
        last-readings must return 7, not 10.
        """
        vehicle, _location, comp, item = self._make_setup(db, station)
        self._submit_check(client, station, vehicle, comp, item, 10, auth_responder)
        self._log_usage(client, station, vehicle, item, 3, auth_responder)

        res = client.get(
            f"/api/v1/checks/daily/last-readings?vehicle_id={vehicle.vehicle_id}",
            headers=auth_responder,
        )
        assert res.status_code == 200
        readings = {r["item_id"]: r for r in res.json()}
        assert readings[item.item_id]["quantity_found"] == 7

    def test_floors_at_zero_not_negative(
        self, client, db, station, membership, auth_responder
    ):
        """
        If usage exceeds quantity_found, result is 0, never negative.
        """
        vehicle, _location, comp, item = self._make_setup(db, station)
        self._submit_check(client, station, vehicle, comp, item, 2, auth_responder)
        self._log_usage(client, station, vehicle, item, 10, auth_responder)

        res = client.get(
            f"/api/v1/checks/daily/last-readings?vehicle_id={vehicle.vehicle_id}",
            headers=auth_responder,
        )
        assert res.status_code == 200
        readings = {r["item_id"]: r for r in res.json()}
        assert readings[item.item_id]["quantity_found"] == 0

    def test_no_usage_returns_original_quantity(
        self, client, db, station, membership, auth_responder
    ):
        """When no usage events exist, last-readings returns the check quantity unchanged."""
        vehicle, _location, comp, item = self._make_setup(db, station)
        self._submit_check(client, station, vehicle, comp, item, 8, auth_responder)

        res = client.get(
            f"/api/v1/checks/daily/last-readings?vehicle_id={vehicle.vehicle_id}",
            headers=auth_responder,
        )
        assert res.status_code == 200
        readings = {r["item_id"]: r for r in res.json()}
        assert readings[item.item_id]["quantity_found"] == 8

    def test_only_subtracts_usage_after_check(
        self, client, db, station, membership, auth_responder
    ):
        """
        Usage logged BEFORE the check timestamp must not affect last-readings.
        Only usage events after the check count.
        """
        vehicle, _location, comp, item = self._make_setup(db, station)

        # Log usage with a timestamp clearly in the past
        past_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self._log_usage(client, station, vehicle, item, 5, auth_responder, ts=past_ts)

        # Submit check AFTER the usage
        check_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self._submit_check(
            client, station, vehicle, comp, item, 10, auth_responder, ts=check_ts
        )

        # last-readings should return 10 -- pre-check usage is irrelevant
        res = client.get(
            f"/api/v1/checks/daily/last-readings?vehicle_id={vehicle.vehicle_id}",
            headers=auth_responder,
        )
        assert res.status_code == 200
        readings = {r["item_id"]: r for r in res.json()}
        assert readings[item.item_id]["quantity_found"] == 10

    def test_functional_item_not_affected_by_usage(
        self, client, db, station, membership, auth_responder
    ):
        """
        FUNCTIONAL items are not consumable -- usage subtraction must not apply.
        quantity_found stays None (functional items use functional_pass, not quantity).
        """
        vehicle, _location, comp, _ = self._make_setup(db, station)

        func_item = Item(
            name=f"LR-Func-Item-{id(vehicle)}",
            category=ItemCategory.EQUIPMENT,
            check_type=ItemCheckType.FUNCTIONAL,
            unit_of_measure="N/A",
            station_supply=False,
        )
        db.add(func_item)
        db.flush()

        # Submit a check with the functional item
        r = client.post(
            "/api/v1/checks/daily",
            json={
                "vehicle_id": vehicle.vehicle_id,
                "station_id": station.station_id,
                "check_date": datetime.now(timezone.utc).date().isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "line_items": [
                    {
                        "compartment_id": comp.compartment_id,
                        "item_id": func_item.item_id,
                        "quantity_needed": 0,
                        "quantity_found": 0,
                        "functional_pass": True,
                        "notes": None,
                    }
                ],
            },
            headers=auth_responder,
        )
        assert r.status_code == 201

        # Manually insert a usage event for the functional item (bypassing validation)
        event = UsageEvent(
            station_id=station.station_id,
            vehicle_id=vehicle.vehicle_id,
            performed_by="test-responder@ems.local",
            timestamp=datetime.now(timezone.utc),
            notes=None,
        )
        db.add(event)
        db.flush()
        db.add(
            UsageEventItem(
                event_id=event.event_id,
                item_id=func_item.item_id,
                quantity_used=1,
            )
        )
        db.flush()

        res = client.get(
            f"/api/v1/checks/daily/last-readings?vehicle_id={vehicle.vehicle_id}",
            headers=auth_responder,
        )
        assert res.status_code == 200
        readings = {r["item_id"]: r for r in res.json()}
        # functional_pass should be True, quantity_found 0 -- not affected by usage
        assert readings[func_item.item_id]["functional_pass"] is True
        assert readings[func_item.item_id]["quantity_found"] == 0
