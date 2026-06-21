"""
tests/test_admin_items.py
Item catalog admin endpoints (ADMIN-B1 through ADMIN-B4).

Coverage:
  - List items with filters (category, check_type, active)
  - Typeahead search across name, alternate_names, ai_tags
  - Create item (Supervisor+); duplicate name → 409; duplicate barcode → 409
  - Edit item (Supervisor+)
  - Deactivate item (Admin only); Supervisor cannot deactivate
  - AI fields stored and returned correctly
  - Inactive items excluded from search by default
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

BASE = "/api/v1/admin/items"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _item(name: str, **kwargs) -> dict:
    return {
        "name": name,
        "category": "Consumable",
        "check_type": "SUPPLY",
        "unit_of_measure": "each",
        **kwargs,
    }


@pytest.fixture
def station_id(client, auth_admin):
    """Create a fresh station per test and add supervisor as a member."""
    r = client.post(
        "/api/v1/stations",
        json={"name": f"AdminItems-{_uid()}", "address": "1 Test St", "region": "Test"},
        headers=auth_admin,
    )
    assert r.status_code == 201
    sid = r.json()["station_id"]
    client.post(
        f"/api/v1/stations/{sid}/members",
        json={"user_id": "test-supervisor@ems.local", "role": "Supervisor"},
        headers=auth_admin,
    )
    return sid


class TestListItems:

    def test_list_returns_active_by_default(self, client, auth_admin, station_id):
        client.post(
            BASE, json=_item("Kerlix Large", station_id=station_id), headers=auth_admin
        )
        resp = client.get(
            f"{BASE}?station_id={station_id}&active=true", headers=auth_admin
        )
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Kerlix Large" in names

    def test_filter_by_category(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item("Test Medication", station_id=station_id, category="Medication"),
            headers=auth_admin,
        )
        client.post(
            BASE,
            json=_item("Test Consumable", station_id=station_id, category="Consumable"),
            headers=auth_admin,
        )
        resp = client.get(
            f"{BASE}?station_id={station_id}&category=Medication", headers=auth_admin
        )
        assert resp.status_code == 200
        categories = {i["category"] for i in resp.json()}
        assert categories == {"Medication"}

    def test_filter_by_check_type(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item(
                "O2 PSI Reading",
                station_id=station_id,
                check_type="MEASUREMENT",
                unit_of_measure="PSI",
            ),
            headers=auth_admin,
        )
        resp = client.get(
            f"{BASE}?station_id={station_id}&check_type=MEASUREMENT", headers=auth_admin
        )
        assert resp.status_code == 200
        types = {i["check_type"] for i in resp.json()}
        assert types == {"MEASUREMENT"}

    def test_include_inactive(self, client, auth_admin, station_id):
        r = client.post(
            BASE,
            json=_item("Soon Inactive Item", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        # active=true should exclude it
        resp_active = client.get(
            f"{BASE}?station_id={station_id}&active=true", headers=auth_admin
        )
        assert not any(i["item_id"] == item_id for i in resp_active.json())
        # no active param returns all items including inactive
        resp_all = client.get(f"{BASE}?station_id={station_id}", headers=auth_admin)
        assert any(i["item_id"] == item_id for i in resp_all.json())

    def test_responder_cannot_list(self, client, auth_responder, station_id):
        resp = client.get(f"{BASE}?station_id={station_id}", headers=auth_responder)
        assert resp.status_code == 403


class TestSearchItems:

    def test_search_by_name(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item("NRB Mask Adult", station_id=station_id),
            headers=auth_admin,
        )
        client.post(
            BASE, json=_item("BVM Adult", station_id=station_id), headers=auth_admin
        )
        resp = client.get(
            f"{BASE}/search?q=NRB&station_id={station_id}", headers=auth_admin
        )
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "NRB Mask Adult" in names
        assert "BVM Adult" not in names

    def test_search_by_alternate_names(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item(
                "Non-Rebreather Mask",
                station_id=station_id,
                alternate_names="NRB,non-rebreather,O2 mask",
            ),
            headers=auth_admin,
        )
        resp = client.get(
            f"{BASE}/search?q=non-rebreather&station_id={station_id}",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Non-Rebreather Mask" in names

    def test_search_by_ai_tags(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item(
                "CAT Tourniquet",
                station_id=station_id,
                ai_tags="tourniquet,CAT,hemostatic,combat",
            ),
            headers=auth_admin,
        )
        resp = client.get(
            f"{BASE}/search?q=hemostatic&station_id={station_id}", headers=auth_admin
        )
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "CAT Tourniquet" in names

    def test_search_case_insensitive(self, client, auth_admin, station_id):
        client.post(
            BASE, json=_item("Kerlix Roll", station_id=station_id), headers=auth_admin
        )
        resp = client.get(
            f"{BASE}/search?q=kerlix&station_id={station_id}", headers=auth_admin
        )
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Kerlix Roll" in names

    def test_search_excludes_inactive_by_default(self, client, auth_admin, station_id):
        r = client.post(
            BASE, json=_item("Old BP Cuff", station_id=station_id), headers=auth_admin
        )
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.get(
            f"{BASE}/search?q=Old+BP+Cuff&station_id={station_id}", headers=auth_admin
        )
        assert resp.status_code == 200
        assert not any(i["item_id"] == item_id for i in resp.json())

    def test_search_includes_inactive_when_requested(
        self, client, auth_admin, station_id
    ):
        r = client.post(
            BASE,
            json=_item("Retired Splint", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.get(
            f"{BASE}/search?q=Retired+Splint&station_id={station_id}&active_only=false",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert any(i["item_id"] == item_id for i in resp.json())

    def test_search_respects_limit(self, client, auth_admin, station_id):
        for i in range(5):
            client.post(
                BASE,
                json=_item(f"Gauze Pad {i}cm", station_id=station_id),
                headers=auth_admin,
            )
        resp = client.get(
            f"{BASE}/search?q=Gauze&station_id={station_id}&limit=3", headers=auth_admin
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 3


class TestCreateItem:

    def test_create_basic_item(self, client, auth_admin, station_id):
        resp = client.post(
            BASE,
            json=_item("Tourniquet CAT Gen 7", station_id=station_id),
            headers=auth_admin,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Tourniquet CAT Gen 7"
        assert data["category"] == "Consumable"
        assert data["active"] is True

    def test_create_measurement_item(self, client, auth_admin, station_id):
        resp = client.post(
            BASE,
            json=_item(
                "On-Board O2 PSI",
                station_id=station_id,
                check_type="MEASUREMENT",
                unit_of_measure="PSI",
                measurement_minimum=500.0,
                measurement_maximum=2200.0,
            ),
            headers=auth_admin,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["check_type"] == "MEASUREMENT"
        assert data["measurement_minimum"] == 500.0

    def test_create_date_record_item(self, client, auth_admin, station_id):
        resp = client.post(
            BASE,
            json=_item(
                "AED Date of Last Charge",
                station_id=station_id,
                category="Equipment",
                check_type="DATE_RECORD",
                unit_of_measure="N/A",
                recurrence_days=90,
            ),
            headers=auth_admin,
        )
        assert resp.status_code == 201
        assert resp.json()["recurrence_days"] == 90

    def test_create_with_ai_fields(self, client, auth_admin, station_id):
        resp = client.post(
            BASE,
            json=_item(
                "NRB Mask Pediatric",
                station_id=station_id,
                ai_tags="mask,NRB,pediatric,oxygen",
                alternate_names="NRB peds,pediatric O2 mask",
                barcode="012345678901",
            ),
            headers=auth_admin,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ai_tags"] == "mask,NRB,pediatric,oxygen"
        assert data["alternate_names"] == "NRB peds,pediatric O2 mask"
        assert data["barcode"] == "012345678901"

    def test_duplicate_name_returns_409(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item("Duplicate Item", station_id=station_id),
            headers=auth_admin,
        )
        resp = client.post(
            BASE,
            json=_item("Duplicate Item", station_id=station_id),
            headers=auth_admin,
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_duplicate_barcode_returns_409(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item("Item A", station_id=station_id, barcode="999000111"),
            headers=auth_admin,
        )
        resp = client.post(
            BASE,
            json=_item("Item B", station_id=station_id, barcode="999000111"),
            headers=auth_admin,
        )
        assert resp.status_code == 409
        assert "barcode" in resp.json()["detail"].lower()

    def test_supervisor_can_create(self, client, auth_supervisor, station_id):
        resp = client.post(
            BASE,
            json=_item("Supervisor Created Item", station_id=station_id),
            headers=auth_supervisor,
        )
        assert resp.status_code == 201

    def test_responder_cannot_create(self, client, auth_responder, station_id):
        resp = client.post(
            BASE,
            json=_item("Responder Item", station_id=station_id),
            headers=auth_responder,
        )
        assert resp.status_code == 403


class TestUpdateItem:

    def test_edit_item_name(self, client, auth_admin, station_id):
        r = client.post(
            BASE, json=_item("Old Name", station_id=station_id), headers=auth_admin
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}",
            json=_item("New Name", station_id=station_id),
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_edit_ai_fields(self, client, auth_admin, station_id):
        r = client.post(
            BASE,
            json=_item("Item For AI Edit", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}",
            json=_item(
                "Item For AI Edit",
                station_id=station_id,
                alternate_names="shortname,alias",
                ai_tags="tag1,tag2",
            ),
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["alternate_names"] == "shortname,alias"

    def test_edit_name_conflict_returns_409(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item("Existing Item Name", station_id=station_id),
            headers=auth_admin,
        )
        r = client.post(
            BASE,
            json=_item("Item To Rename", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}",
            json=_item("Existing Item Name", station_id=station_id),
            headers=auth_admin,
        )
        assert resp.status_code == 409

    def test_edit_same_name_does_not_conflict(self, client, auth_admin, station_id):
        r = client.post(
            BASE,
            json=_item("Stable Name Item", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}",
            json={
                **_item("Stable Name Item", station_id=station_id),
                "unit_of_measure": "box",
            },
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["unit_of_measure"] == "box"


class TestDeactivateItem:

    def test_admin_can_deactivate(self, client, auth_admin, station_id):
        r = client.post(
            BASE,
            json=_item("Item To Deactivate", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_deactivate_already_inactive_returns_409(
        self, client, auth_admin, station_id
    ):
        r = client.post(
            BASE,
            json=_item("Already Inactive", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        assert resp.status_code == 409

    def test_supervisor_cannot_deactivate(
        self, client, auth_admin, auth_supervisor, station_id
    ):
        r = client.post(
            BASE,
            json=_item("Supervisor Cannot Touch", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_supervisor)
        assert resp.status_code == 403

    def test_deactivated_item_excluded_from_active_list(
        self, client, auth_admin, station_id
    ):
        r = client.post(
            BASE,
            json=_item("Will Be Deactivated", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.get(
            f"{BASE}?station_id={station_id}&active=true", headers=auth_admin
        )
        assert not any(i["item_id"] == item_id for i in resp.json())


class TestAiFieldsEndpoint:
    """PATCH /admin/items/{id}/ai-fields — AI-B1 (Admin only)."""

    def test_update_ai_fields_returns_updated_item(
        self, client, auth_admin, station_id
    ):
        r = client.post(
            BASE,
            json=_item("AI Fields Target", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}/ai-fields",
            json={
                "ai_tags": "mask,oxygen",
                "alternate_names": "NRB,non-rebreather",
                "barcode": "012345600001",
            },
            headers=auth_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai_tags"] == "mask,oxygen"
        assert data["alternate_names"] == "NRB,non-rebreather"
        assert data["barcode"] == "012345600001"
        assert data["name"] == "AI Fields Target"

    def test_partial_update_preserves_other_fields(
        self, client, auth_admin, station_id
    ):
        r = client.post(
            BASE,
            json=_item(
                "Partial AI Update", station_id=station_id, ai_tags="existing-tag"
            ),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}/ai-fields",
            json={"alternate_names": "alias1"},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["alternate_names"] == "alias1"
        assert data["ai_tags"] == "existing-tag"

    def test_duplicate_barcode_returns_409(self, client, auth_admin, station_id):
        client.post(
            BASE,
            json=_item("Item With Barcode", station_id=station_id, barcode="BCODE999"),
            headers=auth_admin,
        )
        r = client.post(
            BASE, json=_item("Other Item", station_id=station_id), headers=auth_admin
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}/ai-fields",
            json={"barcode": "BCODE999"},
            headers=auth_admin,
        )
        assert resp.status_code == 409

    def test_supervisor_cannot_update_ai_fields_returns_403(
        self, client, auth_admin, auth_supervisor, station_id
    ):
        r = client.post(
            BASE,
            json=_item("AI Supervisor Guard", station_id=station_id),
            headers=auth_admin,
        )
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}/ai-fields",
            json={"ai_tags": "should-fail"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 403

    def test_unknown_item_returns_404(self, client, auth_admin):
        resp = client.patch(
            f"{BASE}/99999999/ai-fields",
            json={"ai_tags": "test"},
            headers=auth_admin,
        )
        assert resp.status_code == 404
