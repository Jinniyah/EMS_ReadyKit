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

from datetime import datetime, timezone

BASE = "/api/v1/admin/items"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _item(name: str, **kwargs) -> dict:
    return {
        "name": name,
        "category": "Consumable",
        "check_type": "SUPPLY",
        "unit_of_measure": "each",
        **kwargs,
    }


class TestListItems:

    def test_list_returns_active_by_default(self, client, auth_admin):
        client.post(BASE, json=_item("Kerlix Large"), headers=auth_admin)
        resp = client.get(BASE, headers=auth_admin)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Kerlix Large" in names

    def test_filter_by_category(self, client, auth_admin):
        client.post(
            BASE,
            json=_item("Test Medication", category="Medication"),
            headers=auth_admin,
        )
        client.post(
            BASE,
            json=_item("Test Consumable", category="Consumable"),
            headers=auth_admin,
        )
        resp = client.get(f"{BASE}?category=Medication", headers=auth_admin)
        assert resp.status_code == 200
        categories = {i["category"] for i in resp.json()}
        assert categories == {"Medication"}

    def test_filter_by_check_type(self, client, auth_admin):
        client.post(
            BASE,
            json=_item(
                "O2 PSI Reading", check_type="MEASUREMENT", unit_of_measure="PSI"
            ),
            headers=auth_admin,
        )
        resp = client.get(f"{BASE}?check_type=MEASUREMENT", headers=auth_admin)
        assert resp.status_code == 200
        types = {i["check_type"] for i in resp.json()}
        assert types == {"MEASUREMENT"}

    def test_include_inactive(self, client, auth_admin):
        r = client.post(BASE, json=_item("Soon Inactive Item"), headers=auth_admin)
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        # Default (active=true) should exclude it
        resp_active = client.get(BASE, headers=auth_admin)
        assert not any(i["item_id"] == item_id for i in resp_active.json())
        # active=false should include it
        resp_all = client.get(f"{BASE}?active=false", headers=auth_admin)
        assert any(i["item_id"] == item_id for i in resp_all.json())

    def test_responder_cannot_list(self, client, auth_responder):
        resp = client.get(BASE, headers=auth_responder)
        assert resp.status_code == 403


class TestSearchItems:

    def test_search_by_name(self, client, auth_admin):
        client.post(BASE, json=_item("NRB Mask Adult"), headers=auth_admin)
        client.post(BASE, json=_item("BVM Adult"), headers=auth_admin)
        resp = client.get(f"{BASE}/search?q=NRB", headers=auth_admin)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "NRB Mask Adult" in names
        assert "BVM Adult" not in names

    def test_search_by_alternate_names(self, client, auth_admin):
        client.post(
            BASE,
            json=_item(
                "Non-Rebreather Mask", alternate_names="NRB,non-rebreather,O2 mask"
            ),
            headers=auth_admin,
        )
        resp = client.get(f"{BASE}/search?q=non-rebreather", headers=auth_admin)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Non-Rebreather Mask" in names

    def test_search_by_ai_tags(self, client, auth_admin):
        client.post(
            BASE,
            json=_item("CAT Tourniquet", ai_tags="tourniquet,CAT,hemostatic,combat"),
            headers=auth_admin,
        )
        resp = client.get(f"{BASE}/search?q=hemostatic", headers=auth_admin)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "CAT Tourniquet" in names

    def test_search_case_insensitive(self, client, auth_admin):
        client.post(BASE, json=_item("Kerlix Roll"), headers=auth_admin)
        resp = client.get(f"{BASE}/search?q=kerlix", headers=auth_admin)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Kerlix Roll" in names

    def test_search_excludes_inactive_by_default(self, client, auth_admin):
        r = client.post(BASE, json=_item("Old BP Cuff"), headers=auth_admin)
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.get(f"{BASE}/search?q=Old BP Cuff", headers=auth_admin)
        assert resp.status_code == 200
        assert not any(i["item_id"] == item_id for i in resp.json())

    def test_search_includes_inactive_when_requested(self, client, auth_admin):
        r = client.post(BASE, json=_item("Retired Splint"), headers=auth_admin)
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.get(
            f"{BASE}/search?q=Retired Splint&active_only=false", headers=auth_admin
        )
        assert resp.status_code == 200
        assert any(i["item_id"] == item_id for i in resp.json())

    def test_search_respects_limit(self, client, auth_admin):
        for i in range(5):
            client.post(BASE, json=_item(f"Gauze Pad {i}cm"), headers=auth_admin)
        resp = client.get(f"{BASE}/search?q=Gauze&limit=3", headers=auth_admin)
        assert resp.status_code == 200
        assert len(resp.json()) <= 3


class TestCreateItem:

    def test_create_basic_item(self, client, auth_admin):
        resp = client.post(BASE, json=_item("Tourniquet CAT Gen 7"), headers=auth_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Tourniquet CAT Gen 7"
        assert data["category"] == "Consumable"
        assert data["active"] is True

    def test_create_measurement_item(self, client, auth_admin):
        resp = client.post(
            BASE,
            json=_item(
                "On-Board O2 PSI",
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

    def test_create_date_record_item(self, client, auth_admin):
        resp = client.post(
            BASE,
            json=_item(
                "AED Date of Last Charge",
                category="Equipment",
                check_type="DATE_RECORD",
                unit_of_measure="N/A",
                recurrence_days=90,
            ),
            headers=auth_admin,
        )
        assert resp.status_code == 201
        assert resp.json()["recurrence_days"] == 90

    def test_create_with_ai_fields(self, client, auth_admin):
        resp = client.post(
            BASE,
            json=_item(
                "NRB Mask Pediatric",
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

    def test_duplicate_name_returns_409(self, client, auth_admin):
        client.post(BASE, json=_item("Duplicate Item"), headers=auth_admin)
        resp = client.post(BASE, json=_item("Duplicate Item"), headers=auth_admin)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_duplicate_barcode_returns_409(self, client, auth_admin):
        client.post(BASE, json=_item("Item A", barcode="999000111"), headers=auth_admin)
        resp = client.post(
            BASE, json=_item("Item B", barcode="999000111"), headers=auth_admin
        )
        assert resp.status_code == 409
        assert "barcode" in resp.json()["detail"].lower()

    def test_supervisor_can_create(self, client, auth_supervisor):
        resp = client.post(
            BASE, json=_item("Supervisor Created Item"), headers=auth_supervisor
        )
        assert resp.status_code == 201

    def test_responder_cannot_create(self, client, auth_responder):
        resp = client.post(BASE, json=_item("Responder Item"), headers=auth_responder)
        assert resp.status_code == 403


class TestUpdateItem:

    def test_edit_item_name(self, client, auth_admin):
        r = client.post(BASE, json=_item("Old Name"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}", json=_item("New Name"), headers=auth_admin
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_edit_ai_fields(self, client, auth_admin):
        r = client.post(BASE, json=_item("Item For AI Edit"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}",
            json=_item(
                "Item For AI Edit",
                alternate_names="shortname,alias",
                ai_tags="tag1,tag2",
            ),
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["alternate_names"] == "shortname,alias"

    def test_edit_name_conflict_returns_409(self, client, auth_admin):
        client.post(BASE, json=_item("Existing Item Name"), headers=auth_admin)
        r = client.post(BASE, json=_item("Item To Rename"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}", json=_item("Existing Item Name"), headers=auth_admin
        )
        assert resp.status_code == 409

    def test_edit_same_name_does_not_conflict(self, client, auth_admin):
        r = client.post(BASE, json=_item("Stable Name Item"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}",
            json={
                **_item("Stable Name Item"),
                "unit_of_measure": "box",
            },
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["unit_of_measure"] == "box"


class TestDeactivateItem:

    def test_admin_can_deactivate(self, client, auth_admin):
        r = client.post(BASE, json=_item("Item To Deactivate"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_deactivate_already_inactive_returns_409(self, client, auth_admin):
        r = client.post(BASE, json=_item("Already Inactive"), headers=auth_admin)
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        assert resp.status_code == 409

    def test_supervisor_cannot_deactivate(self, client, auth_admin, auth_supervisor):
        r = client.post(BASE, json=_item("Supervisor Cannot Touch"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_supervisor)
        assert resp.status_code == 403

    def test_deactivated_item_excluded_from_active_list(self, client, auth_admin):
        r = client.post(BASE, json=_item("Will Be Deactivated"), headers=auth_admin)
        item_id = r.json()["item_id"]
        client.patch(f"{BASE}/{item_id}/deactivate", headers=auth_admin)
        resp = client.get(BASE, headers=auth_admin)
        assert not any(i["item_id"] == item_id for i in resp.json())


class TestAiFieldsEndpoint:
    """PATCH /admin/items/{id}/ai-fields — AI-B1 (Admin only)."""

    def test_update_ai_fields_returns_updated_item(self, client, auth_admin):
        r = client.post(BASE, json=_item("AI Fields Target"), headers=auth_admin)
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

    def test_partial_update_preserves_other_fields(self, client, auth_admin):
        r = client.post(
            BASE,
            json=_item("Partial AI Update", ai_tags="existing-tag"),
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

    def test_duplicate_barcode_returns_409(self, client, auth_admin):
        client.post(
            BASE,
            json=_item("Item With Barcode", barcode="BCODE999"),
            headers=auth_admin,
        )
        r = client.post(BASE, json=_item("Other Item"), headers=auth_admin)
        item_id = r.json()["item_id"]
        resp = client.patch(
            f"{BASE}/{item_id}/ai-fields",
            json={"barcode": "BCODE999"},
            headers=auth_admin,
        )
        assert resp.status_code == 409

    def test_supervisor_cannot_update_ai_fields_returns_403(
        self, client, auth_admin, auth_supervisor
    ):
        r = client.post(BASE, json=_item("AI Supervisor Guard"), headers=auth_admin)
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
