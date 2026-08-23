"""
tests/test_check_export.py
F-5G3a — Compliance CSV export: GET /checks/daily/station/{id}/export

Covers RBAC, date-range validation (new 400-day cap, distinct from the
90-day cap on the interactive /checks/daily/station/{id} list endpoint),
entity filtering (whole_station vs specific vehicle/location IDs, including
that retired vehicles are still included under whole_station), soft-delete
and cross-station exclusion, exact CSV column values for both formats,
empty-result handling, controlled-substance-check inclusion (Detailed only)
including the UTC date-boundary correctness CLAUDE.md calls out elsewhere,
the CSV formula-injection guard, filename shape, and the audit event
written on every successful export.

Direct-ORM fixtures (station/vehicle/compartment/item/check/line-item) are
used throughout rather than posting through the check-submission API --
this suite needs precise control over field values (notes text, review
fields, check_date, deleted_at) to assert exact CSV output, not the
business-logic status computation the submission endpoint provides.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from ems_readykit.models import (
    Compartment,
    InventoryLocation,
    Item,
    ItemCategory,
    ItemCheckType,
    LocationType,
    Station,
    Vehicle,
    VehicleType,
)
from ems_readykit.models.audit_event import AuditEvent
from ems_readykit.models.check_line_item import CheckLineItem, LineItemStatus
from ems_readykit.models.controlled_substance_check import ControlledSubstanceCheck
from ems_readykit.models.daily_inventory_check import CheckStatus, DailyInventoryCheck
from ems_readykit.models.station_member import StationMember

BASE = "/api/v1/checks/daily"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def station(db, request):
    s = Station(
        name=f"Export Station [{request.node.name}]", address="1 Test Way", region="Test"
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def other_station(db, request):
    s = Station(
        name=f"Export Other Station [{request.node.name}]",
        address="2 Test Way",
        region="Test",
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def membership(db, station):
    for email, role in [
        ("test-supervisor@ems.local", "Supervisor"),
        ("test-administrator@ems.local", "Administrator"),
    ]:
        db.add(
            StationMember(
                station_id=station.station_id,
                user_id=email,
                role=role,
                assigned_by="test",
                active=True,
            )
        )
    db.flush()


def _vehicle(
    db: Session,
    station_id: int,
    *,
    vehicle_type: VehicleType = VehicleType.ALS,
    retired: bool = False,
) -> tuple[Vehicle, InventoryLocation]:
    v = Vehicle(
        station_id=station_id,
        vehicle_number=f"EXP-{_uid()}",
        vehicle_type=vehicle_type,
        active=not retired,
    )
    if retired:
        v.retired_at = datetime.now(timezone.utc)
        v.retired_by = "test-administrator@ems.local"
        v.retirement_reason = "Test retirement"
    db.add(v)
    db.flush()
    loc = InventoryLocation(
        location_type=LocationType.VEHICLE,
        station_id=station_id,
        vehicle_id=v.vehicle_id,
        label=f"Unit {v.vehicle_number}",
    )
    db.add(loc)
    db.flush()
    return v, loc


def _jump_bag(db: Session, station_id: int) -> InventoryLocation:
    loc = InventoryLocation(
        location_type=LocationType.JUMP_BAG,
        station_id=station_id,
        label=f"Jump Bag {_uid()}",
    )
    db.add(loc)
    db.flush()
    return loc


def _compartment(db: Session, location_id: int) -> Compartment:
    c = Compartment(
        location_id=location_id, name=f"Comp-{_uid()}", sort_order=1, active=True
    )
    db.add(c)
    db.flush()
    return c


def _item(db: Session, station_id: int, **kw) -> Item:
    defaults = {
        "name": f"Item-{_uid()}",
        "station_id": station_id,
        "category": ItemCategory.CONSUMABLE,
        "check_type": ItemCheckType.SUPPLY,
        "unit_of_measure": "each",
        "active": True,
    }
    defaults.update(kw)
    i = Item(**defaults)
    db.add(i)
    db.flush()
    return i


def _check(db: Session, *, station_id: int, **kw) -> DailyInventoryCheck:
    # performed_by deliberately does NOT default to "test-responder@ems.local"
    # (the auth_responder fixture's real identity) -- this endpoint calls
    # write_audit_event(), which commits, releasing the SAVEPOINT for the
    # rest of the pytest session (see CLAUDE.md's test-isolation notes). Any
    # row created here with that exact identity would permanently bleed into
    # other files' unscoped "my checks" queries for the rest of the run.
    defaults = {
        "vehicle_id": None,
        "location_id": None,
        "check_date": date.fromisoformat("2026-06-01"),
        "performed_by": "export-fixture-crew@ems.local",
        "timestamp": datetime.now(timezone.utc),
        "status": CheckStatus.PASS,
    }
    defaults.update(kw)
    if isinstance(defaults["check_date"], str):
        defaults["check_date"] = date.fromisoformat(defaults["check_date"])
    c = DailyInventoryCheck(station_id=station_id, **defaults)
    db.add(c)
    db.flush()
    return c


def _line_item(db: Session, *, check_id: int, compartment_id: int, item_id: int, **kw) -> CheckLineItem:
    defaults = {
        "quantity_found": 1,
        "quantity_needed": 1,
        "status": LineItemStatus.OK,
    }
    defaults.update(kw)
    li = CheckLineItem(check_id=check_id, compartment_id=compartment_id, item_id=item_id, **defaults)
    db.add(li)
    db.flush()
    return li


def _export(client, station_id, auth, **params):
    return client.get(f"{BASE}/station/{station_id}/export", params=params, headers=auth)


def _rows(resp) -> list:
    """Parse the CSV body into rows, stripping the intentional UTF-8 BOM prefix
    (added so Excel renders the file correctly) before parsing."""
    text = resp.text.lstrip("﻿")
    return list(csv.reader(io.StringIO(text)))


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class TestRBAC:
    def test_responder_forbidden(self, client, db, station, membership, auth_responder):
        resp = _export(
            client, station.station_id, auth_responder,
            **{"from": "2026-01-01", "to": "2026-01-31", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 403

    def test_non_member_supervisor_forbidden(self, client, db, other_station, auth_supervisor):
        resp = _export(
            client, other_station.station_id, auth_supervisor,
            **{"from": "2026-01-01", "to": "2026-01-31", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 403

    def test_member_supervisor_ok(self, client, db, station, membership, auth_supervisor):
        resp = _export(
            client, station.station_id, auth_supervisor,
            **{"from": "2026-01-01", "to": "2026-01-31", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 200

    def test_administrator_bypasses_membership(self, client, db, other_station, auth_admin):
        resp = _export(
            client, other_station.station_id, auth_admin,
            **{"from": "2026-01-01", "to": "2026-01-31", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 200

    def test_unknown_station_404(self, client, auth_admin):
        resp = _export(
            client, 999999, auth_admin,
            **{"from": "2026-01-01", "to": "2026-01-31", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_malformed_date_422(self, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "06/01/2026", "to": "2026-06-30", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 422

    def test_from_after_to_422(self, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-30", "to": "2026-06-01", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 422

    def test_missing_required_params_422(self, client, station, membership, auth_admin):
        resp = client.get(f"{BASE}/station/{station.station_id}/export", headers=auth_admin)
        assert resp.status_code == 422

    def test_exactly_400_days_ok(self, client, station, membership, auth_admin):
        to_d = date(2026, 6, 30)
        from_d = to_d - timedelta(days=400)
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": from_d.isoformat(), "to": to_d.isoformat(), "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 200

    def test_401_days_422(self, client, station, membership, auth_admin):
        to_d = date(2026, 6, 30)
        from_d = to_d - timedelta(days=401)
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": from_d.isoformat(), "to": to_d.isoformat(), "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 422

    def test_no_entities_selected_422(self, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-30", "format": "simplified", "whole_station": "false"},
        )
        assert resp.status_code == 422

    def test_invalid_format_422(self, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-30", "format": "csv", "whole_station": "true"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Entity filtering
# ---------------------------------------------------------------------------


class TestEntityFiltering:
    def test_whole_station_includes_retired_vehicle(self, db, client, station, membership, auth_admin):
        v_retired, _loc_retired = _vehicle(db, station.station_id, retired=True)
        _check(db, station_id=station.station_id, vehicle_id=v_retired.vehicle_id, performed_by="crew@ems.local")

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-01", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 200
        rows = _rows(resp)
        assert any(row and row[1] == "crew@ems.local" for row in rows[1:])

    def test_specific_vehicle_excludes_others(self, db, client, station, membership, auth_admin):
        v1, _ = _vehicle(db, station.station_id)
        v2, _ = _vehicle(db, station.station_id)
        _check(db, station_id=station.station_id, vehicle_id=v1.vehicle_id, performed_by="crew-one@ems.local")
        _check(db, station_id=station.station_id, vehicle_id=v2.vehicle_id, performed_by="crew-two@ems.local")

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-01", "format": "simplified", "vehicle_ids": [v1.vehicle_id]},
        )
        assert resp.status_code == 200
        rows = _rows(resp)
        performed_by_values = [row[1] for row in rows[1:] if row]
        assert "crew-one@ems.local" in performed_by_values
        assert "crew-two@ems.local" not in performed_by_values

    def test_jump_bag_filter(self, db, client, station, membership, auth_admin):
        jb = _jump_bag(db, station.station_id)
        _check(db, station_id=station.station_id, location_id=jb.location_id, performed_by="jumpbag-crew@ems.local")

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-01", "format": "simplified", "location_ids": [jb.location_id]},
        )
        assert resp.status_code == 200
        rows = _rows(resp)
        assert any(row and row[1] == "jumpbag-crew@ems.local" for row in rows[1:])


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


class TestExclusions:
    def test_soft_deleted_check_excluded(self, db, client, station, membership, auth_admin):
        v, _ = _vehicle(db, station.station_id)
        _check(
            db,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            performed_by="deleted-crew@ems.local",
            deleted_at=datetime.now(timezone.utc),
        )

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-01", "format": "simplified", "whole_station": "true"},
        )
        rows = _rows(resp)
        assert not any(row and len(row) > 1 and row[1] == "deleted-crew@ems.local" for row in rows[1:])

    def test_cross_station_isolation(self, db, client, station, other_station, membership, auth_admin):
        v_other, _ = _vehicle(db, other_station.station_id)
        _check(db, station_id=other_station.station_id, vehicle_id=v_other.vehicle_id, performed_by="other-station-crew@ems.local")

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-01", "format": "simplified", "whole_station": "true"},
        )
        rows = _rows(resp)
        assert not any(row and len(row) > 1 and row[1] == "other-station-crew@ems.local" for row in rows[1:])


# ---------------------------------------------------------------------------
# Simplified CSV shape
# ---------------------------------------------------------------------------


class TestSimplifiedCsv:
    def test_header_and_row_values(self, db, client, station, membership, auth_admin):
        v, _ = _vehicle(db, station.station_id, vehicle_type=VehicleType.BLS)
        _check(
            db,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            performed_by="simplified-crew@ems.local",
            status=CheckStatus.FAIL,
            check_date="2026-06-15",
        )

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-15", "to": "2026-06-15", "format": "simplified", "vehicle_ids": [v.vehicle_id]},
        )
        rows = _rows(resp)
        assert rows[0] == ["Check Date", "Performed By", "Subject", "Status", "Station"]
        data_row = rows[1]
        assert data_row[0] == "2026-06-15"
        assert data_row[1] == "simplified-crew@ems.local"
        assert data_row[2] == f"Unit {v.vehicle_number}"
        assert data_row[3] == "FAIL"
        assert data_row[4] == station.name

    def test_never_contains_cs_section(self, db, client, station, membership, auth_admin):
        v, _ = _vehicle(db, station.station_id, vehicle_type=VehicleType.ALS)
        db.add(
            ControlledSubstanceCheck(
                vehicle_id=v.vehicle_id,
                primary_signer="A",
                secondary_signer="B",
                timestamp=datetime.now(timezone.utc),
            )
        )
        db.flush()

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-01-01", "to": "2026-12-31", "format": "simplified", "vehicle_ids": [v.vehicle_id]},
        )
        assert "Controlled Substance" not in resp.text


# ---------------------------------------------------------------------------
# Detailed CSV shape
# ---------------------------------------------------------------------------


class TestDetailedCsv:
    def test_line_item_and_review_fields(self, db, client, station, membership, auth_admin):
        v, loc = _vehicle(db, station.station_id, vehicle_type=VehicleType.BLS)
        comp = _compartment(db, loc.location_id)
        item = _item(db, station.station_id, name="Gauze Test Item")
        check = _check(
            db,
            station_id=station.station_id,
            vehicle_id=v.vehicle_id,
            performed_by="detailed-crew@ems.local",
            status=CheckStatus.FAIL,
            check_date="2026-06-20",
            notes="Overall check notes",
            reviewed_by="supervisor@ems.local",
            reviewed_at=datetime.now(timezone.utc),
            corrective_action="Restocked from supply room",
        )
        _line_item(
            db,
            check_id=check.check_id,
            compartment_id=comp.compartment_id,
            item_id=item.item_id,
            status=LineItemStatus.MISSING,
            quantity_found=0,
            quantity_needed=2,
            notes="Was empty",
        )

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-20", "to": "2026-06-20", "format": "detailed", "vehicle_ids": [v.vehicle_id]},
        )
        rows = _rows(resp)
        assert rows[0] == ["Section: Daily Inventory Checks — Detailed"]
        header = rows[1]
        assert header == [
            "Check Date", "Performed By", "Subject", "Overall Check Status",
            "Item Name", "Check Type", "Line Item Status", "Quantity Found",
            "Quantity Needed", "Measurement Value", "Functional Pass", "Date Value",
            "Line Item Notes", "Check Notes", "Reviewed By", "Reviewed At", "Corrective Action",
        ]
        data_row = rows[2]
        assert data_row[0] == "2026-06-20"
        assert data_row[1] == "detailed-crew@ems.local"
        assert data_row[4] == "Gauze Test Item"
        assert data_row[6] == "MISSING"
        assert data_row[7] == "0"
        assert data_row[8] == "2"
        assert data_row[12] == "Was empty"
        assert data_row[13] == "Overall check notes"
        assert data_row[14] == "supervisor@ems.local"
        assert data_row[16] == "Restocked from supply room"

    def test_functional_pass_renders_yes_no(self, db, client, station, membership, auth_admin):
        v, loc = _vehicle(db, station.station_id)
        comp = _compartment(db, loc.location_id)
        item = _item(db, station.station_id, check_type=ItemCheckType.FUNCTIONAL)
        check = _check(db, station_id=station.station_id, vehicle_id=v.vehicle_id, check_date="2026-06-21")
        _line_item(
            db, check_id=check.check_id, compartment_id=comp.compartment_id,
            item_id=item.item_id, functional_pass=False,
        )

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-21", "to": "2026-06-21", "format": "detailed", "vehicle_ids": [v.vehicle_id]},
        )
        rows = _rows(resp)
        assert rows[2][10] == "No"


# ---------------------------------------------------------------------------
# Empty-result handling
# ---------------------------------------------------------------------------


class TestEmptyResults:
    def test_zero_matching_checks_returns_200_headers_only(self, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2020-01-01", "to": "2020-01-02", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 200
        rows = _rows(resp)
        assert rows[0] == ["Check Date", "Performed By", "Subject", "Status", "Station"]
        assert len(rows) == 1

    def test_detailed_cs_section_renders_even_when_empty(self, db, client, station, membership, auth_admin):
        v, loc = _vehicle(db, station.station_id, vehicle_type=VehicleType.ALS)
        comp = _compartment(db, loc.location_id)
        item = _item(db, station.station_id)
        check = _check(db, station_id=station.station_id, vehicle_id=v.vehicle_id, check_date="2026-06-22")
        _line_item(db, check_id=check.check_id, compartment_id=comp.compartment_id, item_id=item.item_id)

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-22", "to": "2026-06-22", "format": "detailed", "vehicle_ids": [v.vehicle_id]},
        )
        assert "Controlled Substance Checks" in resp.text
        rows = _rows(resp)
        cs_header_idx = rows.index(["Section: Controlled Substance Checks (ALS Drug Bag)"])
        assert rows[cs_header_idx + 1] == [
            "Vehicle", "Timestamp (UTC)", "Primary Signer", "Secondary Signer",
            "Discrepancy Flag", "Notes",
        ]
        # No data rows follow -- either EOF or a fresh blank/section line, never a data row.
        assert len(rows) == cs_header_idx + 2


# ---------------------------------------------------------------------------
# Controlled-substance checks
# ---------------------------------------------------------------------------


class TestControlledSubstanceChecks:
    def test_included_with_correct_fields(self, db, client, station, membership, auth_admin):
        v, loc = _vehicle(db, station.station_id, vehicle_type=VehicleType.ALS)
        comp = _compartment(db, loc.location_id)
        item = _item(db, station.station_id)
        check = _check(db, station_id=station.station_id, vehicle_id=v.vehicle_id, check_date="2026-06-23")
        _line_item(db, check_id=check.check_id, compartment_id=comp.compartment_id, item_id=item.item_id)

        cs = ControlledSubstanceCheck(
            vehicle_id=v.vehicle_id,
            primary_signer="Alice Primary",
            secondary_signer="Bob Secondary",
            timestamp=datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc),
            discrepancy_flag=True,
            notes="Count matched after recount",
        )
        db.add(cs)
        db.flush()

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-23", "to": "2026-06-23", "format": "detailed", "vehicle_ids": [v.vehicle_id]},
        )
        rows = _rows(resp)
        cs_header_idx = rows.index(["Section: Controlled Substance Checks (ALS Drug Bag)"])
        data_row = rows[cs_header_idx + 2]
        assert data_row[0] == v.vehicle_number
        assert data_row[2] == "Alice Primary"
        assert data_row[3] == "Bob Secondary"
        assert data_row[4] == "Yes"
        assert data_row[5] == "Count matched after recount"

    def test_utc_date_boundary(self, db, client, station, membership, auth_admin):
        """
        A CS check timestamped at 23:30 UTC on the last requested day must be
        included; one at 00:30 UTC the day AFTER the range must be excluded.
        Uses explicit UTC instants, not local time, per CLAUDE.md's boundary
        convention.
        """
        v, loc = _vehicle(db, station.station_id, vehicle_type=VehicleType.ALS)
        _compartment(db, loc.location_id)

        in_range = ControlledSubstanceCheck(
            vehicle_id=v.vehicle_id,
            primary_signer="A",
            secondary_signer="B",
            timestamp=datetime(2026, 6, 24, 23, 30, tzinfo=timezone.utc),
        )
        out_of_range = ControlledSubstanceCheck(
            vehicle_id=v.vehicle_id,
            primary_signer="C",
            secondary_signer="D",
            timestamp=datetime(2026, 6, 25, 0, 30, tzinfo=timezone.utc),
        )
        db.add_all([in_range, out_of_range])
        db.flush()

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-24", "to": "2026-06-24", "format": "detailed", "vehicle_ids": [v.vehicle_id]},
        )
        rows = _rows(resp)
        cs_header_idx = rows.index(["Section: Controlled Substance Checks (ALS Drug Bag)"])
        cs_data_rows = rows[cs_header_idx + 2 :]
        primary_signers = [row[2] for row in cs_data_rows if row]
        assert primary_signers == ["A"]

    def test_station_scoping_via_vehicle_join(self, db, client, station, other_station, membership, auth_admin):
        v_other, _ = _vehicle(db, other_station.station_id, vehicle_type=VehicleType.ALS)
        db.add(
            ControlledSubstanceCheck(
                vehicle_id=v_other.vehicle_id,
                primary_signer="Outside",
                secondary_signer="Station",
                timestamp=datetime(2026, 6, 26, 12, 0, tzinfo=timezone.utc),
            )
        )
        db.flush()
        v_mine, _ = _vehicle(db, station.station_id, vehicle_type=VehicleType.ALS)

        resp = _export(
            client, station.station_id, auth_admin,
            **{
                "from": "2026-06-26", "to": "2026-06-26", "format": "detailed",
                "vehicle_ids": [v_mine.vehicle_id, v_other.vehicle_id],
            },
        )
        assert "Outside" not in resp.text


# ---------------------------------------------------------------------------
# Security: CSV formula-injection guard
# ---------------------------------------------------------------------------


class TestCsvInjectionGuard:
    def test_leading_equals_note_is_neutralized(self, db, client, station, membership, auth_admin):
        v, loc = _vehicle(db, station.station_id)
        comp = _compartment(db, loc.location_id)
        item = _item(db, station.station_id)
        check = _check(
            db, station_id=station.station_id, vehicle_id=v.vehicle_id,
            check_date="2026-06-27", corrective_action="=cmd|'/c calc'!A1",
        )
        _line_item(db, check_id=check.check_id, compartment_id=comp.compartment_id, item_id=item.item_id)

        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-27", "to": "2026-06-27", "format": "detailed", "vehicle_ids": [v.vehicle_id]},
        )
        rows = _rows(resp)
        assert rows[2][16] == "'=cmd|'/c calc'!A1"


# ---------------------------------------------------------------------------
# Filename and audit event
# ---------------------------------------------------------------------------


class TestFilenameAndAudit:
    def test_filename_pattern(self, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-30", "format": "detailed", "whole_station": "true"},
        )
        disposition = resp.headers["content-disposition"]
        assert "compliance_detailed_2026-06-01_to_2026-06-30.csv" in disposition

    def test_audit_event_written(self, db, client, station, membership, auth_admin):
        resp = _export(
            client, station.station_id, auth_admin,
            **{"from": "2026-06-01", "to": "2026-06-30", "format": "simplified", "whole_station": "true"},
        )
        assert resp.status_code == 200
        event = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.action == "CHECK_HISTORY_EXPORTED",
                AuditEvent.station_id == station.station_id,
            )
            .first()
        )
        assert event is not None
        assert event.entity_id == str(station.station_id)
