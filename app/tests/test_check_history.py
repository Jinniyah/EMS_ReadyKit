"""
tests/test_check_history.py
Tests for check history, acknowledgement, and soft-delete endpoints.

Covers:
  CH-B1: GET  /checks/daily/my-history       — own checks only, date filters
  CH-B2: GET  /checks/daily/{id}/detail      — RBAC scoping
  B-E2:  PATCH /checks/daily/{id}/acknowledge — corrective action
  CH-B3: DELETE /checks/daily/{id}           — soft-delete lifecycle
  RBAC enforcement on all restricted endpoints

Note: Starlette TestClient (requests-backed) does not support json= on
DELETE requests via client.delete(). Use client.request("DELETE", ..., json=)
instead — the underlying requests.Session.request() accepts json= for any
HTTP method.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from ems_readykit.models import (
    InventoryLocation,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)
from ems_readykit.models.daily_inventory_check import DailyInventoryCheck, CheckStatus


# ── Helpers ────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _station(db: Session, *, name: Optional[str] = None) -> Station:
    s = Station(name=name or f"Station-{_uid()}", address="1 Main St", region="Downriver")
    db.add(s)
    db.flush()
    return s


def _vehicle(db: Session, station_id: int) -> Vehicle:
    number = f"AMB-{_uid()}"
    v = Vehicle(station_id=station_id, vehicle_number=number, vehicle_type=VehicleType.ALS)
    db.add(v)
    db.flush()
    loc = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station_id,
        vehicle_id=v.vehicle_id,
        label=f"{number} — ALS",
    )
    db.add(loc)
    db.flush()
    return v


def _check(
    db: Session,
    vehicle_id: int,
    station_id: int,
    *,
    performed_by: str = "Test Responder",
    check_date: str = "2026-05-23",
    check_status: CheckStatus = CheckStatus.FAIL,
) -> DailyInventoryCheck:
    c = DailyInventoryCheck(
        vehicle_id=vehicle_id,
        station_id=station_id,
        check_date=check_date,
        performed_by=performed_by,
        timestamp=datetime.now(timezone.utc),
        status=check_status,
    )
    db.add(c)
    db.flush()
    return c


def _delete_with_body(client, url: str, body: dict, headers: dict):
    """
    client.delete() is requests-backed and doesn't forward json= to the body.
    client.request("DELETE", ..., json=) goes through the full requests.Session
    path which handles json= correctly for any HTTP method.
    """
    return client.request("DELETE", url, json=body, headers=headers)


# ── CH-B1: My check history ────────────────────────────────────────────────────

class TestMyCheckHistory:
    def test_returns_own_checks(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        _check(db, v.vehicle_id, s.station_id, performed_by="Test Responder")
        _check(db, v.vehicle_id, s.station_id, performed_by="Test Responder")

        resp = client.get("/api/v1/checks/daily/my-history", headers=auth_responder)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_does_not_return_other_users_checks(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        _check(db, v.vehicle_id, s.station_id, performed_by="Someone Else")

        resp = client.get("/api/v1/checks/daily/my-history", headers=auth_responder)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_excludes_soft_deleted(self, client, db, auth_responder, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, performed_by="Test Responder")

        _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Test deletion for history exclusion check."},
            auth_supervisor,
        )

        resp = client.get("/api/v1/checks/daily/my-history", headers=auth_responder)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_date_filter_from(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        _check(db, v.vehicle_id, s.station_id, performed_by="Test Responder", check_date="2026-05-01")
        _check(db, v.vehicle_id, s.station_id, performed_by="Test Responder", check_date="2026-05-23")

        resp = client.get(
            "/api/v1/checks/daily/my-history?from=2026-05-20",
            headers=auth_responder,
        )
        assert resp.status_code == 200
        assert all(r["check_date"] >= "2026-05-20" for r in resp.json())

    def test_unauthenticated_returns_401_or_403(self, client):
        resp = client.get("/api/v1/checks/daily/my-history")
        assert resp.status_code in (401, 403)


# ── CH-B2: Check detail with RBAC scoping ─────────────────────────────────────

class TestCheckDetail:
    def test_responder_can_see_own_check(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, performed_by="Test Responder")

        resp = client.get(f"/api/v1/checks/daily/{c.check_id}/detail", headers=auth_responder)
        assert resp.status_code == 200
        assert resp.json()["check_id"] == c.check_id

    def test_responder_cannot_see_others_check(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, performed_by="Someone Else")

        resp = client.get(f"/api/v1/checks/daily/{c.check_id}/detail", headers=auth_responder)
        assert resp.status_code == 403

    def test_supervisor_can_see_any_check(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, performed_by="Someone Else")

        resp = client.get(f"/api/v1/checks/daily/{c.check_id}/detail", headers=auth_supervisor)
        assert resp.status_code == 200

    def test_soft_deleted_check_returns_404(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Testing 404 on deleted check detail endpoint."},
            auth_supervisor,
        )

        resp = client.get(f"/api/v1/checks/daily/{c.check_id}/detail", headers=auth_supervisor)
        assert resp.status_code == 404

    def test_nonexistent_check_returns_404(self, client, auth_supervisor):
        resp = client.get("/api/v1/checks/daily/99999/detail", headers=auth_supervisor)
        assert resp.status_code == 404


# ── B-E2: Acknowledge check ────────────────────────────────────────────────────

class TestAcknowledgeCheck:
    def test_supervisor_can_acknowledge(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, check_status=CheckStatus.FAIL)

        resp = client.patch(
            f"/api/v1/checks/daily/{c.check_id}/acknowledge",
            json={"corrective_action": "Restocked all missing items from supply room."},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["corrective_action"] == "Restocked all missing items from supply room."
        assert data["reviewed_by"] is not None
        assert data["reviewed_at"] is not None

    def test_can_re_acknowledge(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, check_status=CheckStatus.FAIL)

        client.patch(
            f"/api/v1/checks/daily/{c.check_id}/acknowledge",
            json={"corrective_action": "First corrective action note recorded here."},
            headers=auth_supervisor,
        )
        resp = client.patch(
            f"/api/v1/checks/daily/{c.check_id}/acknowledge",
            json={"corrective_action": "Updated corrective action after further review."},
            headers=auth_supervisor,
        )
        assert resp.status_code == 200
        assert resp.json()["corrective_action"] == "Updated corrective action after further review."

    def test_corrective_action_too_short_returns_422(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        resp = client.patch(
            f"/api/v1/checks/daily/{c.check_id}/acknowledge",
            json={"corrective_action": "No"},
            headers=auth_supervisor,
        )
        assert resp.status_code == 422

    def test_responder_cannot_acknowledge(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        resp = client.patch(
            f"/api/v1/checks/daily/{c.check_id}/acknowledge",
            json={"corrective_action": "Responder attempting to acknowledge check record."},
            headers=auth_responder,
        )
        assert resp.status_code == 403

    def test_acknowledge_writes_audit_event(self, client, db, auth_supervisor):
        from ems_readykit.models.audit_event import AuditEvent
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id, check_status=CheckStatus.FAIL)

        client.patch(
            f"/api/v1/checks/daily/{c.check_id}/acknowledge",
            json={"corrective_action": "All shortages restocked and verified by supervisor."},
            headers=auth_supervisor,
        )
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "CHECK_ACKNOWLEDGED"
        ).first()
        assert audit is not None


# ── CH-B3: Soft-delete ─────────────────────────────────────────────────────────

class TestSoftDeleteCheck:
    def test_supervisor_can_soft_delete(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        resp = _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Duplicate check submitted in error by responder."},
            auth_supervisor,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_at"] is not None
        assert data["deleted_by"] is not None
        assert data["deletion_reason"] == "Duplicate check submitted in error by responder."

    def test_deletion_reason_too_short_returns_422(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        resp = _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Bad"},
            auth_supervisor,
        )
        assert resp.status_code == 422

    def test_double_delete_returns_409(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "First deletion of this check record for testing."},
            auth_supervisor,
        )
        resp = _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Attempting second deletion of same check record."},
            auth_supervisor,
        )
        assert resp.status_code == 409

    def test_responder_cannot_delete(self, client, db, auth_responder):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        resp = _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Responder attempting to delete check record here."},
            auth_responder,
        )
        assert resp.status_code == 403

    def test_soft_delete_writes_audit_event(self, client, db, auth_supervisor):
        from ems_readykit.models.audit_event import AuditEvent
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Check submitted for wrong vehicle by accident."},
            auth_supervisor,
        )
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "CHECK_SOFT_DELETED"
        ).first()
        assert audit is not None
        assert audit.severity == "WARNING"

    def test_deleted_check_hidden_from_normal_get(self, client, db, auth_supervisor):
        s = _station(db)
        v = _vehicle(db, s.station_id)
        c = _check(db, v.vehicle_id, s.station_id)

        _delete_with_body(
            client,
            f"/api/v1/checks/daily/{c.check_id}",
            {"deletion_reason": "Verifying check is hidden after soft deletion."},
            auth_supervisor,
        )
        resp = client.get(
            f"/api/v1/checks/daily/{c.check_id}",
            headers=auth_supervisor,
        )
        assert resp.status_code == 404
