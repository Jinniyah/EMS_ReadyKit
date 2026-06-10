"""
tests/test_routers.py
Phase 2 + Phase 3 (auth) + Phase 4 (compartments, line items) + Phase 4B (check types) router and schema tests.

All client calls include auth headers. Most tests use auth_admin for
simplicity. RBAC-specific tests use the appropriate role fixture.

performed_by / primary_signer are now set from the JWT identity in the router,
so the request body values are ignored — tests no longer need to assert on
the specific name submitted.

Phase 5 change:
  test_create_daily_check_duplicate_returns_409 replaced with
  test_multiple_checks_same_vehicle_same_day_all_succeed — multiple checks
  per vehicle per day are now explicitly allowed and tested.
  test_station_compliance_today updated to assert 2 checks are returned
  when 2 are submitted.

Session C change:
  Station membership is now enforced. Any test that uses a non-admin role
  to access station-scoped data must first add a StationMember row.
  Use _add_member(db, station_id, email, role) for this.
"""

from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ems_readykit.models import (
    AuditEvent,
    InventoryLocation,
    Item,
    ItemCategory,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)
from ems_readykit.models.station_member import StationMember

# ── Unique name helpers ────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Test data helpers ─────────────────────────────────────────────────────────

def _station(db: Session, *, name: Optional[str] = None) -> Station:
    s = Station(name=name or f"Station-{_uid()}", address="100 Main St", region="Downriver")
    db.add(s)
    db.flush()
    return s


def _vehicle(db: Session, station_id: int, *, number: Optional[str] = None, vtype: VehicleType = VehicleType.ALS) -> Vehicle:
    number = number or f"AMB-{_uid()}"
    v = Vehicle(station_id=station_id, vehicle_number=number, vehicle_type=vtype)
    db.add(v)
    db.flush()
    loc = InventoryLocation(
        location_type=LocationType.VEHICLE, station_id=station_id,
        vehicle_id=v.vehicle_id, label=f"{number} — {vtype.value}",
    )
    db.add(loc)
    db.flush()
    return v


def _item(db: Session, *, name: Optional[str] = None, controlled: bool = False) -> Item:
    item = Item(
        name=name or f"Item-{_uid()}", category=ItemCategory.MEDICATION,
        controlled_substance=controlled, unit_of_measure="mL",
    )
    db.add(item)
    db.flush()
    return item


def _supply_room(db: Session, station_id: int) -> InventoryLocation:
    loc = InventoryLocation(
        location_type=LocationType.STATION_SUPPLY_ROOM,
        station_id=station_id, label=f"Supply Room {_uid()}",
    )
    db.add(loc)
    db.flush()
    return loc


def _add_member(db: Session, station_id: int, user_email: str, role: str) -> None:
    """
    Add a StationMember row for a test user.
    Required when a non-admin auth fixture accesses a station-scoped endpoint
    after Session C membership enforcement was added (ACC-B7/B8).
    """
    db.add(StationMember(
        station_id=station_id,
        user_id=user_email,
        role=role,
        assigned_by="test-administrator@ems.local",
        active=True,
    ))
    db.flush()


# ── Station endpoints ─────────────────────────────────────────────────────────

class TestStationEndpoints:

    def test_create_station_returns_201(self, client, auth_admin):
        response = client.post("/api/v1/stations", json={
            "name": f"Station-{_uid()}", "address": "100 Fire Station Dr", "region": "Downriver",
        }, headers=auth_admin)
        assert response.status_code == 201
        body = response.json()
        assert body["station_id"] is not None
        assert body["active"] is True

    def test_create_station_blank_name_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/stations", json={
            "name": "   ", "address": "100 Main St", "region": "Downriver",
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_list_stations_returns_active_by_default(self, client, auth_admin):
        name_a = f"Active-{_uid()}"
        name_i = f"Inactive-{_uid()}"
        client.post("/api/v1/stations", json={"name": name_a, "address": "1 St", "region": "R"}, headers=auth_admin)
        client.post("/api/v1/stations", json={"name": name_i, "address": "2 St", "region": "R", "active": False}, headers=auth_admin)
        response = client.get("/api/v1/stations", headers=auth_admin)
        assert response.status_code == 200
        names = [s["name"] for s in response.json()]
        assert name_a in names
        assert name_i not in names

    def test_list_stations_inactive_filter(self, client, auth_admin):
        name_i = f"Inactive-{_uid()}"
        client.post("/api/v1/stations", json={"name": name_i, "address": "2 St", "region": "R", "active": False}, headers=auth_admin)
        response = client.get("/api/v1/stations?active=false", headers=auth_admin)
        assert response.status_code == 200
        names = [s["name"] for s in response.json()]
        assert name_i in names

    def test_get_station_by_id(self, client, auth_admin):
        r = client.post("/api/v1/stations", json={"name": f"Station-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        station_id = r.json()["station_id"]
        response = client.get(f"/api/v1/stations/{station_id}", headers=auth_admin)
        assert response.status_code == 200
        assert response.json()["station_id"] == station_id

    def test_get_station_not_found_returns_404(self, client, auth_admin):
        response = client.get("/api/v1/stations/99999999", headers=auth_admin)
        assert response.status_code == 404


# ── Vehicle endpoints ─────────────────────────────────────────────────────────

class TestVehicleEndpoints:

    def test_create_vehicle_returns_201(self, client, auth_admin):
        r = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = r.json()["station_id"]
        response = client.post("/api/v1/vehicles", json={
            "station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS",
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["requires_controlled_substance_check"] is True

    def test_create_vehicle_auto_creates_location(self, client, db, auth_admin):
        r = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = r.json()["station_id"]
        vnum = f"AMB-{_uid()}"
        response = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": vnum, "vehicle_type": "BLS"}, headers=auth_admin)
        assert response.status_code == 201
        vehicle_id = response.json()["vehicle_id"]
        loc = db.query(InventoryLocation).filter(InventoryLocation.vehicle_id == vehicle_id).first()
        assert loc is not None
        assert loc.location_type == LocationType.VEHICLE

    def test_create_vehicle_invalid_station_returns_404(self, client, auth_admin):
        response = client.post("/api/v1/vehicles", json={"station_id": 99999999, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        assert response.status_code == 404

    def test_create_vehicle_duplicate_number_returns_409(self, client, auth_admin):
        r = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = r.json()["station_id"]
        vnum = f"AMB-{_uid()}"
        client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": vnum, "vehicle_type": "ALS"}, headers=auth_admin)
        response = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": vnum, "vehicle_type": "ALS"}, headers=auth_admin)
        assert response.status_code == 409

    def test_qrv_vehicle_cs_check_false(self, client, auth_admin):
        r = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = r.json()["station_id"]
        response = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"ENG-{_uid()}", "vehicle_type": "QRV"}, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["requires_controlled_substance_check"] is False

    def test_get_vehicle_not_found_returns_404(self, client, auth_admin):
        response = client.get("/api/v1/vehicles/99999999", headers=auth_admin)
        assert response.status_code == 404

    def test_list_station_vehicles(self, client, auth_admin):
        r1 = client.post("/api/v1/stations", json={"name": f"S1-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        r2 = client.post("/api/v1/stations", json={"name": f"S2-{_uid()}", "address": "2 St", "region": "R"}, headers=auth_admin)
        s1_id, s2_id = r1.json()["station_id"], r2.json()["station_id"]
        vnum1, vnum2 = f"AMB-{_uid()}", f"AMB-{_uid()}"
        client.post("/api/v1/vehicles", json={"station_id": s1_id, "vehicle_number": vnum1, "vehicle_type": "ALS"}, headers=auth_admin)
        client.post("/api/v1/vehicles", json={"station_id": s2_id, "vehicle_number": vnum2, "vehicle_type": "ALS"}, headers=auth_admin)
        response = client.get(f"/api/v1/stations/{s1_id}/vehicles", headers=auth_admin)
        assert response.status_code == 200
        numbers = [v["vehicle_number"] for v in response.json()]
        assert vnum1 in numbers
        assert vnum2 not in numbers

    def test_list_station_vehicles_invalid_station_returns_404(self, client, auth_admin):
        response = client.get("/api/v1/stations/99999999/vehicles", headers=auth_admin)
        assert response.status_code == 404


# ── Item endpoints ────────────────────────────────────────────────────────────

class TestItemEndpoints:

    def test_create_item_returns_201(self, client, auth_admin):
        response = client.post("/api/v1/items", json={
            "name": f"Epi-{_uid()}", "category": "Medication", "controlled_substance": True, "unit_of_measure": "mL",
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["controlled_substance"] is True

    def test_create_item_duplicate_name_returns_409(self, client, auth_admin):
        name = f"Gauze-{_uid()}"
        client.post("/api/v1/items", json={"name": name, "category": "Consumable", "unit_of_measure": "each"}, headers=auth_admin)
        response = client.post("/api/v1/items", json={"name": name, "category": "Consumable", "unit_of_measure": "each"}, headers=auth_admin)
        assert response.status_code == 409

    def test_list_items_filter_by_category(self, client, auth_admin):
        med_name, equip_name = f"Med-{_uid()}", f"Equip-{_uid()}"
        client.post("/api/v1/items", json={"name": med_name, "category": "Medication", "unit_of_measure": "mL"}, headers=auth_admin)
        client.post("/api/v1/items", json={"name": equip_name, "category": "Equipment", "unit_of_measure": "each"}, headers=auth_admin)
        response = client.get("/api/v1/items?category=Medication", headers=auth_admin)
        assert response.status_code == 200
        names = [i["name"] for i in response.json()]
        assert med_name in names
        assert equip_name not in names

    def test_list_items_filter_controlled(self, client, auth_admin):
        cs_name, non_cs_name = f"CS-{_uid()}", f"NonCS-{_uid()}"
        client.post("/api/v1/items", json={"name": cs_name, "category": "Medication", "controlled_substance": True, "unit_of_measure": "mg"}, headers=auth_admin)
        client.post("/api/v1/items", json={"name": non_cs_name, "category": "Medication", "controlled_substance": False, "unit_of_measure": "mg"}, headers=auth_admin)
        response = client.get("/api/v1/items?controlled_substance=true", headers=auth_admin)
        assert response.status_code == 200
        assert all(i["controlled_substance"] is True for i in response.json())

    def test_get_item_not_found_returns_404(self, client, auth_admin):
        response = client.get("/api/v1/items/99999999", headers=auth_admin)
        assert response.status_code == 404

    def test_create_item_blank_name_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/items", json={"name": "  ", "category": "Medication", "unit_of_measure": "mL"}, headers=auth_admin)
        assert response.status_code == 422


# ── Inventory endpoints ───────────────────────────────────────────────────────

class TestInventoryEndpoints:

    def test_list_locations(self, client, auth_admin):
        response = client.get("/api/v1/inventory/locations", headers=auth_admin)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_location_not_found_returns_404(self, client, auth_admin):
        response = client.get("/api/v1/inventory/locations/99999999", headers=auth_admin)
        assert response.status_code == 404

    def _setup_loc_and_item(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        loc_id = next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid)
        ir = client.post("/api/v1/items", json={"name": f"Item-{_uid()}", "category": "Medication", "unit_of_measure": "mL"}, headers=auth_admin)
        return loc_id, ir.json()["item_id"]

    def test_create_stock_lot_returns_201(self, client, auth_admin):
        loc_id, item_id = self._setup_loc_and_item(client, auth_admin)
        response = client.post("/api/v1/inventory/lots", json={
            "item_id": item_id, "location_id": loc_id, "quantity": 10,
            "lot_number": f"LOT-{_uid()}", "expiration_date": "2027-06-30",
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["quantity"] == 10

    def test_create_stock_lot_negative_quantity_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/inventory/lots", json={"item_id": 1, "location_id": 1, "quantity": -5}, headers=auth_admin)
        assert response.status_code == 422

    def test_create_stock_lot_invalid_location_returns_404(self, client, auth_admin):
        ir = client.post("/api/v1/items", json={"name": f"Item-{_uid()}", "category": "Medication", "unit_of_measure": "mL"}, headers=auth_admin)
        response = client.post("/api/v1/inventory/lots", json={"item_id": ir.json()["item_id"], "location_id": 99999999, "quantity": 5}, headers=auth_admin)
        assert response.status_code == 404

    def test_list_expiring_lots(self, client, auth_admin):
        loc_id, item_id = self._setup_loc_and_item(client, auth_admin)
        soon = (date.today() + timedelta(days=15)).isoformat()
        far = (date.today() + timedelta(days=365)).isoformat()
        client.post("/api/v1/inventory/lots", json={"item_id": item_id, "location_id": loc_id, "quantity": 2, "expiration_date": soon}, headers=auth_admin)
        client.post("/api/v1/inventory/lots", json={"item_id": item_id, "location_id": loc_id, "quantity": 2, "expiration_date": far}, headers=auth_admin)
        response = client.get("/api/v1/inventory/expiring?days=30", headers=auth_admin)
        assert response.status_code == 200
        assert all(
            date.fromisoformat(lot["expiration_date"]) <= date.today() + timedelta(days=30)
            for lot in response.json() if lot["expiration_date"]
        )

    def test_list_location_stock(self, client, auth_admin):
        loc_id, item_id = self._setup_loc_and_item(client, auth_admin)
        client.post("/api/v1/inventory/lots", json={"item_id": item_id, "location_id": loc_id, "quantity": 5}, headers=auth_admin)
        response = client.get(f"/api/v1/inventory/locations/{loc_id}/stock", headers=auth_admin)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_create_par_level_returns_201(self, client, auth_admin):
        loc_id, item_id = self._setup_loc_and_item(client, auth_admin)
        response = client.post("/api/v1/inventory/par-levels", json={
            "item_id": item_id, "location_id": loc_id, "min_quantity": 5, "max_quantity": 20,
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["min_quantity"] == 5

    def test_create_par_level_max_less_than_min_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/inventory/par-levels", json={"item_id": 1, "location_id": 1, "min_quantity": 10, "max_quantity": 5}, headers=auth_admin)
        assert response.status_code == 422

    def test_create_par_level_duplicate_returns_409(self, client, auth_admin):
        loc_id, item_id = self._setup_loc_and_item(client, auth_admin)
        client.post("/api/v1/inventory/par-levels", json={"item_id": item_id, "location_id": loc_id, "min_quantity": 5, "max_quantity": 20}, headers=auth_admin)
        response = client.post("/api/v1/inventory/par-levels", json={"item_id": item_id, "location_id": loc_id, "min_quantity": 3, "max_quantity": 15}, headers=auth_admin)
        assert response.status_code == 409
        assert "par_id" in response.json()["detail"]

    def test_list_location_par_levels(self, client, auth_admin):
        loc_id, item_id = self._setup_loc_and_item(client, auth_admin)
        client.post("/api/v1/inventory/par-levels", json={"item_id": item_id, "location_id": loc_id, "min_quantity": 5, "max_quantity": 20}, headers=auth_admin)
        response = client.get(f"/api/v1/inventory/locations/{loc_id}/par-levels", headers=auth_admin)
        assert response.status_code == 200
        assert len(response.json()) >= 1


# ── Compartment endpoints ─────────────────────────────────────────────────────

class TestCompartmentEndpoints:

    def _make_location(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        return next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid), sid

    def test_create_compartment_returns_201(self, client, auth_admin):
        loc_id, _ = self._make_location(client, auth_admin)
        response = client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={
            "location_id": loc_id, "name": "Compartment #1", "sort_order": 1, "als_only": False,
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["name"] == "Compartment #1"
        assert response.json()["compartment_id"] is not None

    def test_create_duplicate_compartment_returns_409(self, client, auth_admin):
        loc_id, _ = self._make_location(client, auth_admin)
        payload = {"location_id": loc_id, "name": "Drug Bag", "als_only": True}
        client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json=payload, headers=auth_admin)
        response = client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json=payload, headers=auth_admin)
        assert response.status_code == 409

    def test_list_compartments_sorted_by_sort_order(self, client, auth_admin):
        loc_id, _ = self._make_location(client, auth_admin)
        for name, order in [("Compartment #3", 3), ("Compartment #1", 1), ("Compartment #2", 2)]:
            client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={"location_id": loc_id, "name": name, "sort_order": order}, headers=auth_admin)
        response = client.get(f"/api/v1/inventory/locations/{loc_id}/compartments", headers=auth_admin)
        assert response.status_code == 200
        names = [c["name"] for c in response.json()]
        assert names == ["Compartment #1", "Compartment #2", "Compartment #3"]

    def test_get_compartment_by_id(self, client, auth_admin):
        loc_id, _ = self._make_location(client, auth_admin)
        cr = client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={"location_id": loc_id, "name": "First Out Bag", "sort_order": 0}, headers=auth_admin)
        cid = cr.json()["compartment_id"]
        response = client.get(f"/api/v1/inventory/compartments/{cid}", headers=auth_admin)
        assert response.status_code == 200
        assert response.json()["name"] == "First Out Bag"

    def test_get_compartment_not_found_returns_404(self, client, auth_admin):
        response = client.get("/api/v1/inventory/compartments/99999999", headers=auth_admin)
        assert response.status_code == 404

    def test_responder_can_list_compartments(self, client, db, auth_admin, auth_responder):
        """Session C: responder must be a station member to list compartments."""
        loc_id, sid = self._make_location(client, auth_admin)
        _add_member(db, sid, "test-responder@ems.local", "Responder")
        client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={"location_id": loc_id, "name": "Compartment #1"}, headers=auth_admin)
        response = client.get(f"/api/v1/inventory/locations/{loc_id}/compartments", headers=auth_responder)
        assert response.status_code == 200

    def test_responder_cannot_create_compartment_returns_403(self, client, db, auth_admin, auth_responder):
        """Role 403 — Responder lacks Supervisor role regardless of membership."""
        loc_id, sid = self._make_location(client, auth_admin)
        _add_member(db, sid, "test-responder@ems.local", "Responder")
        response = client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={"location_id": loc_id, "name": "Compartment #1"}, headers=auth_responder)
        assert response.status_code == 403


# ── Check line item tests ─────────────────────────────────────────────────────

class TestCheckLineItems:

    def _setup(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        loc_id = next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid)
        cr = client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={"location_id": loc_id, "name": "Compartment #1", "sort_order": 1}, headers=auth_admin)
        cid = cr.json()["compartment_id"]
        ir = client.post("/api/v1/items", json={"name": f"Item-{_uid()}", "category": "Consumable", "unit_of_measure": "each"}, headers=auth_admin)
        item_id = ir.json()["item_id"]
        return sid, vid, cid, item_id

    def test_daily_check_with_line_items_returns_201(self, client, auth_admin):
        sid, vid, cid, item_id = self._setup(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-01", "timestamp": _utcnow(),
            "line_items": [{"compartment_id": cid, "item_id": item_id, "quantity_needed": 4, "quantity_found": 4}],
        }, headers=auth_admin)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "PASS"
        assert len(body["line_items"]) == 1
        assert body["line_items"][0]["status"] == "OK"

    def test_short_item_sets_status_needs_restock(self, client, auth_admin):
        sid, vid, cid, item_id = self._setup(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-02", "timestamp": _utcnow(),
            "line_items": [{"compartment_id": cid, "item_id": item_id, "quantity_needed": 4, "quantity_found": 2}],
        }, headers=auth_admin)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "NEEDS_RESTOCK"
        assert body["line_items"][0]["status"] == "SHORT"

    def test_missing_item_sets_status_fail(self, client, auth_admin):
        sid, vid, cid, item_id = self._setup(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-03", "timestamp": _utcnow(),
            "line_items": [{"compartment_id": cid, "item_id": item_id, "quantity_needed": 4, "quantity_found": 0}],
        }, headers=auth_admin)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "FAIL"
        assert body["line_items"][0]["status"] == "MISSING"

    def test_check_without_line_items_defaults_to_pass(self, client, auth_admin):
        sid, vid, _cid, _item_id = self._setup(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-04", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["status"] == "PASS"
        assert response.json()["line_items"] == []

    def test_invalid_compartment_id_returns_404(self, client, auth_admin):
        sid, vid, _cid, item_id = self._setup(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-05", "timestamp": _utcnow(),
            "line_items": [{"compartment_id": 99999999, "item_id": item_id, "quantity_needed": 4, "quantity_found": 4}],
        }, headers=auth_admin)
        assert response.status_code == 404

    def test_expired_lot_sets_status_expired(self, client, auth_admin):
        sid, vid, cid, item_id = self._setup(client, auth_admin)
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        loc_id = next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid)
        lot_r = client.post("/api/v1/inventory/lots", json={
            "item_id": item_id, "location_id": loc_id,
            "quantity": 2, "lot_number": "EXP-LOT",
            "expiration_date": "2020-01-01",
        }, headers=auth_admin)
        lot_id = lot_r.json()["lot_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-07", "timestamp": _utcnow(),
            "line_items": [
                {"compartment_id": cid, "item_id": item_id,
                 "lot_id": lot_id, "quantity_needed": 2, "quantity_found": 2},
            ],
        }, headers=auth_admin)
        assert response.status_code == 201
        body = response.json()
        assert body["line_items"][0]["status"] == "EXPIRED"
        assert body["status"] == "FAIL"
        assert body["line_items"][0]["expiration_date"] == "2020-01-01"
        assert body["line_items"][0]["lot_number"] == "EXP-LOT"

    def test_valid_lot_passes_expiration_check(self, client, auth_admin):
        sid, vid, cid, item_id = self._setup(client, auth_admin)
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        loc_id = next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid)
        lot_r = client.post("/api/v1/inventory/lots", json={
            "item_id": item_id, "location_id": loc_id,
            "quantity": 2, "lot_number": "GOOD-LOT",
            "expiration_date": "2029-01-01",
        }, headers=auth_admin)
        lot_id = lot_r.json()["lot_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-08", "timestamp": _utcnow(),
            "line_items": [
                {"compartment_id": cid, "item_id": item_id,
                 "lot_id": lot_id, "quantity_needed": 2, "quantity_found": 2},
            ],
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["status"] == "PASS"
        assert response.json()["line_items"][0]["status"] == "OK"
        assert response.json()["line_items"][0]["expiration_date"] == "2029-01-01"

    def test_wrong_lot_item_returns_422(self, client, auth_admin):
        sid, vid, cid, item_id = self._setup(client, auth_admin)
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        loc_id = next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid)
        ir2 = client.post("/api/v1/items", json={"name": f"OtherItem-{_uid()}", "category": "Consumable", "unit_of_measure": "each"}, headers=auth_admin)
        item2_id = ir2.json()["item_id"]
        lot_r = client.post("/api/v1/inventory/lots", json={
            "item_id": item2_id, "location_id": loc_id, "quantity": 2,
        }, headers=auth_admin)
        lot_id = lot_r.json()["lot_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-09", "timestamp": _utcnow(),
            "line_items": [
                {"compartment_id": cid, "item_id": item_id,
                 "lot_id": lot_id, "quantity_needed": 2, "quantity_found": 2},
            ],
        }, headers=auth_admin)
        assert response.status_code == 422
        assert "lot_id" in response.json()["detail"].lower() or "item" in response.json()["detail"].lower()

    def test_mixed_statuses_worst_case_wins(self, client, auth_admin):
        sid, vid, cid, _ = self._setup(client, auth_admin)
        ir2 = client.post("/api/v1/items", json={"name": f"Item2-{_uid()}", "category": "Consumable", "unit_of_measure": "each"}, headers=auth_admin)
        ir3 = client.post("/api/v1/items", json={"name": f"Item3-{_uid()}", "category": "Consumable", "unit_of_measure": "each"}, headers=auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-06", "timestamp": _utcnow(),
            "line_items": [
                {"compartment_id": cid, "item_id": ir2.json()["item_id"], "quantity_needed": 4, "quantity_found": 4},
                {"compartment_id": cid, "item_id": ir3.json()["item_id"], "quantity_needed": 4, "quantity_found": 0},
            ],
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["status"] == "FAIL"


# ── Check endpoints ───────────────────────────────────────────────────────────

class TestCheckEndpoints:

    def _make_station_and_vehicle(self, client, auth_admin, vtype: str = "ALS"):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": vtype}, headers=auth_admin)
        return sid, vr.json()["vehicle_id"]

    def test_create_daily_check_returns_201(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-05-10", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["status"] == "PASS"
        assert response.json()["performed_by"] == "test-administrator@ems.local"

    def test_create_daily_check_invalid_date_format_returns_422(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "05/10/2026", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_multiple_checks_same_vehicle_same_day_all_succeed(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        payload_base = {"vehicle_id": vid, "station_id": sid, "check_date": "2026-06-15"}
        r1 = client.post("/api/v1/checks/daily", json={**payload_base, "timestamp": _utcnow(), "notes": "Shift-start check"}, headers=auth_admin)
        assert r1.status_code == 201
        time.sleep(0.01)
        r2 = client.post("/api/v1/checks/daily", json={**payload_base, "timestamp": _utcnow(), "notes": "Post-call restock check"}, headers=auth_admin)
        assert r2.status_code == 201
        time.sleep(0.01)
        r3 = client.post("/api/v1/checks/daily", json={**payload_base, "timestamp": _utcnow(), "notes": "Shift-end check"}, headers=auth_admin)
        assert r3.status_code == 201
        ids = {r1.json()["check_id"], r2.json()["check_id"], r3.json()["check_id"]}
        assert len(ids) == 3

    def test_create_daily_check_invalid_vehicle_returns_404(self, client, auth_admin):
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": 99999999, "station_id": 1, "check_date": "2026-05-10", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 404

    def test_daily_check_creates_audit_event(self, client, db, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": "2026-07-01", "timestamp": _utcnow(),
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(
            AuditEvent.action == "CHECK_COMPLETED", AuditEvent.vehicle_id == vid,
        ).first()
        assert event is not None
        assert event.severity == "INFO"

    def test_station_compliance_today_returns_all_checks(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        today = datetime.now(timezone.utc).date().isoformat()
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow(), "notes": "First check"}, headers=auth_admin)
        time.sleep(0.01)
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow(), "notes": "Second check"}, headers=auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}/today", headers=auth_admin)
        assert response.status_code == 200
        assert len(response.json()) == 2


# ── B-E3: Date-range compliance query ───────────────────────────────────────

class TestStationDateRangeChecks:
    """B-E3: GET /checks/daily/station/{id}?from=&to="""

    def _make_sv(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        return sid, vr.json()["vehicle_id"]

    def test_date_range_returns_checks_in_window(self, client, auth_admin):
        sid, vid = self._make_sv(client, auth_admin)
        # Timestamps must land on the intended dates (server derives check_date from timestamp)
        ts_may01  = datetime(2026, 5,  1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        ts_may10  = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        ts_june01 = datetime(2026, 6,  1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": "2026-05-01", "timestamp": ts_may01}, headers=auth_admin)
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": "2026-05-10", "timestamp": ts_may10}, headers=auth_admin)
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": "2026-06-01", "timestamp": ts_june01}, headers=auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}?from=2026-05-01&to=2026-05-31", headers=auth_admin)
        assert response.status_code == 200
        dates = [c["check_date"] for c in response.json()]
        assert "2026-05-01" in dates
        assert "2026-05-10" in dates
        assert "2026-06-01" not in dates

    def test_no_params_defaults_to_today(self, client, auth_admin):
        sid, vid = self._make_sv(client, auth_admin)
        today = datetime.now(timezone.utc).date().isoformat()
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow()}, headers=auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}", headers=auth_admin)
        assert response.status_code == 200
        assert any(c["check_date"] == today for c in response.json())

    def test_from_after_to_returns_422(self, client, auth_admin):
        sid, _ = self._make_sv(client, auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}?from=2026-05-31&to=2026-05-01", headers=auth_admin)
        assert response.status_code == 422
        assert "from" in response.json()["detail"].lower()

    def test_range_over_90_days_returns_422(self, client, auth_admin):
        sid, _ = self._make_sv(client, auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}?from=2026-01-01&to=2026-12-31", headers=auth_admin)
        assert response.status_code == 422
        assert "90" in response.json()["detail"]

    def test_responder_can_query_own_station(self, client, db, auth_admin, auth_responder):
        sid, vid = self._make_sv(client, auth_admin)
        _add_member(db, sid, "test-responder@ems.local", "Responder")
        today = datetime.now(timezone.utc).date().isoformat()
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow()}, headers=auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}", headers=auth_responder)
        assert response.status_code == 200

    def test_non_member_returns_403(self, client, db, auth_admin, auth_responder):
        sid, _ = self._make_sv(client, auth_admin)
        # No _add_member call — responder is not a member
        response = client.get(f"/api/v1/checks/daily/station/{sid}", headers=auth_responder)
        assert response.status_code == 403


# ── Check endpoints (CS checks) ───────────────────────────────────────────────

class TestCSCheckEndpoints:

    def _make_station_and_vehicle(self, client, auth_admin, vtype: str = "ALS"):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": vtype}, headers=auth_admin)
        return sid, vr.json()["vehicle_id"]

    def test_create_cs_check_als_vehicle_returns_201(self, client, auth_admin):
        _, vid = self._make_station_and_vehicle(client, auth_admin, vtype="ALS")
        response = client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones", "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["discrepancy_flag"] is False
        assert response.json()["primary_signer"] == "Test Administrator"

    def test_create_cs_check_non_als_returns_422(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"ENG-{_uid()}", "vehicle_type": "QRV"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        response = client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones", "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_admin)
        assert response.status_code == 422
        assert "ALS" in response.json()["detail"]

    def test_create_cs_check_same_signers_returns_422(self, client, db, auth_responder):
        """Session C: responder needs membership before reaching the dual-signer check."""
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers={"Authorization": "Bearer test-administrator"})
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers={"Authorization": "Bearer test-administrator"})
        vid = vr.json()["vehicle_id"]
        _add_member(db, sid, "test-responder@ems.local", "Responder")
        response = client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "Test Responder", "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_responder)
        assert response.status_code == 422
        assert "dual-signature" in response.json()["detail"].lower()

    def test_cs_check_discrepancy_creates_high_severity_audit(self, client, db, auth_admin):
        _, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones", "timestamp": _utcnow(), "discrepancy_flag": True, "notes": "Count off by 1.",
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(AuditEvent.action == "CS_DISCREPANCY", AuditEvent.vehicle_id == vid).first()
        assert event is not None
        assert event.severity == "HIGH"

    def test_cs_check_no_discrepancy_creates_info_audit(self, client, db, auth_admin):
        _, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones", "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(AuditEvent.action == "CS_CHECK_COMPLETED", AuditEvent.vehicle_id == vid).first()
        assert event is not None
        assert event.severity == "INFO"

    def test_list_vehicle_cs_checks_non_als_returns_422(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"ENG-{_uid()}", "vehicle_type": "QRV"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        response = client.get(f"/api/v1/checks/controlled-substance/vehicle/{vid}", headers=auth_admin)
        assert response.status_code == 422


# ── Audit endpoints ───────────────────────────────────────────────────────────

class TestAuditEndpoints:

    def test_list_audit_events_returns_200(self, client, auth_supervisor):
        response = client.get("/api/v1/audit", headers=auth_supervisor)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_audit_events_filter_by_severity(self, client, db, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones", "timestamp": _utcnow(), "discrepancy_flag": True, "notes": "Count mismatch.",
        }, headers=auth_admin)
        response = client.get("/api/v1/audit?severity=HIGH", headers=auth_admin)
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert all(e["severity"] == "HIGH" for e in events)

    def test_list_audit_events_filter_by_action(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        today = datetime.now(timezone.utc).date().isoformat()
        client.post("/api/v1/checks/daily", json={"vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow()}, headers=auth_admin)
        response = client.get("/api/v1/audit?action=CHECK_COMPLETED", headers=auth_admin)
        assert response.status_code == 200
        assert len(response.json()) >= 1
        assert all(e["action"] == "CHECK_COMPLETED" for e in response.json())

    def test_list_audit_events_limit(self, client, auth_supervisor):
        response = client.get("/api/v1/audit?limit=5", headers=auth_supervisor)
        assert response.status_code == 200
        assert len(response.json()) <= 5

    def test_list_audit_events_invalid_limit_returns_422(self, client, auth_supervisor):
        response = client.get("/api/v1/audit?limit=0", headers=auth_supervisor)
        assert response.status_code == 422


# ── Schema validation tests ───────────────────────────────────────────────────

class TestSchemaValidation:

    def test_stock_lot_expiry_far_future_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/inventory/lots", json={"item_id": 1, "location_id": 1, "quantity": 5, "expiration_date": "2099-01-01"}, headers=auth_admin)
        assert response.status_code == 422

    def test_par_level_min_zero_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/inventory/par-levels", json={"item_id": 1, "location_id": 1, "min_quantity": 0, "max_quantity": 10}, headers=auth_admin)
        assert response.status_code == 422

    def test_vehicle_missing_required_field_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/vehicles", json={"station_id": 1, "vehicle_number": f"AMB-{_uid()}"}, headers=auth_admin)
        assert response.status_code == 422


# ── RBAC enforcement tests ────────────────────────────────────────────────────

class TestRBAC:

    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/stations")
        assert response.status_code in (401, 403)

    def test_responder_can_list_stations(self, client, auth_responder):
        """Responders use GET /stations/my — GET /stations is Admin only."""
        response = client.get("/api/v1/stations", headers=auth_responder)
        assert response.status_code == 403

    def test_responder_can_list_my_stations(self, client, auth_responder):
        response = client.get("/api/v1/stations/my", headers=auth_responder)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_responder_cannot_create_station_returns_403(self, client, auth_responder):
        response = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_responder)
        assert response.status_code == 403

    def test_supervisor_can_list_stations(self, client, auth_supervisor):
        """Supervisors use GET /stations/my — GET /stations is Admin only."""
        response = client.get("/api/v1/stations", headers=auth_supervisor)
        assert response.status_code == 403

    def test_supervisor_can_list_my_stations(self, client, auth_supervisor):
        response = client.get("/api/v1/stations/my", headers=auth_supervisor)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_supervisor_cannot_create_station_returns_403(self, client, auth_supervisor):
        response = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_supervisor)
        assert response.status_code == 403

    def test_admin_can_create_station(self, client, auth_admin):
        response = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        assert response.status_code == 201

    def test_responder_can_read_items(self, client, auth_responder):
        response = client.get("/api/v1/items", headers=auth_responder)
        assert response.status_code == 200

    def test_responder_cannot_create_item_returns_403(self, client, auth_responder):
        response = client.post("/api/v1/items", json={"name": f"Item-{_uid()}", "category": "Medication", "unit_of_measure": "mL"}, headers=auth_responder)
        assert response.status_code == 403

    def test_responder_cannot_access_audit_log_returns_403(self, client, auth_responder):
        response = client.get("/api/v1/audit", headers=auth_responder)
        assert response.status_code == 403

    def test_supervisor_can_access_audit_log(self, client, auth_supervisor):
        response = client.get("/api/v1/audit", headers=auth_supervisor)
        assert response.status_code == 200

    def test_responder_can_submit_daily_check(self, client, db, auth_admin, auth_responder):
        """Session C: responder must be a station member to submit a check."""
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        _add_member(db, sid, "test-responder@ems.local", "Responder")
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": "2026-08-01", "timestamp": _utcnow(),
        }, headers=auth_responder)
        assert response.status_code == 201
        assert response.json()["performed_by"] == "test-responder@ems.local"

    def test_responder_cannot_view_daily_check_detail_returns_403(self, client, db, auth_admin, auth_responder):
        """Session C: responder needs membership to submit, then gets 403 on detail (Supervisor+ only)."""
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        _add_member(db, sid, "test-responder@ems.local", "Responder")
        cr = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": "2026-08-02", "timestamp": _utcnow(),
        }, headers=auth_responder)
        assert cr.status_code == 201, f"Check submission failed: {cr.json()}"
        check_id = cr.json()["check_id"]
        response = client.get(f"/api/v1/checks/daily/{check_id}", headers=auth_responder)
        assert response.status_code == 403


# ── Check type tests ──────────────────────────────────────────────────────────

class TestCheckTypes:
    """
    Tests for the four non-SUPPLY item check types:
      MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT
    """

    def _make_env(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        locs = client.get("/api/v1/inventory/locations", headers=auth_admin).json()
        loc_id = next(loc["location_id"] for loc in locs if loc["vehicle_id"] == vid)
        cr = client.post(f"/api/v1/inventory/locations/{loc_id}/compartments", json={
            "location_id": loc_id, "name": f"Comp-{_uid()}", "sort_order": 1,
        }, headers=auth_admin)
        cid = cr.json()["compartment_id"]
        return sid, vid, loc_id, cid

    def _make_item(self, client, auth_admin, *, check_type: str, name: Optional[str] = None,
                   measurement_minimum: Optional[float] = None,
                   recurrence_days: Optional[int] = None) -> int:
        payload = {
            "name": name or f"Item-{_uid()}",
            "category": "Equipment",
            "unit_of_measure": "each",
            "check_type": check_type,
        }
        if measurement_minimum is not None:
            payload["measurement_minimum"] = measurement_minimum
        if recurrence_days is not None:
            payload["recurrence_days"] = recurrence_days
        r = client.post("/api/v1/items", json=payload, headers=auth_admin)
        assert r.status_code == 201, f"Item creation failed: {r.json()}"
        return r.json()["item_id"]

    def _submit_check(self, client, auth_admin, *, sid, vid, cid, check_date: str, line_items: list) -> dict:
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": check_date, "timestamp": _utcnow(),
            "line_items": line_items,
        }, headers=auth_admin)
        assert response.status_code == 201, f"Check submission failed: {response.json()}"
        return response.json()

    def test_o2_psi_above_minimum_returns_ok(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="MEASUREMENT", measurement_minimum=500.0)
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-01",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "measurement_value": 1800.0}])
        assert body["line_items"][0]["status"] == "OK"
        assert body["status"] == "PASS"

    def test_o2_psi_at_minimum_returns_ok(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="MEASUREMENT", measurement_minimum=500.0)
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-02",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "measurement_value": 500.0}])
        assert body["line_items"][0]["status"] == "OK"

    def test_o2_psi_below_minimum_returns_low(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="MEASUREMENT", measurement_minimum=500.0)
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-03",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "measurement_value": 300.0}])
        assert body["line_items"][0]["status"] == "LOW"

    def test_o2_psi_below_minimum_sets_check_needs_restock(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="MEASUREMENT", measurement_minimum=500.0)
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-04",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "measurement_value": 200.0}])
        assert body["status"] == "NEEDS_RESTOCK"

    def test_measurement_missing_value_returns_missing(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="MEASUREMENT", measurement_minimum=500.0)
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-05",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0}])
        assert body["line_items"][0]["status"] == "MISSING"
        assert body["status"] == "FAIL"

    def test_battery_ok_true_returns_ok(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="FUNCTIONAL")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-06",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "functional_pass": True}])
        assert body["line_items"][0]["status"] == "OK"
        assert body["status"] == "PASS"

    def test_battery_ok_false_returns_fail(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="FUNCTIONAL")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-07",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "functional_pass": False}])
        assert body["line_items"][0]["status"] == "FAIL"

    def test_functional_fail_sets_check_fail(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="FUNCTIONAL")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-08",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "functional_pass": False}])
        assert body["status"] == "FAIL"

    def test_functional_missing_value_returns_missing(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="FUNCTIONAL")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-09",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0}])
        assert body["line_items"][0]["status"] == "MISSING"
        assert body["status"] == "FAIL"

    def test_recent_charge_date_returns_ok(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="DATE_RECORD", recurrence_days=90)
        recent_date = (date.today() - timedelta(days=10)).isoformat()
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-10",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "date_value": recent_date}])
        assert body["line_items"][0]["status"] == "OK"
        assert body["status"] == "PASS"

    def test_overdue_charge_date_returns_overdue(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="DATE_RECORD", recurrence_days=90)
        overdue_date = (date.today() - timedelta(days=100)).isoformat()
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-11",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "date_value": overdue_date}])
        assert body["line_items"][0]["status"] == "OVERDUE"

    def test_overdue_sets_check_fail(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="DATE_RECORD", recurrence_days=30)
        overdue_date = (date.today() - timedelta(days=35)).isoformat()
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-12",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0, "date_value": overdue_date}])
        assert body["status"] == "FAIL"

    def test_date_record_missing_value_returns_missing(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="DATE_RECORD", recurrence_days=90)
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-13",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 0, "quantity_found": 0}])
        assert body["line_items"][0]["status"] == "MISSING"
        assert body["status"] == "FAIL"

    def test_document_present_returns_ok(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="DOCUMENT")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-14",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 1, "quantity_found": 1}])
        assert body["line_items"][0]["status"] == "OK"
        assert body["status"] == "PASS"

    def test_document_missing_returns_missing(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        item_id = self._make_item(client, auth_admin, check_type="DOCUMENT")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-15",
                                  line_items=[{"compartment_id": cid, "item_id": item_id, "quantity_needed": 1, "quantity_found": 0}])
        assert body["line_items"][0]["status"] == "MISSING"
        assert body["status"] == "FAIL"

    def test_mixed_check_types_worst_case_determines_overall_status(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        functional_item = self._make_item(client, auth_admin, check_type="FUNCTIONAL")
        document_item = self._make_item(client, auth_admin, check_type="DOCUMENT")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-16",
                                  line_items=[
                                      {"compartment_id": cid, "item_id": functional_item, "quantity_needed": 0, "quantity_found": 0, "functional_pass": True},
                                      {"compartment_id": cid, "item_id": document_item, "quantity_needed": 1, "quantity_found": 0},
                                  ])
        statuses = {li["item_id"]: li["status"] for li in body["line_items"]}
        assert statuses[functional_item] == "OK"
        assert statuses[document_item] == "MISSING"
        assert body["status"] == "FAIL"

    def test_low_measurement_and_ok_supply_yields_needs_restock(self, client, auth_admin):
        sid, vid, _loc_id, cid = self._make_env(client, auth_admin)
        o2_item = self._make_item(client, auth_admin, check_type="MEASUREMENT", measurement_minimum=500.0)
        supply_item = self._make_item(client, auth_admin, check_type="SUPPLY")
        body = self._submit_check(client, auth_admin, sid=sid, vid=vid, cid=cid, check_date="2026-07-17",
                                  line_items=[
                                      {"compartment_id": cid, "item_id": o2_item, "quantity_needed": 0, "quantity_found": 0, "measurement_value": 100.0},
                                      {"compartment_id": cid, "item_id": supply_item, "quantity_needed": 2, "quantity_found": 2},
                                  ])
        statuses = {li["item_id"]: li["status"] for li in body["line_items"]}
        assert statuses[o2_item] == "LOW"
        assert statuses[supply_item] == "OK"
        assert body["status"] == "NEEDS_RESTOCK"

    def test_create_jump_bag_location_returns_201(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        response = client.post("/api/v1/inventory/locations", json={
            "location_type": "JUMP_BAG", "station_id": sid, "label": f"Jump Bag 710/712 — {_uid()}",
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["location_type"] == "JUMP_BAG"
        assert response.json()["station_id"] == sid

    def test_cannot_create_vehicle_location_via_api_returns_422(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        response = client.post("/api/v1/inventory/locations", json={
            "location_type": "VEHICLE", "station_id": sid, "label": "Should not be allowed",
        }, headers=auth_admin)
        assert response.status_code == 422
