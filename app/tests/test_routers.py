"""
tests/test_routers.py
Phase 2 + Phase 3 (auth) router and schema tests.

All client calls include auth headers. Most tests use auth_admin for
simplicity. RBAC-specific tests use the appropriate role fixture.

performed_by / primary_signer are now set from the JWT identity in the router,
so the request body values are ignored — tests no longer need to assert on
the specific name submitted.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest
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


# ── Unique name helpers ────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        response = client.post("/api/v1/vehicles", json={
            "station_id": sid, "vehicle_number": vnum, "vehicle_type": "BLS",
        }, headers=auth_admin)
        assert response.status_code == 201
        vehicle_id = response.json()["vehicle_id"]

        loc = db.query(InventoryLocation).filter(InventoryLocation.vehicle_id == vehicle_id).first()
        assert loc is not None
        assert loc.location_type == LocationType.VEHICLE

    def test_create_vehicle_invalid_station_returns_404(self, client, auth_admin):
        response = client.post("/api/v1/vehicles", json={
            "station_id": 99999999, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS",
        }, headers=auth_admin)
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
        response = client.post("/api/v1/vehicles", json={
            "station_id": sid, "vehicle_number": f"ENG-{_uid()}", "vehicle_type": "QRV",
        }, headers=auth_admin)
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
            "name": f"Epi-{_uid()}", "category": "Medication",
            "controlled_substance": True, "unit_of_measure": "mL",
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
        loc_id = next(l["location_id"] for l in locs if l["vehicle_id"] == vid)
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
        response = client.post("/api/v1/inventory/lots", json={
            "item_id": 1, "location_id": 1, "quantity": -5,
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_create_stock_lot_invalid_location_returns_404(self, client, auth_admin):
        ir = client.post("/api/v1/items", json={"name": f"Item-{_uid()}", "category": "Medication", "unit_of_measure": "mL"}, headers=auth_admin)
        response = client.post("/api/v1/inventory/lots", json={
            "item_id": ir.json()["item_id"], "location_id": 99999999, "quantity": 5,
        }, headers=auth_admin)
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
        response = client.post("/api/v1/inventory/par-levels", json={
            "item_id": 1, "location_id": 1, "min_quantity": 10, "max_quantity": 5,
        }, headers=auth_admin)
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
            "check_date": "2026-05-10", "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["status"] == "PASS"
        # performed_by should be set to the JWT identity name
        assert response.json()["performed_by"] == "Test Administrator"

    def test_create_daily_check_invalid_date_format_returns_422(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "05/10/2026", "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_create_daily_check_duplicate_returns_409(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        payload = {
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-06-15", "timestamp": _utcnow(), "status": "PASS",
        }
        client.post("/api/v1/checks/daily", json=payload, headers=auth_admin)
        response = client.post("/api/v1/checks/daily", json=payload, headers=auth_admin)
        assert response.status_code == 409

    def test_create_daily_check_invalid_vehicle_returns_404(self, client, auth_admin):
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": 99999999, "station_id": 1,
            "check_date": "2026-05-10", "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_admin)
        assert response.status_code == 404

    def test_daily_check_creates_audit_event(self, client, db, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-07-01", "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(
            AuditEvent.action == "CHECK_COMPLETED",
            AuditEvent.vehicle_id == vid,
        ).first()
        assert event is not None
        assert event.severity == "INFO"

    def test_station_compliance_today(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        today = datetime.now(timezone.utc).date().isoformat()
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": today, "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}/today", headers=auth_admin)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_create_cs_check_als_vehicle_returns_201(self, client, auth_admin):
        _, vid = self._make_station_and_vehicle(client, auth_admin, vtype="ALS")
        response = client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones",
            "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["discrepancy_flag"] is False
        # primary_signer set from JWT
        assert response.json()["primary_signer"] == "Test Administrator"

    def test_create_cs_check_non_als_returns_422(self, client, auth_admin):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"ENG-{_uid()}", "vehicle_type": "QRV"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        response = client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones",
            "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_admin)
        assert response.status_code == 422
        assert "ALS" in response.json()["detail"]

    def test_create_cs_check_same_signers_returns_422(self, client, auth_responder):
        # test-responder identity name is "Test Responder"
        # if secondary_signer == "Test Responder" the router raises 422
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers={"Authorization": "Bearer test-administrator"})
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers={"Authorization": "Bearer test-administrator"})
        vid = vr.json()["vehicle_id"]
        response = client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid,
            "secondary_signer": "Test Responder",  # same as JWT identity for test-responder
            "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_responder)
        assert response.status_code == 422
        assert "dual-signature" in response.json()["detail"].lower()

    def test_cs_check_discrepancy_creates_high_severity_audit(self, client, db, auth_admin):
        _, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones",
            "timestamp": _utcnow(), "discrepancy_flag": True, "notes": "Count off by 1.",
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(
            AuditEvent.action == "CS_DISCREPANCY",
            AuditEvent.vehicle_id == vid,
        ).first()
        assert event is not None
        assert event.severity == "HIGH"

    def test_cs_check_no_discrepancy_creates_info_audit(self, client, db, auth_admin):
        _, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/controlled-substance", json={
            "vehicle_id": vid, "secondary_signer": "M. Jones",
            "timestamp": _utcnow(), "discrepancy_flag": False,
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(
            AuditEvent.action == "CS_CHECK_COMPLETED",
            AuditEvent.vehicle_id == vid,
        ).first()
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
            "vehicle_id": vid, "secondary_signer": "M. Jones",
            "timestamp": _utcnow(), "discrepancy_flag": True, "notes": "Count mismatch.",
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
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": today,
            "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_admin)
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
        response = client.post("/api/v1/inventory/lots", json={
            "item_id": 1, "location_id": 1, "quantity": 5, "expiration_date": "2099-01-01",
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_par_level_min_zero_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/inventory/par-levels", json={
            "item_id": 1, "location_id": 1, "min_quantity": 0, "max_quantity": 10,
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_vehicle_missing_required_field_returns_422(self, client, auth_admin):
        response = client.post("/api/v1/vehicles", json={
            "station_id": 1, "vehicle_number": f"AMB-{_uid()}",
        }, headers=auth_admin)
        assert response.status_code == 422


# ── RBAC enforcement tests ────────────────────────────────────────────────────

class TestRBAC:

    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/stations")
        assert response.status_code == 401

    def test_responder_cannot_list_stations_returns_403(self, client, auth_responder):
        response = client.get("/api/v1/stations", headers=auth_responder)
        assert response.status_code == 403

    def test_responder_cannot_create_station_returns_403(self, client, auth_responder):
        response = client.post("/api/v1/stations", json={
            "name": f"S-{_uid()}", "address": "1 St", "region": "R",
        }, headers=auth_responder)
        assert response.status_code == 403

    def test_supervisor_can_list_stations(self, client, auth_supervisor):
        response = client.get("/api/v1/stations", headers=auth_supervisor)
        assert response.status_code == 200

    def test_supervisor_cannot_create_station_returns_403(self, client, auth_supervisor):
        response = client.post("/api/v1/stations", json={
            "name": f"S-{_uid()}", "address": "1 St", "region": "R",
        }, headers=auth_supervisor)
        assert response.status_code == 403

    def test_admin_can_create_station(self, client, auth_admin):
        response = client.post("/api/v1/stations", json={
            "name": f"S-{_uid()}", "address": "1 St", "region": "R",
        }, headers=auth_admin)
        assert response.status_code == 201

    def test_responder_can_read_items(self, client, auth_responder):
        response = client.get("/api/v1/items", headers=auth_responder)
        assert response.status_code == 200

    def test_responder_cannot_create_item_returns_403(self, client, auth_responder):
        response = client.post("/api/v1/items", json={
            "name": f"Item-{_uid()}", "category": "Medication", "unit_of_measure": "mL",
        }, headers=auth_responder)
        assert response.status_code == 403

    def test_responder_cannot_access_audit_log_returns_403(self, client, auth_responder):
        response = client.get("/api/v1/audit", headers=auth_responder)
        assert response.status_code == 403

    def test_supervisor_can_access_audit_log(self, client, auth_supervisor):
        response = client.get("/api/v1/audit", headers=auth_supervisor)
        assert response.status_code == 200

    def test_responder_can_submit_daily_check(self, client, auth_admin, auth_responder):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-08-01", "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_responder)
        assert response.status_code == 201
        # performed_by comes from JWT — should be the responder's identity
        assert response.json()["performed_by"] == "Test Responder"

    def test_responder_cannot_view_daily_check_detail_returns_403(self, client, auth_admin, auth_responder):
        sr = client.post("/api/v1/stations", json={"name": f"S-{_uid()}", "address": "1 St", "region": "R"}, headers=auth_admin)
        sid = sr.json()["station_id"]
        vr = client.post("/api/v1/vehicles", json={"station_id": sid, "vehicle_number": f"AMB-{_uid()}", "vehicle_type": "ALS"}, headers=auth_admin)
        vid = vr.json()["vehicle_id"]
        cr = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-08-02", "timestamp": _utcnow(), "status": "PASS",
        }, headers=auth_responder)
        check_id = cr.json()["check_id"]
        response = client.get(f"/api/v1/checks/daily/{check_id}", headers=auth_responder)
        assert response.status_code == 403
