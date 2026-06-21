# EMS ReadyKit — Completed Items
# Last updated: 2026-06-20 (Session AI: ITM-4 done — seed.py rewritten with BASE_ITEM_SEED,
# station_id on all items, Newberg full par levels, other stations catalog only.
# 484/484 expected after `alembic upgrade head && python seed.py`.)
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, AA, AB, AC, AD, AE, AF, AG, AH, AI
# Active backlog -> docs/backlog.md

---

## Session AI — ITM-4: Rewrite `seed.py` with `BASE_ITEM_SEED` + station-scoped items (2026-06-20)

**ITM-4 complete.** `seed.py` is fully rewritten. The 32 `test_seed_integrity` failures that
opened with ITM-1's `station_id` NOT NULL constraint are resolved.

**`BASE_ITEM_SEED`** (~100+ entries across 7 `category_group` buckets):
`Airway & Respiratory`, `Wound Care & Trauma Supplies`, `PPE & Cleaning`,
`Diagnostic & Monitoring Equipment`, `Medications & Controlled Substances`,
`Documents, Linens & Patient Comfort`, `Vehicle Operations`. One canonical entry per
real-world item. Merged items from ITM-2's finalized merge table: "Gauze, 3x3" replaces
Gauze 3x3 PC18 + Gauze 3x3 JB + Gauze Pads 3x3 JB; "Stethoscope" replaces all four
location-suffixed variants; "LUCAS Device" merges LUCAS Device + LUCAS Device Ready Check;
"Fire Extinguisher" replaces "Fire Extinguisher UL Listed" (FUNCTIONAL → SUPPLY, Jennifer-confirmed);
new item "Stretcher Battery Date of Last Charge" (DATE_RECORD, recurrence=90); and so on for
all items in ITM-2's merge table.

**`get_or_create_item(db, *, station_id, name, ...):`** `station_id` is now required.
Query now scoped to `(station_id, name)` — matching the `uq_items_station_name` constraint
from migration 0028. On re-seed of an existing DB, mutable fields (check_type, recurrence_days,
measurement_min/max, etc.) are updated in-place; the item row is never recreated.

**`seed_station_catalog(db, station_id)`:** New helper. Iterates `BASE_ITEM_SEED` and creates
each item for the given station. Returns count of newly created items. Every station gets its
own copy of the canonical catalog; items are station-scoped from first write.

**`build_supply_room(db, loc, station_id)`:** Now takes `station_id`. Item lookups for test
stock lots are scoped to `(item_name, station_id)` — no cross-station bleed-through.

**`build_ambulance_inventory(db, loc, station_id, is_als)`** and **`build_jump_bag(db, jb, station_id)`:**
All `get_or_create_item()` calls now pass `station_id`. All location-suffixed names replaced with
canonical names. O2 PSI thresholds corrected per ITM-2: Stretcher O2 PSI and Jump Bag O2 PSI
`measurement_minimum=200.0`, `measurement_maximum=500.0` (small tank); `priority_question` updated
to "above 200 PSI?". On-Board O2 PSI unchanged (large tank, 500–2200). LUCAS Device Ready Check
removed — merged into "LUCAS Device" as one FUNCTIONAL priority item (`priority_check=True`,
`priority_question="LUCAS shows READY?"`). "Fire Extinguisher UL Listed" (FUNCTIONAL) removed from
Truck Operations; replaced with canonical "Fire Extinguisher" (SUPPLY) presence check.

**Seeding strategy in `seed(db)`:**
- **Newberg Township Station 1:** `seed_station_catalog` → `build_supply_room` → `build_ambulance_inventory(is_als=False)` → `build_jump_bag`. Full par levels from real 712 / jump bag inventory forms.
- **Marcellus Township Station 1:** `seed_station_catalog` + `build_supply_room` only. No par levels — assigned via admin UI (ITM-6).
- **Newberg Training Station (orange):** `seed_station_catalog` + `build_supply_room`. Training Unit A/B + Jump Bag A/B created (no par levels).
- **⚠ TEST STATION:** `seed_station_catalog` + `build_supply_room` + 7 `[TEST]`-prefixed dev items. No par levels.

**Removed from `seed.py`:** `purge_stale_par_levels()`, `purge_wrong_drug_cabinets()` (fresh DB,
not upgrade path); `build_training_ambulance()`, `build_training_jump_bag()`, `build_test_inventory()`
(replaced by catalog-only seeding + Training handled in `seed_training.py`); SR-SEED1
post-processing block (station_supply now baked into `BASE_ITEM_SEED`).

**Module docstring updated:** removed "item catalog is SHARED across all stations" line.

**`test_seed_integrity.py` — 6 test changes:**
1. `test_lucas_device_ready_check_in_pc8_is_functional` → renamed to `test_lucas_device_in_pc8_is_functional_priority` (verifies LUCAS Device has priority_check=True + priority_question)
2. `test_pc8_has_all_seven_items` → `test_pc8_has_all_six_items` (removes "LUCAS Device Ready Check" from expected list)
3. `test_lucas_not_in_supply_room` — removed "LUCAS Device Ready Check" from loop
4. `test_stretcher_o2_psi_measurement_minimum` — assertion changed 500.0 → 200.0
5. `test_jump_bag_o2_psi_measurement_minimum` — assertion changed 500.0 → 200.0
6. `test_truck_operations_has_functional_items` — threshold changed `>= 10` → `>= 9`

**Test result:** 484/484 expected after `cd app; Remove-Item ems_readykit_dev.db; alembic upgrade head; python seed.py; pytest`.

**Migration 0028 bug fix (discovered during reseed):** The original migration used
`alter_column("name", unique=False)` inside Alembic batch mode, expecting it to drop
the old global `UNIQUE` on `items.name`. This silently failed: Alembic batch mode
recreates the table by reading its DDL from `sqlite_master`, and that DDL retained
the inline `UNIQUE` keyword from migration 0001 through every subsequent batch
recreation (migrations 0003, 0017). SQLAlchemy's inspector also filters out
`sqlite_autoindex_*` names so the constraint couldn't be found or dropped through
the ORM layer. Fixed by replacing the batch alter with explicit raw SQL
(`CREATE TABLE _items_new (..., UNIQUE (station_id, name))` / INSERT SELECT /
DROP / RENAME) — no reflection, no DDL inheritance, exactly the schema we want.

**Files changed:**
- `app/seed.py` — full rewrite (ITM-4)
- `app/tests/test_seed_integrity.py` — 6 test corrections
- `app/alembic/versions/0028_items_station_id.py` — rewritten with raw SQL to reliably drop the old global unique

---

## Session AH — ITM-3: `category_group` on Items (2026-06-20)

**ITM-3 complete.** Cabinet grouping field added to the `Item` model.

**Migration 0029:** `items.category_group` VARCHAR(100) nullable added via Alembic batch
mode. No data migration needed — column is nullable; values will be populated by the
ITM-4 seed rewrite.

**Model change (`models/item.py`):** `category_group: Mapped[Optional[str]]` column added
between `station_id` and `unit_of_measure`. Seven valid values: "Airway & Respiratory",
"Wound Care & Trauma Supplies", "PPE & Cleaning", "Diagnostic & Monitoring Equipment",
"Medications & Controlled Substances", "Documents, Linens & Patient Comfort",
"Vehicle Operations".

**Schema change (`schemas/item.py`):** `category_group: Optional[str]` added to `ItemBase`
with `max_length=100`. Inherited by `ItemCreate` and `ItemRead` — field round-trips through
all item endpoints with no existing call sites broken.

**Test result:** 452 passed, 32 failed (all `test_seed_integrity` — expected, unchanged).

**Files changed:**
- `app/ems_readykit/models/item.py` — `category_group` Mapped column
- `app/ems_readykit/schemas/item.py` — `category_group` Optional field in `ItemBase`
- `app/alembic/versions/0029_items_category_group.py` — new migration

---

## Session AG — ITM-1: `station_id` on Items, Per-Station Uniqueness, Supply Catalog Scoping (2026-06-20)

**ITM-1 complete.** Items are now station-scoped at the model and database level.

**Migration 0028:** `items.station_id` FK (NOT NULL → stations table) added via Alembic
batch mode. Global `uq_items_name` unique constraint dropped; replaced with
`uq_items_station_name (station_id, name)` — items from different stations may share a
name, but the same station cannot have two identically-named items.

**Supply catalog scoped to station:** `GET /inventory/supply-catalog?station_id=X` was
returning items from ALL stations (missing `Item.station_id == station_id` filter in
`inventory.py::get_supply_catalog`). Fixed by adding that filter as the first condition.
Also fixed a related `on_hand == 0` symptom — multiple same-named items across stations
caused the endpoint to return the wrong station's item (with no stock) when the test suite
created a second station.

**Test suite updated throughout:** `ItemCreate` schema now requires `station_id: int` — 30+
call sites in `test_routers.py`, `test_persona_admin.py`, `test_persona_supervisor.py` updated
to create a station first then pass its `station_id`. Two supply room test fixes: unscoped
`filter_by(name=…).first()` replaced with direct fixture reference to avoid cross-station
item lookup. `TestInventoryEndpoints::test_create_stock_lot_invalid_location_returns_404`
rewritten to use `_setup_loc_and_item` helper (no longer creates an item inline without a station).

**Test result:** 452 passed, 32 failed (all `test_seed_integrity` — expected, `seed.py` has
not been updated for ITM-4 yet; the `seeded_db` fixture connects to a dev DB whose items
still use the old global catalog structure).

**Files changed:**
- `app/ems_readykit/models/item.py` — `station_id` FK + `UniqueConstraint`
- `app/alembic/versions/0028_items_station_id.py` — new migration
- `app/ems_readykit/routers/inventory.py` — supply catalog station filter
- `app/tests/test_routers.py` — station_id in all item creation calls; station fixture; _setup helpers
- `app/tests/test_persona_admin.py` — station creation before item creation in two tests
- `app/tests/test_persona_supervisor.py` — added `auth_admin` param; station creation in boundary test
- `app/tests/test_supply_room.py` — fixed unscoped item lookup in functional exclusion test

---

## Session AF — Compliance Calendar Fixes + PAR-B1 Reactivation + Audit Test Timezone Bug (2026-06-19)

Three frontend/UX bugs found by Jennifer in UAT, plus a backend test-suite failure
that took three diagnostic passes (across two root causes) to fully resolve.

**1. Compliance Dashboard showing retired vehicles** (calendar + today list). Root
cause: `GET /stations/{id}/vehicles` returns ALL vehicles (active + retired) unless
`active=true` is explicitly passed; nothing downstream filtered `retired_at`. Fix:
`supervisorApi.getTodayCompliance` now filters `!v.retired_at` at the source
(`frontend/src/modules/supervisor/api/supervisorApi.js`), with defensive
`!v.retired_at` checks also added in `index.jsx` and `ComplianceCalendar.jsx`,
matching the documented BUG-AD1 convention.

**2. Jump bag missing from Compliance Calendar month view; Station Supplies Count
missing entirely from the calendar.** `ComplianceCalendar.jsx` rewritten: week view =
active (non-retired) vehicles + jump bags only (Station Supply Room intentionally
excluded — wasted space at weekly cadence per Jennifer's direction). Month view =
combined vehicle/jump-bag picker + grid, plus a month-only "Station Supplies Count"
reminder strip (new `supervisorApi.getSupplyRoomLocation`, excludes a retired supply
room via `!loc.retired_at` check after fetch since `GET /stations/{id}/supply-room`
has no server-side retired filter).

**3. PAR-B1 — "This item is already assigned to this compartment" on re-add after
removal; check wizard Step 3 stuck on a removed item.** Root cause:
`ParLevel.uq_par_item_compartment (item_id, compartment_id)` unique constraint has no
concept of `active`. Soft-deactivating a par level (Remove) leaves a row occupying
that slot; re-adding the same item to the same compartment always hit the
`IntegrityError` → 409 fallback even with no active duplicate present. Fixed in both
creation entry points — reactivate the matching inactive row (clear
`deactivated_at`/`deactivation_reason`, apply new min/max) instead of inserting a
duplicate, preserving the original `par_id` and its history:
- `app/ems_readykit/routers/admin_items.py` :: `assign_item_to_compartment`
  (`POST /admin/items/{id}/assign` — the actual UI path)
- `app/ems_readykit/routers/inventory.py` :: `create_par_level`
  (`POST /inventory/par-levels` — not currently called from any frontend UI, fixed
  for consistency since it has the identical flaw)

New test file: `app/tests/test_par_level_reactivation.py`.

**4. Backend test suite — two separate root causes found across the session, both
on the test side, not the application side:**

*First pass:* `test_audit_from_date_tomorrow_returns_empty` and
`test_audit_to_date_yesterday_returns_empty` were asserting `== []` against the
**entire, unfiltered** `GET /audit` endpoint. Every route handler in this app calls
`db.commit()`, which releases the active SAVEPOINT — committed rows are never rolled
back between tests within a pytest session (documented behavior). With 480+ tests in
the suite, many of which write audit events, the global audit table legitimately had
hundreds of unrelated rows in it by the time these two tests ran. Fixed by scoping
both tests to a station they create themselves, matching the pattern their siblings
`test_list_audit_events_filter_by_severity`/`_by_action` already used.

A first attempt at this fix incorrectly suspected `routers/audit.py`'s naive-vs-aware
datetime comparison (`DateTime(timezone=True)` on SQLite). This was verified WRONG
via isolated repro against the pinned SQLAlchemy version (2.0.30) — the comparison
logic was never actually broken. That change was made and explicitly reverted before
the station-scoping fix above was applied instead.

*Second pass (new failure on a fresh run, after the station-scoping fix landed):*
`test_audit_from_date_tomorrow_returns_empty` still failed — but now genuinely scoped
to its own station, so this was new evidence, not the same bug recurring. The full
traceback showed the test's own freshly-written audit event being returned despite
querying `from_date=<tomorrow>`. Root cause: the test computed `tomorrow` from local
wall-clock `date.today()`, while `AuditEvent.timestamp` is always written as
`datetime.now(timezone.utc)` (`core/audit.py`). The captured log line on the failing
run showed local time `20:29:35` with `from_date=2026-06-20` — at US Eastern evening
hours, UTC has already rolled to the next calendar day, so the event's actual UTC
timestamp satisfied `>= from_date` and was incorrectly included. This is a test-data
bug (wrong clock for the boundary), not a defect in `routers/audit.py`'s comparison
logic (left untouched both times, confirmed unmodified throughout the session). Fixed
by computing `tomorrow`/`yesterday` from `datetime.now(timezone.utc).date()` instead
of local `date.today()` in both tests.

**Dependency fix (treated as a separate quick fix, not part of this session's
backlog):** GitHub Actions' `pip-audit` CI gate flagged `pydantic-settings==2.14.1`
(GHSA-4xgf-cpjx-pc3j); bumped to `2.14.2` in `app/requirements.txt`. Unrelated to the
audit-test timezone fix above — pure dependency patch bump, no code changes.

**Same-day UAT follow-up (BUG-AF2):** after redeploying the above, Jennifer found the
Station Supplies Count reminder showed "no count on record" for a real count
completed the day before, and tapping it no longer opened the check. Root cause:
this session's calendar fix had widened the reminder's lookback to 730 days through
`getComplianceRange` (`GET /checks/daily/station/{id}`), which caps its date range at
90 days server-side and 422s above that — every request was silently failing,
`useApi` correctly nulled out the data on error, and the reminder rendered as if
nothing had ever been counted, with no visible error. Fixed by switching the
reminder's data source to `GET /checks/daily/location/{location_id}` (new
`supervisorApi.getLocationCheckHistory`), which is location-scoped and has no
date-range limit at all — the right tool for "most recent check ever," which a
range-bounded endpoint was never going to support no matter how wide the window.
Display text and click target both now read from this single fetch, so they can't
disagree again. Also added a visible error state (`.cal__supply-reminder--error`)
instead of silently looking empty if this fetch ever fails for a different reason.

**Verified:** `cd app; pytest` (484/484), `cd app; ruff check .`, and
`cd app; black --check .` all confirmed green by Jennifer. Deployed to Azure and
confirmed live, including the same-day BUG-AF2 follow-up redeploy.

| # | Item | Completed |
|---|------|-----------|
| CAL-AF1 | Compliance Dashboard/Calendar — retired vehicles filtered out at source (supervisorApi.getTodayCompliance) plus defensive checks | 2026-06-19 |
| CAL-AF2 | ComplianceCalendar rewritten — jump bags in month view; Station Supplies Count reminder strip added | 2026-06-19 |
| PAR-B1 | Par-level reactivation on re-add after removal — assign_item_to_compartment + create_par_level reactivate inactive rows instead of erroring; new test_par_level_reactivation.py | 2026-06-19 |
| AUDIT-AF1 | test_audit_from_date_tomorrow_returns_empty / test_audit_to_date_yesterday_returns_empty scoped to a station the test creates (fixed global-table pollution) | 2026-06-19 |
| AUDIT-AF2 | Same two tests' tomorrow/yesterday boundary computed from UTC today (datetime.now(timezone.utc).date()) instead of local date.today() — fixed a local/UTC day-boundary mismatch found on a later run | 2026-06-19 |
| SEC-AF1 | pydantic-settings 2.14.1 → 2.14.2 (GHSA-4xgf-cpjx-pc3j); quick fix, not part of Session AF backlog proper | 2026-06-19 |
| BUG-AF2 | Station Supplies Count reminder data-source bug — switched to getLocationCheckHistory (unbounded, location-scoped) instead of getComplianceRange (90-day-capped, was 422ing silently); added visible error state | 2026-06-19 |

---

## Changelog Archive — Sessions Z through AF (consolidated version history)
*Moved here 2026-06-20 from backlog.md's version-history footer to keep the active
backlog small. This is a compressed cross-reference, not a replacement for the full
session write-ups above — those remain authoritative for technical detail.*

- **v2.07 (2026-06-19):** BUG-AF2 fixed and closed — see Session AF write-up above.
- **v2.06 (2026-06-19):** Session AF closed — pytest 484/484, ruff, black all green;
  deployed and confirmed live. pydantic-settings dependency bump included.
- **v2.05 (2026-06-19):** Session AF continued — audit date-range test fix, second
  pass (UTC vs local day boundary) — see Session AF write-up above.
- **v2.04 (2026-06-19):** Session AF in progress (not yet closed) — three UAT bugs
  found and fixed; PAR-B1 backend fix applied; test suite not yet confirmed green
  at this point in the session.
- **v2.03 (2026-06-19):** Session AE closed and verified — pytest + npm test green;
  `_session_AE_removed/` staging folder deleted; deployed and confirmed live.
- **v2.02 (2026-06-19):** Session AE closed — MERGE-1 member management
  consolidation — see Session AE write-up above.
- **v2.01 (2026-06-19):** Close-out note for a missing-files incident caused by a
  quota interruption; confirmed all files restored and present. LAUNCH-OPS5 marked
  in-progress (Jennifer actively walking it).
- **v2.00 (2026-06-19):** Session AD closed — BUG-AD1 retired-vehicle leak fix — see
  Session AD write-up above.
- **v1.99 (2026-06-19):** Session AC closed — LAUNCH-OPS9 email alignment check —
  see Session AC write-up above.
- **v1.98 (2026-06-18):** Session AB closed — training station, security patches,
  Settings CSS fixes — see Session AB write-up above. All launch gates met at this
  point (later reopened 2026-06-20 for ITM-1..8).
- **v1.97 (2026-06-14):** Help screen added as LAUNCH-F1 (Session AA).
- **v1.96 (2026-06-14):** Session Z closed, ruff fixes, published to Azure.
- **v1.95 (2026-06-14):** Session Z — ACC-B6/B7/B8 complete, migration 0027,
  multi-role switching — see Session Z write-up below.

---

## Session AE — Member Management Consolidation (MERGE-1) (2026-06-19)

Jennifer reported that Station Administration → Members and Settings → Team Members
were two overlapping, confusing screens, and that removing a member in Station
Administration threw `"Input should be a valid integer, unable to parse string as
an integer"`.

**Root cause:** the frontend had two independent member-CRUD implementations hitting
the same backend routes:
- `modules/admin/api/adminApi.js` — old, broken. Called
  `DELETE /stations/{id}/members/{userId}` and the equivalent PATCH using a
  `user_id` (email string). This was correct before ACC-B7 (Session Z), but ACC-B7
  changed `station_members.py`'s PATCH/DELETE routes to take `member_id` (an integer
  primary key) so a person could hold multiple roles as separate rows. `adminApi.js`
  was never updated to match, so every removal sent a string where Pydantic expected
  an int.
- `modules/settings/api/membersApi.js` — correct, already `member_id`-based, with
  fuller functionality (multi-role grouping by person, edit name, CSV import) than
  the admin module's flat-list version.

No backend changes were needed — `station_members.py` was already correct.

**Fix:** consolidated to one screen and one API module:
- `MemberManagementSection.jsx`, `EmailAlignmentSection.jsx`, and `membersApi.js`
  moved from `modules/settings/` to `modules/admin/`.
- `modules/admin/components/MembersScreen.jsx` rewritten to wrap them (replacing the
  old `MemberList.jsx` + `AddMemberForm.jsx` pair, retired).
- The broken `getStationMembers`/`addMember`/`updateMember`/`removeMember` functions
  removed from `adminApi.js`.
- `modules/settings/index.jsx` no longer renders any member UI — Settings is now
  exclusively admin-only station/vehicle configuration (check workflow toggle,
  station/vehicle/location retirement).
- CSS: `.settings-section`, `.settings-row`, `.badge`, `.member-*`, and
  `.email-alignment__*` classes moved from `settings.css` to `index.css` since they
  became genuinely cross-module (same pattern already used for `.item-combobox`
  and `.csv-import`).
- Supervisors can now manage their own station's members (add, edit name, add
  additional roles, CSV import) without Administrator access — this was already
  true of the underlying SUPERVISOR_PLUS-gated endpoints; only the split UI was
  obscuring it. The Email Alignment Check stays Admin-only within the same screen.

Answering Jennifer's question about what removal actually does: removing a member
in the (working) Settings screen only deactivated that one role row
(`member.active = False` on that `member_id`) — it never deleted the person. If
they held other roles, those were untouched; if it was their only role, they lost
station access but the row persisted, soft-deleted, for audit history.

Six superseded files (old `MemberList.jsx`, `AddMemberForm.jsx`, and the pre-move
copies of `MemberManagementSection.jsx`, `EmailAlignmentSection.jsx`, `membersApi.js`,
`EmailAlignmentSection.test.jsx` from `settings/`) were staged in a
`_session_AE_removed/` folder since the filesystem tooling available had no delete
operation — confirmed deleted by Jennifer after review.

**Verified:** `cd app; pytest` passing (468+ baseline unchanged — no backend changes),
`cd frontend; npm test` passing (`EmailAlignmentSection.test.jsx` moved cleanly
alongside its component), deployed to Azure and confirmed live.

| # | Item | Completed |
|---|------|-----------|
| MERGE-1 | Member management consolidated from two screens into Station Administration -> Members; fixed broken member_id/user_id mismatch in adminApi.js; Settings narrowed to admin-only config; pytest + npm test green; deployed to Azure | 2026-06-19 |

---

## Session AD — Retired Vehicle Leak Fix (2026-06-19)

Found by Jennifer during LAUNCH-OPS5/6 walkthroughs: after retiring the "TEST UAT"
vehicle from Settings, it still appeared in Admin → Vehicles with "Show out-of-service
vehicles" unchecked, with a working "Return to Service" button.

Root cause: `active` and `retired_at` are two independent fields on the Vehicle model
(documented in CLAUDE.md as `v.active === true && !v.retired_at`). Retiring a vehicle
sets `active = False` as a side effect, but several frontend call sites only ever
checked `active` and never `retired_at` directly -- meaning the "no longer in active
service" signal worked by coincidence, not by design, and didn't distinguish a
permanently retired vehicle from a genuinely temporary out-of-service one. The retire
endpoint itself (`PATCH /vehicles/{id}/retire`) was correct the whole time; this was
purely a frontend display/action-gating bug.

Four call sites patched:
- `admin/components/VehiclesScreen.jsx` -- screen-level filter excluded `retired_at`
  rows outright (regardless of the "Show out-of-service" toggle); `VehicleAdminCard`
  now shows a "Retired" badge and the retirement reason instead of editable fields,
  Return to Service, or compartment edit controls.
- `vehicles/index.jsx` (V&E Status) + `vehicles/components/VehicleCard.jsx` -- same
  screen-level exclusion; card now shows "Retired" badge instead of "Out of Service"
  and hides Report an Issue / Mark Out of Service / Return to Service entirely.
- `pages/HomePage.jsx` -- `useStationIssues` excluded retired vehicles before
  fetching repair requests, so old repair history on a retired vehicle can no longer
  trigger the home screen's "Unresolved Issue" badge.
- `check-wizard/components/Step1Vehicle.jsx` -- defensive fix only (this path was
  already safe because the server-side `active=true` filter combined with
  retirement's `active=False` side effect happened to exclude retired vehicles), but
  now checks `retired_at` directly via a shared `isCheckableVehicle()` helper rather
  than relying on that side effect continuing to hold.

`usage-log/index.jsx` already filtered correctly (`v.active === true && !v.retired_at`)
and served as the reference pattern for the fix.

4 new/updated test files: `VehicleCard.test.jsx` (4 new regression cases),
`VehiclesScreen.test.jsx` (new file, 3 cases -- this screen had no test coverage
before, which is how the bug shipped unnoticed).

| # | Item | Completed |
|---|------|-----------|
| BUG-AD1 | Retired vehicles excluded from VehiclesScreen, V&E Status, HomePage issue badge, check wizard picker; 7 new frontend tests | 2026-06-19 |

---

## Session AC — Email Alignment Diagnostic + Settings UI (2026-06-19)

LAUNCH-OPS9 was the one remaining engineering item on the post-launch operational list;
everything else there (priority items config, physical stock counts, team member CSV
import, chief/volunteer walkthroughs) is the EMS chief's job, not engineering, and was
handed off as a walkthrough checklist instead.

Built as an on-demand Admin diagnostic rather than a startup-time check, since
StationMember rows can be added or imported at any time after the app is already
running -- a one-time startup scan would miss anything added later. `GET
/admin/email-alignment-check` scans StationMember rows and flags any whose `user_id`
doesn't look like a valid email (blank, contains whitespace, missing `@`/domain, or
not lowercase), which is the standard symptom of an admin typing a display name into
the email field during manual add or CSV import. Read-only; never modifies data.
Optional `station_id` filter; `include_inactive` to also scan soft-deleted rows.
Added to `admin_stations.py` (Admin-only, alongside the other admin diagnostics like
`/admin/retired`) rather than a new router. 12 new tests in `test_email_alignment.py`.

Follow-up same session: wired a "Run Check" button into Settings (Admin-only section,
`EmailAlignmentSection.jsx`, placed above StationManagementSection). On a flagged
result, an Admin can pick recipients from existing Administrators/Supervisors at the
station (excluding anyone who is themselves flagged, since their address may not be
reachable) or type in additional emails, then draft a notification email. No email
account is connected in this environment, so the draft opens via a `mailto:` link
in the Admin's own mail app rather than sending automatically. New CSS block added
to `settings.css` (`.email-alignment__*`), reusing existing color tokens. 17 new
frontend tests in `EmailAlignmentSection.test.jsx`.

(Session AE later moved `EmailAlignmentSection.jsx` and its test file from
`settings/` to `admin/` as part of the member-management consolidation — same
behavior, new home.)

| # | Item | Completed |
|---|------|-----------|
| LAUNCH-OPS9 | `GET /admin/email-alignment-check` — flags malformed StationMember.user_id values; Admin only; 12 tests | 2026-06-19 |
| LAUNCH-OPS9-UI | Settings → Email Alignment Check section: Run Check button, flagged-issue list, recipient picker, draft email via mailto; 17 frontend tests | 2026-06-19 |

---

## Session AB — Training Station + Security + Settings Polish (2026-06-18)

Training station added as a permanent safe playground for crew training — orange (#e65100)
so it is immediately distinct from the real blue stations. Two BLS ambulances (Training Unit A/B)
and two jump bags (Training Jump Bag A/B) with ~1/3 of Unit 712's inventory. All 6 check types
are represented including AED + LUCAS priority items, O2 PSI measurement, AED pads expiry,
and requires_full_check compartments (Truck Operations, Under Hood). A training check takes
~5 minutes vs 20 for Unit 712.

Training seed split into a standalone `seed_training.py` called by `startup.sh` on every deploy
— including production — so the training station is automatically restored after any database
teardown without manual intervention. The main `seed.py` operational guard remains in place.

Six pip-audit CVEs resolved by bumping starlette (1.1.0→1.3.1), python-multipart (0.0.27→0.0.31),
and cryptography (46.0.7→48.0.1). The starlette upgrade introduced a StarletteDeprecationWarning
for plain httpx — resolved by switching to httpx2==2.4.0. Migration 0025 fixed for both SQLite
and PostgreSQL (inline unnamed FK constraint removed from batch_alter_table).

Settings screen CSS overhauled: member rows match the settings-row vertical rhythm,
role chip indent removed, settings-section__heading works on both h2 and button elements
without a modifier class, RetiredListSection inline styles replaced with CSS classes.

| # | Item | Completed |
|---|------|-----------|
| TRAIN-1 | Newberg Training Station — orange, 2 BLS ambulances + 2 jump bags, all check types | 2026-06-18 |
| TRAIN-2 | `seed_training.py` — standalone idempotent script, always seeded including production | 2026-06-18 |
| TRAIN-3 | `startup.sh` split into Pass 1 (operational, dev-only) and Pass 2 (training, always) | 2026-06-18 |
| SEC-AB1 | starlette 1.1.0 → 1.3.1 (CVE-2026-54283, CVE-2026-54282) | 2026-06-18 |
| SEC-AB2 | python-multipart 0.0.27 → 0.0.31 (CVE-2026-53540, CVE-2026-53539, CVE-2026-53538) | 2026-06-18 |
| SEC-AB3 | cryptography 46.0.7 → 48.0.1 (GHSA-537c-gmf6-5ccf) | 2026-06-18 |
| SEC-AB4 | httpx → httpx2==2.4.0 (StarletteDeprecationWarning resolved) | 2026-06-18 |
| BUG-AB1 | Migration 0025 — removed inline unnamed FK from batch_alter_table; SQLite + PostgreSQL compatible | 2026-06-18 |
| CSS-AB1 | Settings screen — member row padding, role chip indent, heading button pattern, RetiredListSection inline styles removed | 2026-06-18 |
| CSS-AB2 | MemberManagementSection — all missing CSS classes added to settings.css (member-row-*, badge-*, btn--small) | 2026-06-18 |

---

## Session AA — Help Screen + PII Banner + Launch Gate (2026-06-14)

| # | Item | Completed |
|---|------|-----------|
| LAUNCH-F1 | Help screen — Quick Reference, Feature Guide, Show Tutorial Again button | 2026-06-14 |
| LAUNCH-F2 | PII disclaimer banner on login screen — always visible, no acknowledgement required | 2026-06-14 |
| LAUNCH-OPS8 | TEST STATION production guard — replaced with Training Station strategy | 2026-06-14 |

---

## Session Z — Station Member Management + Azure Publish (2026-06-14)
ACC-B6 (edit member name), ACC-B7 (multiple roles per person, Option A),
and ACC-B8 (CSV bulk import) implemented together as one cohesive set.
Migration 0027 drops the single-user unique constraint and replaces it with
(station_id, user_id, role). PATCH and DELETE now use member_id for precision.
The UserPill role switcher updated to show all available roles fetched from
a new /stations/my/roles endpoint. test_member_management.py added (32 tests).
Three ruff errors fixed post-implementation. App published to Azure.

| # | Item | Completed |
|---|------|-----------|
| ACC-B6 | `PATCH /stations/{id}/members/{member_id}` — update preferred_name; propagates to all rows for same user | 2026-06-14 |
| ACC-B7 | Multi-role support (Option A): migration 0027; `GET /stations/my/roles`; UserPill and useRoleMode updated | 2026-06-14 |
| ACC-B8 | `POST /stations/{id}/members/import` CSV bulk import + template download; `MemberManagementSection.jsx` in Settings | 2026-06-14 |
| RUFF-Z | Three ruff errors fixed: B018 in station_members.py, two F841 in test_member_management.py | 2026-06-14 |
| AZURE-PUBLISH | App published to Azure — live at lively-bush-0ed75ca10.7.azurestaticapps.net | 2026-06-14 |

---

## Session Y — UAT Complete + Test Suite Fix + Questions Closed (2026-06-14)
All UAT scenarios passed. Test suite fixed: two root causes resolved (audit metadata date
serialization from CQ-B6; par level NULL compartment duplicate detection from CQ-B7).
437 tests collected, 0 failed. All open questions resolved. App is launch-ready.

| # | Item | Completed |
|---|------|-----------|
| UAT-2 | Responder UAT passed | 2026-06-14 |
| UAT-5 | Cross-role test cases passed | 2026-06-14 |
| UAT-6 | Edge case test cases passed | 2026-06-14 |
| UAT-7 | Pending assignment test case passed | 2026-06-14 |
| UAT-8 | Multi-station test case passed | 2026-06-14 |
| UAT-9 | Unit 712 full shift-start check — cold run passed | 2026-06-14 |
| UAT-10 | After-call usage log — cold run passed | 2026-06-14 |
| UAT-11 | Damaged item scenario — cold run passed | 2026-06-14 |
| BUG-Y1 | `check_history.py` audit metadata passed `date` object to JSON serializer — converted via `_check_date_str()` helper | 2026-06-14 |
| BUG-Y2 | `create_par_level` NULL compartment duplicate not caught by DB constraint — pre-check restored for NULL case | 2026-06-14 |
| Q-3 | Download check history CSV — resolved: yes, build as F-5G3 when first compliance report is due | 2026-06-14 |
| Q-6 | Auto-hard-delete of soft-deleted checks — resolved: Azure Function on 90-day timer | 2026-06-14 |
| F-5F7 | Supply room stock view on supervisor dashboard — resolved: inline low-stock alerts (SR-B3) and DamagedItemsPanel cover this | 2026-06-14 |

---

## Session X — Code Quality Cleanup (2026-06-14)
All five CQ backlog items implemented. Codebase is portfolio-ready.
Migration 0026 added for check_date Date type. Old admin.py replaced by three sub-routers.

| # | Item | Completed |
|---|------|-----------|
| CQ-B7 | `create_par_level` pre-check refined — DB IntegrityError for compartment-scoped; pre-check retained for NULL compartment_id | 2026-06-14 |
| CQ-B4 | `LastReadingItem` → `schemas/checks.py`; `_ItemStatusPatch` → `schemas/inventory.py` as `ItemStatusPatch` | 2026-06-14 |
| CQ-B5 | `admin.py` (30KB) split into `admin_items.py`, `admin_vehicles.py`, `admin_stations.py`; `main.py` updated | 2026-06-14 |
| CQ-F1 | `check-wizard/index.jsx` 18 `useState` calls → `useReducer`; `submissionResult` object groups submit fields | 2026-06-14 |
| CQ-B6 | `check_date` `String(10)` → `Date` type; migration 0026; model + router + schema updated | 2026-06-14 |

---

## Session W — Check History Endpoints + Usage Log Gap Closure (2026-06-13)

| # | Item | Completed |
|---|------|-----------|
| CH-B4 | `DELETE /checks/daily/{id}/force` — Admin only, permanent hard-delete; 6 new tests | 2026-06-13 |
| CH-B5 | `GET /checks/daily/deleted?station_id=` — Supervisor+, list soft-deleted; 6 new tests | 2026-06-13 |
| CH-B6 | `PATCH /checks/daily/{id}/restore` — Supervisor+, restore soft-deleted; 7 new tests | 2026-06-13 |
| USAGE-B1 | `get_last_readings` subtracts post-check usage via `_get_post_check_usage()` | 2026-06-13 |
| USAGE-B2 | `location_id` on UsageEvent + schema validation + location-scoped usage query | 2026-06-13 |

---

## Session V — UAT Continued (2026-06-12)

| # | Item | Completed |
|---|------|-----------|
| UAT-3 | Supervisor UAT passed | 2026-06-12 |
| UAT-4 | Administrator UAT passed | 2026-06-12 |
| UAT-BUG4 | Progress bar showed "Vehicle" for supply room checks | 2026-06-12 |
| UAT-BUG5 | "This check" as check subject — selection_label fix | 2026-06-12 |
| UAT-BUG6 | Check date blank on Step 5 — todayIso() fallback | 2026-06-12 |
| UAT-BUG7 | Supply room check did not update View Supplies — SR-B5 reconcile | 2026-06-12 |
| DEAD-CODE | RestockVehiclePanel, StockSummaryView, getStationChecksToday deleted | 2026-06-12 |
| CI-AUDIT | npm audit --omit=dev so esbuild CVEs don't block deploy | 2026-06-12 |
| PAR-FIX | list_location_par_levels filters ParLevel.active (UAT-BUG8) | 2026-06-12 |

---

## Session U — Supervisor UAT + Damaged Items (2026-06-12)

| # | Item | Completed |
|---|------|-----------|
| UAT-BUG-LOG | Log Items Used showed no ambulances (v.status vs v.active fix) | 2026-06-12 |
| UAT-BUG-NC | No Change bypassed Reconcile when items short | 2026-06-12 |
| USAGE-FLAKY | test_usage.py flaky unique constraint (id(station) → uuid4().hex[:12]) | 2026-06-12 |
| SUP-DMG-FIX1 | FAIL banner persisted after repair resolved | 2026-06-12 |
| SUP-DMG1 | GET /stations/{id}/damaged-items; DamagedItemsPanel; 13 tests | 2026-06-12 |

---

## Sessions A–T — Foundation through Par Level Deactivation (2026-05-26 to 2026-06-11)
Full history in git. Highlights: Azure AD JWT auth, 3-role RBAC, check wizard 5-step flow,
compliance dashboard, supply room, retirement, security headers, CI/CD pipeline.

---

## Post-Session L — Frontend Tests + Rate Limiting (2026-06-08/09)

| # | Item | Completed |
|---|------|-----------|
| FE-TEST-INFRA--10 | MSAL mocks, useAuth mock, 10 component test files | 2026-06-09 |
| RATE-FIX | slowapi rate limiter; TESTING flag; check_date server-derived; performed_by email | 2026-06-09 |
| RATE-CI | ruff in CI; migration 0019 composite index | 2026-06-09 |
