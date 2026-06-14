"""
tests/test_member_management.py
Tests for ACC-B6 (edit member name), ACC-B7 (multiple roles per person),
and ACC-B8 (CSV bulk import) in the station membership management endpoints.

Endpoints covered:
  GET  /stations/{id}/members                  -- list members
  POST /stations/{id}/members                  -- add a role row
  PATCH /stations/{id}/members/{member_id}     -- update preferred_name
  DELETE /stations/{id}/members/{member_id}    -- remove a role row
  GET  /stations/{id}/members/import/template  -- CSV template download
  POST /stations/{id}/members/import           -- CSV bulk import
  GET  /stations/my/roles?station_id=          -- roles at a station
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _station(db: Session, *, name: Optional[str] = None) -> Station:
    s = Station(name=name or f"Station-{_uid()}", address="1 Main St", region="R")
    db.add(s)
    db.flush()
    return s


def _member(
    db: Session,
    station_id: int,
    *,
    user_id: Optional[str] = None,
    role: str = "Responder",
    preferred_name: Optional[str] = None,
) -> StationMember:
    m = StationMember(
        station_id=station_id,
        user_id=user_id or f"user-{_uid()}@ems.local",
        role=role,
        preferred_name=preferred_name,
        assigned_by="test-administrator@ems.local",
        active=True,
    )
    db.add(m)
    db.flush()
    return m


def _csv_file(rows: list[dict]) -> bytes:
    """Build a CSV bytes payload from a list of dicts."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["email", "preferred_name", "role"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


# -- List members --------------------------------------------------------------


class TestListMembers:
    def test_supervisor_can_list_members(self, client, db, auth_supervisor):
        s = _station(db)
        _member(db, s.station_id, role="Responder")
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members", headers=auth_supervisor
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_responder_cannot_list_members(self, client, db, auth_responder):
        s = _station(db)
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members", headers=auth_responder
        )
        assert resp.status_code == 403

    def test_returns_only_active_members_by_default(self, client, db, auth_admin):
        s = _station(db)
        active = _member(db, s.station_id)
        inactive = _member(db, s.station_id)
        inactive.active = False
        db.flush()
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members", headers=auth_admin
        )
        ids = [m["member_id"] for m in resp.json()]
        assert active.member_id in ids
        assert inactive.member_id not in ids

    def test_include_inactive_returns_all(self, client, db, auth_admin):
        s = _station(db)
        active = _member(db, s.station_id)
        inactive = _member(db, s.station_id)
        inactive.active = False
        db.flush()
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members?include_inactive=true",
            headers=auth_admin,
        )
        ids = [m["member_id"] for m in resp.json()]
        assert active.member_id in ids
        assert inactive.member_id in ids


# -- Add member ----------------------------------------------------------------


class TestAddMember:
    def test_supervisor_can_add_responder(self, client, db, auth_supervisor):
        s = _station(db)
        email = f"new-{_uid()}@ems.local"
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": email, "role": "Responder"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 201
        assert resp.json()["user_id"] == email
        assert resp.json()["role"] == "Responder"

    def test_supervisor_cannot_add_administrator(self, client, db, auth_supervisor):
        s = _station(db)
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": f"u-{_uid()}@ems.local", "role": "Administrator"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 403

    def test_admin_can_add_administrator(self, client, db, auth_admin):
        s = _station(db)
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": f"u-{_uid()}@ems.local", "role": "Administrator"},
            headers=auth_admin,
        )
        assert resp.status_code == 201

    def test_invalid_role_returns_422(self, client, db, auth_admin):
        s = _station(db)
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": f"u-{_uid()}@ems.local", "role": "Captain"},
            headers=auth_admin,
        )
        assert resp.status_code == 422

    def test_duplicate_active_role_returns_409(self, client, db, auth_admin):
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": email, "role": "Responder"},
            headers=auth_admin,
        )
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": email, "role": "Responder"},
            headers=auth_admin,
        )
        assert resp.status_code == 409

    def test_acc_b7_same_person_can_have_two_roles(self, client, db, auth_admin):
        """ACC-B7: A person can hold Responder AND Supervisor simultaneously."""
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        r1 = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": email, "role": "Responder"},
            headers=auth_admin,
        )
        r2 = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": email, "role": "Supervisor"},
            headers=auth_admin,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members", headers=auth_admin
        )
        rows = [m for m in resp.json() if m["user_id"] == email]
        assert len(rows) == 2
        roles = {m["role"] for m in rows}
        assert roles == {"Responder", "Supervisor"}

    def test_reactivates_inactive_row(self, client, db, auth_admin):
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        m = _member(db, s.station_id, user_id=email, role="Responder")
        m.active = False
        db.flush()
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members",
            json={"user_id": email, "role": "Responder"},
            headers=auth_admin,
        )
        assert resp.status_code == 201
        assert resp.json()["active"] is True


# -- Edit member (ACC-B6) ------------------------------------------------------


class TestEditMember:
    def test_supervisor_can_update_preferred_name(self, client, db, auth_supervisor):
        s = _station(db)
        m = _member(db, s.station_id, preferred_name="Old Name")
        resp = client.patch(
            f"/api/v1/stations/{s.station_id}/members/{m.member_id}",
            json={"preferred_name": "New Name"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        assert resp.json()["preferred_name"] == "New Name"

    def test_name_update_propagates_to_all_rows_for_same_user(
        self, client, db, auth_admin
    ):
        """If a person has two roles, updating their name via one member_id updates both rows."""
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        m1 = _member(db, s.station_id, user_id=email, role="Responder")
        # Second role row -- must exist in DB; value not needed in Python
        _member(db, s.station_id, user_id=email, role="Supervisor")

        client.patch(
            f"/api/v1/stations/{s.station_id}/members/{m1.member_id}",
            json={"preferred_name": "Shared Name"},
            headers=auth_admin,
        )
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members", headers=auth_admin
        )
        rows = [m for m in resp.json() if m["user_id"] == email]
        assert all(m["preferred_name"] == "Shared Name" for m in rows)

    def test_nonexistent_member_returns_404(self, client, db, auth_admin):
        s = _station(db)
        resp = client.patch(
            f"/api/v1/stations/{s.station_id}/members/99999",
            json={"preferred_name": "Ghost"},
            headers=auth_admin,
        )
        assert resp.status_code == 404

    def test_responder_cannot_edit_member(self, client, db, auth_responder):
        s = _station(db)
        m = _member(db, s.station_id)
        resp = client.patch(
            f"/api/v1/stations/{s.station_id}/members/{m.member_id}",
            json={"preferred_name": "Attempt"},
            headers=auth_responder,
        )
        assert resp.status_code == 403


# -- Remove member role --------------------------------------------------------


class TestRemoveMemberRole:
    def test_supervisor_can_remove_responder_row(self, client, db, auth_supervisor):
        s = _station(db)
        m = _member(db, s.station_id, role="Responder")
        resp = client.delete(
            f"/api/v1/stations/{s.station_id}/members/{m.member_id}",
            headers=auth_supervisor,
        )
        assert resp.status_code == 204

    def test_acc_b7_removing_one_role_leaves_other_active(self, client, db, auth_admin):
        """Removing one role row leaves the other role active for that person."""
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        m_resp = _member(db, s.station_id, user_id=email, role="Responder")
        # Supervisor row must exist; value not needed in Python
        _member(db, s.station_id, user_id=email, role="Supervisor")

        client.delete(
            f"/api/v1/stations/{s.station_id}/members/{m_resp.member_id}",
            headers=auth_admin,
        )
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members", headers=auth_admin
        )
        rows = [m for m in resp.json() if m["user_id"] == email]
        assert len(rows) == 1
        assert rows[0]["role"] == "Supervisor"

    def test_cannot_remove_last_own_active_row(self, client, db, auth_supervisor):
        s = _station(db)
        m = _member(
            db, s.station_id, user_id="test-supervisor@ems.local", role="Supervisor"
        )
        resp = client.delete(
            f"/api/v1/stations/{s.station_id}/members/{m.member_id}",
            headers=auth_supervisor,
        )
        assert resp.status_code == 403
        assert "last active role" in resp.json()["detail"].lower()

    def test_can_remove_one_of_own_two_rows(self, client, db, auth_admin):
        """An admin can remove one of their own role rows if another remains."""
        s = _station(db)
        m1 = _member(
            db, s.station_id, user_id="test-administrator@ems.local", role="Responder"
        )
        _member(
            db,
            s.station_id,
            user_id="test-administrator@ems.local",
            role="Administrator",
        )
        resp = client.delete(
            f"/api/v1/stations/{s.station_id}/members/{m1.member_id}",
            headers=auth_admin,
        )
        assert resp.status_code == 204

    def test_nonexistent_member_id_returns_404(self, client, db, auth_admin):
        s = _station(db)
        resp = client.delete(
            f"/api/v1/stations/{s.station_id}/members/99999",
            headers=auth_admin,
        )
        assert resp.status_code == 404


# -- My roles (ACC-B7) ---------------------------------------------------------


class TestMyRoles:
    def test_returns_roles_for_current_user(self, client, db, auth_supervisor):
        s = _station(db)
        _member(
            db, s.station_id, user_id="test-supervisor@ems.local", role="Supervisor"
        )
        _member(db, s.station_id, user_id="test-supervisor@ems.local", role="Responder")
        resp = client.get(
            f"/api/v1/stations/my/roles?station_id={s.station_id}",
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        assert set(resp.json()) == {"Supervisor", "Responder"}

    def test_admin_gets_all_roles_regardless_of_rows(self, client, db, auth_admin):
        """Administrator always has all three roles available."""
        s = _station(db)
        resp = client.get(
            f"/api/v1/stations/my/roles?station_id={s.station_id}",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert set(resp.json()) == {"Administrator", "Supervisor", "Responder"}

    def test_user_with_no_membership_returns_empty(self, client, db, auth_responder):
        s = _station(db)
        resp = client.get(
            f"/api/v1/stations/my/roles?station_id={s.station_id}",
            headers=auth_responder,
        )
        assert resp.status_code == 200
        assert resp.json() == []


# -- CSV import (ACC-B8) -------------------------------------------------------


class TestCsvImport:
    def _post_csv(self, client, station_id, rows, headers):
        content = _csv_file(rows)
        return client.post(
            f"/api/v1/stations/{station_id}/members/import",
            files={"file": ("members.csv", content, "text/csv")},
            headers=headers,
        )

    def test_imports_valid_rows(self, client, db, auth_admin):
        s = _station(db)
        rows = [
            {
                "email": f"u1-{_uid()}@ems.local",
                "preferred_name": "User One",
                "role": "Responder",
            },
            {
                "email": f"u2-{_uid()}@ems.local",
                "preferred_name": "User Two",
                "role": "Supervisor",
            },
        ]
        resp = self._post_csv(client, s.station_id, rows, auth_admin)
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] == 2
        assert body["errors"] == []

    def test_skips_existing_active_rows(self, client, db, auth_admin):
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        _member(db, s.station_id, user_id=email, role="Responder")
        rows = [{"email": email, "preferred_name": "", "role": "Responder"}]
        resp = self._post_csv(client, s.station_id, rows, auth_admin)
        assert resp.status_code == 200
        assert resp.json()["skipped"] == 1
        assert resp.json()["created"] == 0

    def test_reactivates_inactive_rows(self, client, db, auth_admin):
        s = _station(db)
        email = f"u-{_uid()}@ems.local"
        m = _member(db, s.station_id, user_id=email, role="Responder")
        m.active = False
        db.flush()
        rows = [{"email": email, "preferred_name": "Reactivated", "role": "Responder"}]
        resp = self._post_csv(client, s.station_id, rows, auth_admin)
        assert resp.status_code == 200
        assert resp.json()["reactivated"] == 1

    def test_invalid_role_collected_as_error(self, client, db, auth_admin):
        s = _station(db)
        rows = [
            {"email": f"u-{_uid()}@ems.local", "preferred_name": "", "role": "Captain"}
        ]
        resp = self._post_csv(client, s.station_id, rows, auth_admin)
        assert resp.status_code == 200
        assert resp.json()["errors"][0]["row"] == 2

    def test_supervisor_cannot_import_administrator_rows(
        self, client, db, auth_supervisor
    ):
        s = _station(db)
        rows = [
            {
                "email": f"u-{_uid()}@ems.local",
                "preferred_name": "",
                "role": "Administrator",
            }
        ]
        resp = self._post_csv(client, s.station_id, rows, auth_supervisor)
        assert resp.status_code == 200
        assert resp.json()["created"] == 0
        assert len(resp.json()["errors"]) == 1

    def test_missing_required_column_returns_422(self, client, db, auth_admin):
        s = _station(db)
        content = b"email,preferred_name\nu@ems.local,Test\n"
        resp = client.post(
            f"/api/v1/stations/{s.station_id}/members/import",
            files={"file": ("members.csv", content, "text/csv")},
            headers=auth_admin,
        )
        assert resp.status_code == 422

    def test_template_download_returns_csv(self, client, db, auth_admin):
        s = _station(db)
        resp = client.get(
            f"/api/v1/stations/{s.station_id}/members/import/template",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_responder_cannot_import(self, client, db, auth_responder):
        s = _station(db)
        rows = [
            {
                "email": f"u-{_uid()}@ems.local",
                "preferred_name": "",
                "role": "Responder",
            }
        ]
        resp = self._post_csv(client, s.station_id, rows, auth_responder)
        assert resp.status_code == 403
