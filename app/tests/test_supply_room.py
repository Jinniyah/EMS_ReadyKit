"""
tests/test_supply_room.py
Supply Room & Restocking — SUPPLY-B1, SUPPLY-B2, SUPPLY-B3.

Covers:
  - GET /stations/{id}/supply-room
  - GET /inventory/locations/{id}/stock-summary
  - POST /inventory/transfer
  - GET /inventory/locations/{id}/transfers
  - GET /inventory/receive-stock/template
  - POST /inventory/locations/{id}/receive-stock/csv
"""
from __future__ import annotations

import io
from datetime import date, datetime, timedelta, timezone

import pytest

from ems_readykit.models.compartment import Compartment
from ems_readykit.models.inventory_location import InventoryLocation, LocationType
from ems_readykit.models.item import Item, ItemCategory, ItemCheckType
from ems_readykit.models.par_level import ParLevel
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember
from ems_readykit.models.stock_lot import StockLot
from ems_readykit.models.vehicle import Vehicle, VehicleType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def station(db):
    s = Station(name="Test Supply Station", address="123 Test St", region="Test", active=True)
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def supply_room(db, station):
    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station.station_id,
        label="Test Supply Room",
    )
    db.add(loc)
    db.flush()
    for name, descriptor, sort_order in [
        ("Cab 1 - Shelf 1", "Cabinet 1, top shelf", 1),
        ("Cab 1 - Shelf 2", "Cabinet 1, bottom shelf", 2),
    ]:
        db.add(Compartment(location_id=loc.location_id, name=name,
                           location_descriptor=descriptor, sort_order=sort_order, active=True))
    db.flush()
    return loc


@pytest.fixture
def vehicle_location(db, station):
    """
    Get-or-create semantics (same reason as test_item): route handlers that
    call db.commit() release the active savepoint, so SQLite may not fully
    undo the vehicle insert on the outer rollback. Re-using the existing row
    and re-pointing it at the current test's station avoids the UNIQUE
    constraint failure on vehicles.vehicle_number for subsequent tests.
    """
    v = db.query(Vehicle).filter(Vehicle.vehicle_number == "T01").first()
    if v is None:
        v = Vehicle(
            station_id=station.station_id,
            vehicle_number="T01",
            vehicle_type=VehicleType.BLS,
            active=True,
        )
        db.add(v)
        db.flush()
    else:
        v.station_id = station.station_id
        db.flush()

    loc = db.query(InventoryLocation).filter(
        InventoryLocation.vehicle_id == v.vehicle_id,
        InventoryLocation.location_type == LocationType.VEHICLE,
    ).first()
    if loc is None:
        loc = InventoryLocation(
            location_type=LocationType.VEHICLE,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            label="Unit T01",
        )
        db.add(loc)
        db.flush()
    else:
        loc.station_id = station.station_id
        db.flush()
    return loc


@pytest.fixture
def test_item(db):
    """
    Get-or-create semantics: after any test that calls db.commit() inside
    a route handler, SQLite's StaticPool may not fully undo the insert on
    rollback. Using an existing row avoids the UNIQUE constraint error on
    items.name without affecting test correctness — each test gets fresh
    StockLots and Stations via auto-increment PKs regardless.
    """
    item = db.query(Item).filter(Item.name == "Test Gauze Pad").first()
    if item is None:
        item = Item(
            name="Test Gauze Pad",
            category=ItemCategory.CONSUMABLE,
            check_type=ItemCheckType.SUPPLY,
            unit_of_measure="each",
            active=True,
        )
        db.add(item)
        db.flush()
    return item


@pytest.fixture
def supply_lot(db, supply_room, test_item):
    lot = StockLot(
        item_id=test_item.item_id,
        location_id=supply_room.location_id,
        quantity=20,
        lot_number="LOT-TEST-001",
        expiration_date=date.today() + timedelta(days=180),
    )
    db.add(lot)
    db.flush()
    return lot


@pytest.fixture
def membership(db, station):
    """Add admin, supervisor, and responder to the station."""
    for user_id, role in [
        ("test-administrator@ems.local", "Administrator"),
        ("test-supervisor@ems.local",    "Supervisor"),
        ("test-responder@ems.local",     "Responder"),
    ]:
        db.add(StationMember(
            station_id=station.station_id,
            user_id=user_id,
            role=role,
            assigned_by="test",
            active=True,
        ))
    db.flush()


# ---------------------------------------------------------------------------
# SUPPLY-B3: GET /stations/{id}/supply-room
# ---------------------------------------------------------------------------

def test_get_supply_room_ok(client, db, station, supply_room, membership, auth_admin):
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-room", headers=auth_admin)
    assert r.status_code == 200
    data = r.json()
    assert data["location_type"] == "STATION_SUPPLY_ROOM"
    assert data["station_id"] == station.station_id


def test_get_supply_room_404_when_none(client, db, station, membership, auth_admin):
    """Station exists but has no supply room."""
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-room", headers=auth_admin)
    assert r.status_code == 404


def test_get_supply_room_requires_membership(client, db, station, supply_room, auth_supervisor):
    """Supervisor without a membership row gets 403.
    Note: auth_admin bypasses membership checks entirely — use supervisor here."""
    # Intentionally no `membership` fixture so test-supervisor@ems.local has no row
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-room", headers=auth_supervisor)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# SUPPLY-B2: GET /inventory/locations/{id}/stock-summary
# ---------------------------------------------------------------------------

def test_stock_summary_empty(client, db, supply_room, membership, auth_admin):
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    assert r.json() == []


def test_stock_summary_with_lots(client, db, supply_room, supply_lot, membership, auth_admin):
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    item = items[0]
    assert item["total_quantity"] == 20
    assert item["status"] == "NO_PAR"
    assert len(item["lots"]) == 1


def test_stock_summary_status_with_par(client, db, supply_room, supply_lot, test_item, membership, auth_admin):
    db.add(ParLevel(
        item_id=test_item.item_id, location_id=supply_room.location_id,
        min_quantity=25, max_quantity=50,
    ))
    db.flush()
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    item = r.json()[0]
    assert item["status"] == "LOW"
    assert item["par_min"] == 25


def test_stock_summary_status_ok(client, db, supply_room, supply_lot, test_item, membership, auth_admin):
    db.add(ParLevel(
        item_id=test_item.item_id, location_id=supply_room.location_id,
        min_quantity=5, max_quantity=20,
    ))
    db.flush()
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/stock-summary",
                   headers=auth_admin)
    assert r.status_code == 200
    assert r.json()[0]["status"] == "OK"


# ---------------------------------------------------------------------------
# Transfer history (SR-B5: POST /inventory/transfer removed; history retained)
# ---------------------------------------------------------------------------

def test_transfer_history_empty(client, db, station, supply_room, membership, auth_supervisor):
    # No transfers exist for this supply room — endpoint should return empty list
    r = client.get(f"/api/v1/inventory/locations/{supply_room.location_id}/transfers",
                   headers=auth_supervisor)
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# CSV template
# ---------------------------------------------------------------------------

def test_csv_template_download(client, auth_supervisor):
    r = client.get("/api/v1/inventory/receive-stock/template", headers=auth_supervisor)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().splitlines()
    assert lines[0] == "item_name,lot_number,expiration_date,quantity"


# ---------------------------------------------------------------------------
# CSV bulk receive
# ---------------------------------------------------------------------------

def test_csv_receive_valid(client, db, supply_room, test_item, membership, auth_supervisor):
    csv_content = (
        "item_name,lot_number,expiration_date,quantity\n"
        f"{test_item.name},LOT-CSV-001,2027-12-31,15\n"
    )
    r = client.post(
        f"/api/v1/inventory/locations/{supply_room.location_id}/receive-stock/csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rows_imported"] == 1
    assert data["rows_skipped"] == 0
    assert len(data["lots_created"]) == 1
    assert data["lots_created"][0]["quantity"] == 15


def test_csv_receive_unknown_item(client, db, supply_room, membership, auth_supervisor):
    csv_content = (
        "item_name,lot_number,expiration_date,quantity\n"
        "Totally Unknown Item XYZ,,, 5\n"
    )
    r = client.post(
        f"/api/v1/inventory/locations/{supply_room.location_id}/receive-stock/csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rows_imported"] == 0
    assert data["rows_skipped"] == 1
    assert "not found" in data["errors"][0]["error"]


# ---------------------------------------------------------------------------
# SR-B3: GET /stations/{id}/supply-alerts
# ---------------------------------------------------------------------------

@pytest.fixture
def supply_room_par(db, supply_room, test_item):
    """A par level on the supply room for test_item (min=10)."""
    comp = db.query(Compartment).filter(
        Compartment.location_id == supply_room.location_id
    ).first()
    if comp is None:
        comp = Compartment(location_id=supply_room.location_id, name="SR Test Comp",
                           sort_order=1, active=True)
        db.add(comp)
        db.flush()
    db.add(ParLevel(
        item_id=test_item.item_id, location_id=supply_room.location_id,
        compartment_id=comp.compartment_id, min_quantity=10, max_quantity=20,
    ))
    db.flush()


@pytest.fixture
def vehicle_comp(db, vehicle_location, test_item):
    """
    A compartment on the test vehicle with a par level for test_item.
    Get-or-create: vehicle_location persists across tests when route handlers
    call db.commit() (releases savepoint, outer rollback doesn't undo the row).
    """
    comp = db.query(Compartment).filter(
        Compartment.location_id == vehicle_location.location_id,
        Compartment.name        == "SR-B4 Test Comp",
    ).first()
    if comp is None:
        comp = Compartment(location_id=vehicle_location.location_id,
                           name="SR-B4 Test Comp", sort_order=1, active=True)
        db.add(comp)
        db.flush()

    existing_par = db.query(ParLevel).filter(
        ParLevel.item_id        == test_item.item_id,
        ParLevel.compartment_id == comp.compartment_id,
    ).first()
    if existing_par is None:
        db.add(ParLevel(
            item_id=test_item.item_id, location_id=vehicle_location.location_id,
            compartment_id=comp.compartment_id, min_quantity=5, max_quantity=5,
        ))
        db.flush()
    return comp


def test_supply_alerts_low_stock(client, db, station, supply_room, supply_lot, supply_room_par, membership, auth_supervisor):
    # supply_lot has 20 units; par_min is 10 — supply_lot > par → no alerts
    # Reduce lot to 5 to trigger alert
    supply_lot.quantity = 5
    db.flush()
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-alerts", headers=auth_supervisor)
    assert r.status_code == 200
    alerts = r.json()
    assert len(alerts) == 1
    assert alerts[0]["item_name"] == "Test Gauze Pad"
    assert alerts[0]["on_hand"] == 5
    assert alerts[0]["par_min"] == 10


def test_supply_alerts_stock_ok(client, db, station, supply_room, supply_lot, supply_room_par, membership, auth_supervisor):
    # supply_lot has 20 units; par_min is 10 → on_hand >= par_min → no alerts
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-alerts", headers=auth_supervisor)
    assert r.status_code == 200
    assert r.json() == []


def test_supply_alerts_no_supply_room(client, db, station, membership, auth_supervisor):
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-alerts", headers=auth_supervisor)
    assert r.status_code == 200
    assert r.json() == []


def test_supply_alerts_requires_supervisor(client, db, station, supply_room, membership, auth_responder):
    r = client.get(f"/api/v1/stations/{station.station_id}/supply-alerts", headers=auth_responder)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# SR-B4: Auto-decrement supply room on vehicle check submit
# ---------------------------------------------------------------------------

def _utcnow_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_check_auto_decrements_supply_room(client, db, station, supply_room, supply_lot, vehicle_location, vehicle_comp, test_item, membership, auth_supervisor):
    v = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_location.vehicle_id).first()

    # First check: baseline qty_found = 3
    r1 = client.post("/api/v1/checks/daily", json={
        "vehicle_id": v.vehicle_id, "station_id": station.station_id,
        "check_date": "2026-06-01", "timestamp": _utcnow_str(),
        "line_items": [{"compartment_id": vehicle_comp.compartment_id,
                        "item_id": test_item.item_id, "quantity_needed": 5, "quantity_found": 3}],
    }, headers=auth_supervisor)
    assert r1.status_code == 201

    # Second check: topped off to 5 → 2 units should be deducted from supply room (20 → 18)
    r2 = client.post("/api/v1/checks/daily", json={
        "vehicle_id": v.vehicle_id, "station_id": station.station_id,
        "check_date": "2026-06-02", "timestamp": _utcnow_str(),
        "line_items": [{"compartment_id": vehicle_comp.compartment_id,
                        "item_id": test_item.item_id, "quantity_needed": 5, "quantity_found": 5}],
    }, headers=auth_supervisor)
    assert r2.status_code == 201

    db.expire_all()
    total = sum(
        lot.quantity for lot in db.query(StockLot).filter(
            StockLot.location_id == supply_room.location_id,
            StockLot.item_id     == test_item.item_id,
        ).all()
    )
    assert total == 18


def test_check_auto_decrement_best_effort(client, db, station, supply_room, supply_lot, vehicle_location, vehicle_comp, test_item, membership, auth_supervisor):
    """Check still submits even when supply room has less stock than was topped off."""
    v = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_location.vehicle_id).first()

    # First check: baseline = 5
    r1 = client.post("/api/v1/checks/daily", json={
        "vehicle_id": v.vehicle_id, "station_id": station.station_id,
        "check_date": "2026-06-01", "timestamp": _utcnow_str(),
        "line_items": [{"compartment_id": vehicle_comp.compartment_id,
                        "item_id": test_item.item_id, "quantity_needed": 5, "quantity_found": 5}],
    }, headers=auth_supervisor)
    assert r1.status_code == 201

    # Second check: topped off by 100 (supply room only has 20)
    r2 = client.post("/api/v1/checks/daily", json={
        "vehicle_id": v.vehicle_id, "station_id": station.station_id,
        "check_date": "2026-06-02", "timestamp": _utcnow_str(),
        "line_items": [{"compartment_id": vehicle_comp.compartment_id,
                        "item_id": test_item.item_id, "quantity_needed": 5, "quantity_found": 105}],
    }, headers=auth_supervisor)
    assert r2.status_code == 201  # never blocked by insufficient stock

    db.expire_all()
    total = sum(
        lot.quantity for lot in db.query(StockLot).filter(
            StockLot.location_id == supply_room.location_id,
            StockLot.item_id     == test_item.item_id,
        ).all()
    )
    assert total == 0  # depleted to zero, not negative


# ---------------------------------------------------------------------------
# SR-B1: GET /inventory/supply-catalog?station_id=
# ---------------------------------------------------------------------------

def test_supply_catalog_returns_items(client, db, station, supply_room, supply_lot, membership, auth_supervisor):
    r = client.get(f"/api/v1/inventory/supply-catalog?station_id={station.station_id}", headers=auth_supervisor)
    assert r.status_code == 200
    catalog = r.json()
    # Test Gauze Pad is SUPPLY + station_supply defaults True → should appear
    names = [i["item_name"] for i in catalog]
    assert "Test Gauze Pad" in names
    item = next(i for i in catalog if i["item_name"] == "Test Gauze Pad")
    assert item["on_hand"] == 20
    assert item["check_type"] == "SUPPLY"


def test_supply_catalog_excludes_functional_items(client, db, station, supply_room, membership, auth_supervisor, test_item):
    from ems_readykit.models.item import ItemCheckType
    func_item = db.query(test_item.__class__).filter_by(name="Test Gauze Pad").first()
    # Temporarily set to FUNCTIONAL — should be excluded from catalog
    func_item.check_type = ItemCheckType.FUNCTIONAL
    db.flush()
    r = client.get(f"/api/v1/inventory/supply-catalog?station_id={station.station_id}", headers=auth_supervisor)
    assert r.status_code == 200
    names = [i["item_name"] for i in r.json()]
    assert "Test Gauze Pad" not in names


def test_supply_catalog_excludes_non_station_supply_items(client, db, station, supply_room, supply_lot, membership, auth_supervisor, test_item):
    test_item.station_supply = False
    db.flush()
    r = client.get(f"/api/v1/inventory/supply-catalog?station_id={station.station_id}", headers=auth_supervisor)
    assert r.status_code == 200
    names = [i["item_name"] for i in r.json()]
    assert "Test Gauze Pad" not in names


def test_supply_catalog_no_supply_room(client, db, station, membership, auth_supervisor):
    # Station exists but has no supply room — should return empty list
    r = client.get(f"/api/v1/inventory/supply-catalog?station_id={station.station_id}", headers=auth_supervisor)
    assert r.status_code == 200
    assert r.json() == []


def test_supply_catalog_requires_membership(client, db, station, supply_room, auth_supervisor):
    # No membership fixture — supervisor has no station access
    r = client.get(f"/api/v1/inventory/supply-catalog?station_id={station.station_id}", headers=auth_supervisor)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# SR-B2: PATCH /inventory/supply-catalog/items/{id}/count
# ---------------------------------------------------------------------------

def test_patch_count_decrease(client, db, station, supply_room, supply_lot, membership, auth_supervisor, test_item):
    # Supply lot starts at 20 — correct to 15
    r = client.patch(
        f"/api/v1/inventory/supply-catalog/items/{test_item.item_id}/count",
        json={"location_id": supply_room.location_id, "quantity": 15, "comment": "Physical count"},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["on_hand"] == 15


def test_patch_count_increase(client, db, station, supply_room, supply_lot, membership, auth_supervisor, test_item):
    # Supply lot starts at 20 — found 5 more during count → 25
    r = client.patch(
        f"/api/v1/inventory/supply-catalog/items/{test_item.item_id}/count",
        json={"location_id": supply_room.location_id, "quantity": 25},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    assert r.json()["on_hand"] == 25


def test_patch_count_same(client, db, station, supply_room, supply_lot, membership, auth_supervisor, test_item):
    r = client.patch(
        f"/api/v1/inventory/supply-catalog/items/{test_item.item_id}/count",
        json={"location_id": supply_room.location_id, "quantity": 20},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    assert r.json()["on_hand"] == 20


def test_patch_count_wrong_location_type(client, db, station, vehicle_location, supply_lot, membership, auth_supervisor, test_item):
    r = client.patch(
        f"/api/v1/inventory/supply-catalog/items/{test_item.item_id}/count",
        json={"location_id": vehicle_location.location_id, "quantity": 5},
        headers=auth_supervisor,
    )
    assert r.status_code == 422


def test_patch_count_requires_supervisor(client, db, station, supply_room, supply_lot, membership, auth_responder, test_item):
    r = client.patch(
        f"/api/v1/inventory/supply-catalog/items/{test_item.item_id}/count",
        json={"location_id": supply_room.location_id, "quantity": 10},
        headers=auth_responder,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# B-E8: PUT /inventory/lots/{lot_id} — correct expiry date / lot number
# ---------------------------------------------------------------------------

def test_update_lot_expiry(client, db, supply_lot, membership, auth_supervisor):
    new_expiry = str(date.today() + timedelta(days=365))
    r = client.put(
        f"/api/v1/inventory/lots/{supply_lot.lot_id}",
        json={"expiration_date": new_expiry},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["expiration_date"] == new_expiry
    assert data["lot_number"] == supply_lot.lot_number


def test_update_lot_number(client, db, supply_lot, membership, auth_supervisor):
    r = client.put(
        f"/api/v1/inventory/lots/{supply_lot.lot_id}",
        json={"lot_number": "LOT-CORRECTED-999"},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["lot_number"] == "LOT-CORRECTED-999"
    # expiry unchanged
    assert data["expiration_date"] == str(supply_lot.expiration_date)


def test_update_lot_clear_expiry(client, db, supply_lot, membership, auth_supervisor):
    r = client.put(
        f"/api/v1/inventory/lots/{supply_lot.lot_id}",
        json={"expiration_date": None},
        headers=auth_supervisor,
    )
    assert r.status_code == 200
    assert r.json()["expiration_date"] is None


def test_update_lot_404(client, db, membership, auth_supervisor):
    r = client.put(
        "/api/v1/inventory/lots/99999",
        json={"expiration_date": str(date.today() + timedelta(days=30))},
        headers=auth_supervisor,
    )
    assert r.status_code == 404


def test_update_lot_requires_supervisor(client, db, supply_lot, membership, auth_responder):
    r = client.put(
        f"/api/v1/inventory/lots/{supply_lot.lot_id}",
        json={"expiration_date": str(date.today() + timedelta(days=30))},
        headers=auth_responder,
    )
    assert r.status_code == 403


def test_update_lot_requires_membership(client, db, supply_lot, auth_supervisor):
    # No membership fixture — supervisor has no station access
    r = client.put(
        f"/api/v1/inventory/lots/{supply_lot.lot_id}",
        json={"expiration_date": str(date.today() + timedelta(days=30))},
        headers=auth_supervisor,
    )
    assert r.status_code == 403
