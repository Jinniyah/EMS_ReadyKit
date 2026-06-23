"""
tests/test_item_station_scoping.py
ITM-5 / ITM-8: Verify that item endpoints are scoped to the caller's station.

Coverage:
  - Station-A supervisor cannot list station-B items (403 on list, search, get, edit)
  - POST /admin/items without station membership returns 403
  - Name uniqueness is per-station: same name allowed at two stations, rejected within one
  - GET /admin/items returns only the caller's station's items
  - GET /admin/items/search returns only the caller's station's items
  - Admin bypasses all station membership checks
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember

BASE = "/api/v1/admin/items"

SUPERVISOR_EMAIL = "test-supervisor@ems.local"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _item(name: str, station_id: int, **kwargs) -> dict:
    return {
        "name": name,
        "station_id": station_id,
        "category": "Consumable",
        "check_type": "SUPPLY",
        "unit_of_measure": "each",
        **kwargs,
    }


@pytest.fixture
def two_stations(db: Session):
    """
    Creates Station A and Station B.
    Adds test-supervisor to Station A only.
    Returns {'station_a': id, 'station_b': id}.

    db.commit() (not flush) is used deliberately: route handlers in these tests
    call db.commit(), which releases the active SQLAlchemy savepoint and makes
    all previously-flushed rows permanent for the rest of the test session.
    Committing in the fixture makes that dependency explicit rather than relying
    on a side effect of the first route-handler commit sweeping in the flushed rows.

    SUPERVISOR_EMAIL is safe to hardcode here because the unique constraint on
    StationMember is (station_id, user_id, role), and station_id is unique per
    test via _uid() — so the same email on a different station_id is a distinct
    row and cannot collide across tests.

    If you ever need to add assertions that query StationMember by user_id alone
    (unscoped by station), or if this fixture is promoted to session scope, switch
    to Option B: derive a per-test email from request.node.name and build matching
    auth headers instead of relying on auth_supervisor:

        uid = request.node.name
        email = f"supervisor-{uid}@ems.local"
        token = f"test-supervisor-{uid}"   # auth.py: Bearer {token} → {token}@ems.local
        member = StationMember(user_id=email, ...)
        headers = {"Authorization": f"Bearer {token}"}
        return {..., "auth_supervisor": headers}
    """
    station_a = Station(name=f"Scope-A-{_uid()}", address="1 A St", region="Test")
    station_b = Station(name=f"Scope-B-{_uid()}", address="2 B St", region="Test")
    db.add_all([station_a, station_b])
    db.flush()

    member = StationMember(
        station_id=station_a.station_id,
        user_id=SUPERVISOR_EMAIL,
        role="SUPERVISOR",
        assigned_by="test",
        active=True,
    )
    db.add(member)
    db.commit()

    return {"station_a": station_a.station_id, "station_b": station_b.station_id}


class TestListScopedToStation:

    def test_list_returns_only_own_station_items(
        self, client, auth_admin, auth_supervisor, two_stations
    ):
        sid_a = two_stations["station_a"]
        sid_b = two_stations["station_b"]
        client.post(BASE, json=_item("Gauze 3x3", sid_a), headers=auth_admin)
        client.post(BASE, json=_item("Gauze 3x3", sid_b), headers=auth_admin)

        resp = client.get(f"{BASE}?station_id={sid_a}", headers=auth_supervisor)
        assert resp.status_code == 200
        station_ids = {i["station_id"] for i in resp.json()}
        assert station_ids == {sid_a}

    def test_list_station_b_returns_403_for_station_a_supervisor(
        self, client, auth_supervisor, two_stations
    ):
        resp = client.get(
            f"{BASE}?station_id={two_stations['station_b']}", headers=auth_supervisor
        )
        assert resp.status_code == 403

    def test_admin_can_list_any_station(self, client, auth_admin, two_stations):
        for sid in (two_stations["station_a"], two_stations["station_b"]):
            resp = client.get(f"{BASE}?station_id={sid}", headers=auth_admin)
            assert resp.status_code == 200


class TestSearchScopedToStation:

    def test_search_returns_only_own_station_items(
        self, client, auth_admin, auth_supervisor, two_stations
    ):
        sid_a = two_stations["station_a"]
        sid_b = two_stations["station_b"]
        name = f"Stethoscope-{_uid()}"
        client.post(BASE, json=_item(name, sid_a), headers=auth_admin)
        client.post(BASE, json=_item(name, sid_b), headers=auth_admin)

        resp = client.get(
            f"{BASE}/search?q=Stethoscope&station_id={sid_a}", headers=auth_supervisor
        )
        assert resp.status_code == 200
        station_ids = {i["station_id"] for i in resp.json()}
        assert station_ids == {sid_a}

    def test_search_station_b_returns_403_for_station_a_supervisor(
        self, client, auth_supervisor, two_stations
    ):
        resp = client.get(
            f"{BASE}/search?q=anything&station_id={two_stations['station_b']}",
            headers=auth_supervisor,
        )
        assert resp.status_code == 403

    def test_admin_can_search_any_station(self, client, auth_admin, two_stations):
        for sid in (two_stations["station_a"], two_stations["station_b"]):
            resp = client.get(f"{BASE}/search?q=x&station_id={sid}", headers=auth_admin)
            assert resp.status_code == 200


class TestCreateScopedToStation:

    def test_create_without_membership_returns_403(
        self, client, auth_supervisor, two_stations
    ):
        resp = client.post(
            BASE,
            json=_item(f"Item-{_uid()}", two_stations["station_b"]),
            headers=auth_supervisor,
        )
        assert resp.status_code == 403

    def test_create_with_membership_succeeds(
        self, client, auth_supervisor, two_stations
    ):
        resp = client.post(
            BASE,
            json=_item(f"Item-{_uid()}", two_stations["station_a"]),
            headers=auth_supervisor,
        )
        assert resp.status_code == 201
        assert resp.json()["station_id"] == two_stations["station_a"]


class TestPerStationNameUniqueness:

    def test_same_name_allowed_at_two_stations(self, client, auth_admin, two_stations):
        name = f"Kerlix-{_uid()}"
        r1 = client.post(
            BASE, json=_item(name, two_stations["station_a"]), headers=auth_admin
        )
        r2 = client.post(
            BASE, json=_item(name, two_stations["station_b"]), headers=auth_admin
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["item_id"] != r2.json()["item_id"]

    def test_duplicate_name_at_same_station_returns_409(
        self, client, auth_admin, two_stations
    ):
        name = f"Tourniquet-{_uid()}"
        client.post(
            BASE, json=_item(name, two_stations["station_a"]), headers=auth_admin
        )
        resp = client.post(
            BASE, json=_item(name, two_stations["station_a"]), headers=auth_admin
        )
        assert resp.status_code == 409


class TestGetEditScopedToStation:

    def test_get_item_from_other_station_returns_403(
        self, client, auth_admin, auth_supervisor, two_stations
    ):
        r = client.post(
            BASE,
            json=_item(f"Item-{_uid()}", two_stations["station_b"]),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.get(f"{BASE}/{item_id}", headers=auth_supervisor)
        assert resp.status_code == 403

    def test_get_item_from_own_station_succeeds(
        self, client, auth_admin, auth_supervisor, two_stations
    ):
        r = client.post(
            BASE,
            json=_item(f"Item-{_uid()}", two_stations["station_a"]),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.get(f"{BASE}/{item_id}", headers=auth_supervisor)
        assert resp.status_code == 200

    def test_edit_item_from_other_station_returns_403(
        self, client, auth_admin, auth_supervisor, two_stations
    ):
        r = client.post(
            BASE,
            json=_item(f"Item-{_uid()}", two_stations["station_b"]),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        name = f"Renamed-{_uid()}"
        resp = client.patch(
            f"{BASE}/{item_id}",
            json=_item(name, two_stations["station_b"]),
            headers=auth_supervisor,
        )
        assert resp.status_code == 403

    def test_admin_can_access_any_item(self, client, auth_admin, two_stations):
        for sid in (two_stations["station_a"], two_stations["station_b"]):
            r = client.post(BASE, json=_item(f"Item-{_uid()}", sid), headers=auth_admin)
            item_id = r.json()["item_id"]
            resp = client.get(f"{BASE}/{item_id}", headers=auth_admin)
            assert resp.status_code == 200
