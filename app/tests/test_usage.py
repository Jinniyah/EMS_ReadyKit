"""
tests/test_usage.py
After-Call Reset — POST /checks/usage and GET /checks/usage/* endpoints.

Covers:
  - POST /checks/usage happy path (creates event, decrements supply room FIFO)
  - POST /checks/usage rejects non-SUPPLY items
  - POST /checks/usage rejects unknown item_ids
  - POST /checks/usage non-member gets 403
  - GET /checks/usage/station/{id} returns history
  - GET /checks/usage/station/{id}/frequent returns aggregated data
  - GET /checks/usage/station/{id}/frequent returns empty list with no data
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.vehicle import Vehicle, VehicleType

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def station(db):
    s = Station(name="Usage Test Station", address="1 Main St", region="Test", active=True)
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def membership(db, station, auth_responder):
    # auth_responder token maps to test-responder@ems.local
    m = StationMember(station_id=station.station_id, user_id="test-responder@ems.local",
                      role="RESPONDER", assigned_by="test-setup", active=True)
    db.add(m)
    db.flush()
    return m


@pytest.fixture
def vehicle(db, station):
    v = db.query(Vehicle).filter(Vehicle.vehicle_number == "U-USAGE").first()
    if v is None:
        v = Vehicle(station_id=station.station_id, vehicle_number="U-USAGE",
                    vehicle_type=VehicleType.BLS, active=True)
        db.add(v)
        db.flush()
    else:
        v.station_id = station.station_id
        db.flush()
    return v


@pytest.fixture
def supply_room(db, station):
    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Usage Test Supply Room",
    )
    db.add(loc)
    db.flush()
    db.add(Compartment(location_id=loc.location_id, name="Shelf 1",
                       location_descriptor="Shelf 1", sort_order=1, active=True))
    db.flush()
    return loc


@pytest.fixture
def supply_item(db):
    item = db.query(Item).filter(Item.name == "Usage Test Gauze").first()
    if item is None:
        item = Item(name="Usage Test Gauze", category=ItemCategory.CONSUMABLE,
                    check_type=ItemCheckType.SUPPLY, unit_of_measure="each",
                    station_supply=True)
        db.add(item)
        db.flush()
    return item


@pytest.fixture
def functional_item(db):
    item = db.query(Item).filter(Item.name == "Usage Test Functional").first()
    if item is None:
        item = Item(name="Usage Test Functional", category=ItemCategory.EQUIPMENT,
                    check_type=ItemCheckType.FUNCTIONAL, unit_of_measure="N/A",
                    station_supply=False)
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


def _payload(station_id, items, vehicle_id=None):
    return {
        "station_id": station_id,
        "vehicle_id": vehicle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCreateUsageEvent:
    def test_happy_path_creates_event(self, client, db, station, supply_room,
                                      supply_item, stock_lot, membership, auth_responder):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": supply_item.item_id, "quantity_used": 3}]),
            headers=auth_responder,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["event_id"] > 0
        assert data["station_id"] == station.station_id
        assert len(data["items"]) == 1
        assert data["items"][0]["item_name"] == supply_item.name
        assert data["items"][0]["quantity_used"] == 3

    def test_decrements_supply_room_fifo(self, client, db, station, supply_room,
                                          supply_item, stock_lot, membership, auth_responder):
        initial_qty = stock_lot.quantity
        client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": supply_item.item_id, "quantity_used": 5}]),
            headers=auth_responder,
        )
        db.expire(stock_lot)
        assert stock_lot.quantity == initial_qty - 5

    def test_depletes_to_zero_not_negative(self, client, db, station, supply_room,
                                            supply_item, stock_lot, membership, auth_responder):
        # Request more than available
        client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": supply_item.item_id, "quantity_used": 999}]),
            headers=auth_responder,
        )
        db.expire(stock_lot)
        assert stock_lot.quantity == 0

    def test_rejects_non_supply_items(self, client, station, supply_room, functional_item,
                                      membership, auth_responder):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": functional_item.item_id, "quantity_used": 1}]),
            headers=auth_responder,
        )
        assert res.status_code == 422
        assert "Non-supply" in res.json()["detail"] or "non-supply" in res.json()["detail"].lower()

    def test_rejects_unknown_item(self, client, station, supply_room, membership, auth_responder):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": 99999, "quantity_used": 1}]),
            headers=auth_responder,
        )
        assert res.status_code == 404

    def test_non_member_gets_403(self, client, station, supply_item, stock_lot):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id, [{"item_id": supply_item.item_id, "quantity_used": 1}]),
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

    def test_with_vehicle_id(self, client, db, station, supply_room, supply_item,
                              stock_lot, vehicle, membership, auth_responder):
        res = client.post(
            "/api/v1/checks/usage",
            json=_payload(station.station_id,
                          [{"item_id": supply_item.item_id, "quantity_used": 2}],
                          vehicle_id=vehicle.vehicle_id),
            headers=auth_responder,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["vehicle_id"] == vehicle.vehicle_id
        assert data["vehicle_number"] == vehicle.vehicle_number


class TestUsageHistory:
    def test_returns_history(self, client, db, station, supply_room, supply_item,
                              stock_lot, membership, auth_responder):
        # Create two events
        for _ in range(2):
            client.post(
                "/api/v1/checks/usage",
                json=_payload(station.station_id, [{"item_id": supply_item.item_id, "quantity_used": 1}]),
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
    def test_empty_when_no_history(self, client, db, station, supply_room, membership, auth_responder):
        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}/frequent",
            headers=auth_responder,
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_frequent_items_sorted_by_total(self, client, db, station, supply_room,
                                                      membership, auth_responder):
        # Create two different supply items
        item_a = Item(name="Freq Test Item A", category=ItemCategory.CONSUMABLE,
                      check_type=ItemCheckType.SUPPLY, unit_of_measure="each", station_supply=True)
        item_b = Item(name="Freq Test Item B", category=ItemCategory.CONSUMABLE,
                      check_type=ItemCheckType.SUPPLY, unit_of_measure="each", station_supply=True)
        db.add_all([item_a, item_b])
        db.flush()
        # Add stock so decrement doesn't fail
        for item in [item_a, item_b]:
            db.add(StockLot(item_id=item.item_id, location_id=supply_room.location_id, quantity=50))
        db.flush()

        # Log item_a 3 times (total 3), item_b 1 time (total 1)
        for _ in range(3):
            client.post("/api/v1/checks/usage",
                        json=_payload(station.station_id, [{"item_id": item_a.item_id, "quantity_used": 1}]),
                        headers=auth_responder)
        client.post("/api/v1/checks/usage",
                    json=_payload(station.station_id, [{"item_id": item_b.item_id, "quantity_used": 1}]),
                    headers=auth_responder)

        res = client.get(
            f"/api/v1/checks/usage/station/{station.station_id}/frequent",
            headers=auth_responder,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 2
        # item_a should rank first
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
