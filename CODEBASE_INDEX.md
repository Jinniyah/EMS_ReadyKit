# EMS ReadyKit — Codebase Index
# Last updated: 2026-06-20 — Session AI closed (ITM-4: seed.py rewritten with BASE_ITEM_SEED,
# station-scoped items, Newberg full par levels, Marcellus/Training/Test catalog only.
# ITM-1/2/3/4 ✅ done. 484/484 expected after reseed. Next: ITM-5 + ITM-6.)
# PURPOSE: Load this file at the start of every session to orient quickly.
# After reading this, load only the sections relevant to the current task.
# Full project state → docs/project_index.md | Open work → docs/backlog.md

---

## ⚠ PENDING: Item model rework ITM-5..8 in progress (see docs/backlog.md)
**ITM-1 ✅ DONE (Session AG):** `station_id` FK + `UniqueConstraint("station_id", "name")`
added to `Item`; migration 0028 applied; supply catalog scoped to station; test suite updated.
**ITM-3 ✅ DONE (Session AH):** `category_group` VARCHAR(100) nullable added to `Item`;
migration 0029 applied; schema updated.
**ITM-4 ✅ DONE (Session AI):** `seed.py` fully rewritten — `BASE_ITEM_SEED` with 7 category
groups, `get_or_create_item(station_id=...)` required, `seed_station_catalog()`, canonical item
names, corrected O2 PSI thresholds, LUCAS merge, Fire Extinguisher SUPPLY. 32
`test_seed_integrity` failures resolved. Reseed required: `Remove-Item ems_readykit_dev.db;
alembic upgrade head; python seed.py`.
**ITM-5** (backend station scoping for item endpoints) is next.

---

## Repo Root Layout

```
EMS_ReadyKit/
├── app/                        # Python backend (FastAPI)
│   ├── ems_readykit/           # Application package
│   │   ├── core/               # Config, auth, DB, logging, audit
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── routers/            # FastAPI route handlers + deps.py
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── main.py             # App factory, middleware, router registration
│   ├── alembic/                # DB migrations (versions/ subdirectory)
│   ├── tests/                  # pytest suite (484 collected; 484 passing after reseed — ITM-4 resolved all 32 seed_integrity failures)
│   ├── seed.py                 # Dev seed data — ITM-4 rewrite complete (Session AI). BASE_ITEM_SEED, station-scoped items, Newberg full par levels, Marcellus/Training/Test catalog only.
│   ├── seed_training.py        # Training station seed — always run, including production (Session AB)
│   ├── initial_stock.csv       # 10 seed stock items — upload via Receive New Stock → CSV
│   └── pyproject.toml          # Dependencies + pytest config
├── frontend/                   # React 18 + Vite PWA
│   └── src/
│       ├── modules/            # Feature modules (self-contained)
│       ├── pages/              # Top-level page components
│       ├── shared/             # Cross-module: api, components, hooks, utils
│       └── App.jsx             # Router, auth guard, top-level layout
├── docs/                       # All project documentation
│   ├── backlog.md              # ALL open work items — single source of truth
│   ├── project_index.md        # Technical reference, API structure, stack
│   ├── backlog_completed.md    # Completed items (Sessions A–AF) + changelog archive
│   ├── models/                 # Real inventory checklist photos (712, jump bag) — ITM-2 source
│   ├── uat_test_cases.md       # UAT test cases
│   └── adr/                   # Architecture Decision Records (ADR-001–006)
├── iac/                        # Terraform (Azure infra)
├── .github/workflows/          # CI/CD (pip-audit → test → build → deploy)
├── CLAUDE.md                   # Rules for AI-assisted development
├── CODEBASE_INDEX.md           # This file
└── README.md                   # Public-facing project overview
```

---

## Backend — Routers (app/ems_readykit/routers/)

All routes are prefixed `/api/v1/`. Router registration order in main.py matters
(station_members before stations; check_history before checks).

| File | Size | Route Prefix | Roles | Purpose |
|------|------|-------------|-------|---------|
| `deps.py` | 5 KB | — | — | Shared: `get_current_user`, `require_role`, `get_vehicle_or_404`, `require_station_membership`, role constants |
| `stations.py` | 11 KB | `/stations` | All / Admin | CRUD; GET /my; GET supply-room (404 if missing); POST supply-room (get-or-create + Shelf 1–4); `GET /stations/{id}/expiring-soon` includes EXPIRY_DATE check-type items (SUP-F3); `GET /stations/{id}/settings` (Supervisor+, CH-B8); `PATCH /stations/{id}/settings` (Admin only, CH-B7); `PATCH /stations/{id}/retire` (Admin, RET-B3); `GET /stations/{id}/damaged-items` (Supervisor+, SUP-DMG1). `GET /stations/{id}/supply-room` has no `retired_at` filter server-side — a retired supply room is still returned; the frontend filters it out (see supervisorApi.js note below). |
| `station_members.py` | 8 KB | `/stations/{id}/members` | Supervisor+ | Membership management; PATCH/DELETE by `member_id` (integer PK, ACC-B7); CSV bulk import + template download (ACC-B8). This is the only correct member endpoint set — frontend consolidated onto it in Session AE (MERGE-1) after a stale `user_id`-based caller in `adminApi.js` was found broken. |
| `vehicles.py` | 6 KB | `/vehicles` | All + membership | Vehicle CRUD; OOS/RTS status toggle; `PATCH /vehicles/{id}/retire` (Admin, RET-B1) — sets `retired_at`, `retired_by`, `retirement_reason`, AND `active=False`. Frontend must check `retired_at` directly, not just `active` (see BUG-AD1, Session AD). `GET /stations/{id}/vehicles` returns ALL vehicles (active + retired) unless `?active=true` is explicitly passed — callers that don't pass it must filter `retired_at` client-side (Session AF, found in `supervisorApi.getTodayCompliance`). |
| `checks.py` | 26 KB | `/checks/daily` | All + membership | Check wizard: create with embedded line_items; `_compute_line_item_status`; `_auto_decrement_supply_room` (SR-B4, N+1 batched PERF-1); `_reconcile_supply_room_check` (SR-B5 — called on STATION_SUPPLY_ROOM submission; reconciles quantity_found back to StockLot quantities FIFO); helpers: `_resolve_check_location`, `_enforce_full_check_compartments`, `_build_lot_map`, `_build_line_items` (CQ-B3); `GET /daily/last-readings`. Two distinct list endpoints with very different scope, worth knowing apart: `GET /daily/station/{station_id}` (date-range, capped at 90 days, 422s above that) vs `GET /daily/location/{location_id}` (single location, ALL checks ever, no range limit at all) — see BUG-AF2 note below for why picking the wrong one breaks an "all-time most recent" lookup. |
| `check_history.py` | 7 KB | `/checks/daily` | All / Supervisor+ | Read-only history; soft-delete; acknowledgement; hard-delete (Admin only); `my-history` accepts optional `station_id` filter |
| `repair_requests.py` | 9 KB | `/vehicles/{id}/repair-requests` | All roles | File, update, resolve repair requests; `resolution_notes` required on RESOLVED |
| `inventory.py` | 28 KB | `/inventory` | All + membership | Locations, compartments, par levels, lots, stock summary, CSV receive. `GET /supply-catalog?station_id=` (SR-B1). `PATCH /supply-catalog/items/{id}/count` (SR-B2). `PUT /lots/{id}` (SR-F7). `PATCH /inventory/items/{id}/status` marks/clears damaged. `PATCH /locations/{id}/retire` (Admin, RET-B2). `GET /lots/retired?location_id=` (Supervisor+, RET-B6). `PATCH /lots/{id}/retire` (Supervisor+, RET-B5) — registered BEFORE `/lots/{lot_id}` to avoid path ambiguity. `PATCH /par-levels/{id}` soft-deactivate with reason + membership check (B-E9). `POST /par-levels` (`create_par_level`) reactivates a matching soft-deactivated `(item_id, compartment_id)` row instead of inserting a duplicate (PAR-B1, Session AF) — see note below. |
| `items.py` | 3 KB | `/items` | Supervisor+ (create/edit) / All (read) | Item catalog; `POST /items` is SUPERVISOR_PLUS (not admin-only); deactivation is ADMIN_ONLY via admin router. ⚠ Will need `station_id` scoping — see ITM-5 in `docs/backlog.md`. |
| `admin_items.py` | — | `/admin` | Admin (most) / Supervisor+ | Item catalog admin, par levels, CSV import (split from monolithic admin.py, CQ-B5). `POST /admin/items/{id}/assign` (`assign_item_to_compartment`) reactivates a matching soft-deactivated `(item_id, compartment_id)` par level instead of inserting a duplicate (PAR-B1, Session AF) — see note below. Already accepts `location_id` for any `InventoryLocation` (vehicle, jump bag, or supply room), not just `vehicle_id` — confirmed during ITM planning; the frontend (`ItemAssignments.jsx`) just never exposes that option yet (ITM-6). ⚠ `list_items`/`search_items`/`_conflict_on_name` will need `station_id` scoping — see ITM-5. |
| `admin_vehicles.py` | — | `/admin` | Admin | Vehicle color and details admin (split from monolithic admin.py, CQ-B5) |
| `admin_stations.py` | — | `/admin` | Admin | `POST /admin/stations` (ADMIN-B15, auto-creates supply room + StationMember). `PATCH /admin/locations/{id}` renames a location label (SS-B1). `GET /admin/retired?type=&station_id=` lists retired vehicles/locations/stations (RET-B4). `GET /admin/email-alignment-check?station_id=&include_inactive=` — flags StationMember rows whose `user_id` doesn't look like a valid email (blank, contains whitespace, missing `@`/domain, not lowercase); read-only diagnostic for catching display-name-instead-of-email mistakes from manual add or CSV import (LAUNCH-OPS9, Session AC). |
| `usage.py` | 9 KB | `/checks` | All + membership | `POST /checks/usage` (log items used, FIFO decrement); `GET /checks/usage/station/{id}` (history); `GET /checks/usage/station/{id}/frequent` (top 10 items, 90-day window) |
| `audit.py` | 2 KB | `/audit` | Supervisor+ | Paginated audit event log; `GET /audit?from_date=&to_date=` date-range filter (B-E18). Unmodified across Session AF — two separate suspicions about a naive/aware datetime comparison here were each checked via isolated repro and ruled out; the real bug both times was on the test side (global-table pollution, then a local-vs-UTC date computed in the wrong timezone). See `docs/backlog_completed.md` Session AF write-up for the full two-pass diagnosis before touching this file's date filters. |

### ⚠ PAR-B1 (Session AF): par-level reactivation on re-add after removal
`ParLevel`'s unique constraint `uq_par_item_compartment (item_id, compartment_id)` has no
concept of `active`. Soft-deactivating a par level (Remove, via either Station
Administration's `CompartmentParLevels.jsx`/`ItemAssignments.jsx` or a direct API call)
leaves a row occupying that slot — re-adding the same item to the same compartment used to
always fail with "already assigned" via the `IntegrityError` fallback, even with no active
duplicate present. Both creation endpoints (`assign_item_to_compartment` in
`admin_items.py`, `create_par_level` in `inventory.py`) now check for a matching inactive
row first and reactivate it (clearing `deactivated_at`/`deactivation_reason`, applying the
new min/max) instead of inserting a duplicate, preserving the original `par_id` and its
history. New test file: `app/tests/test_par_level_reactivation.py`.

### ⚠ BUG-AF2 (Session AF, same-day UAT follow-up): pick the right check-list endpoint for unbounded lookups
`GET /checks/daily/station/{station_id}` (used by `supervisorApi.getComplianceRange`) caps
its date range at 90 days and returns 422 above that. A first pass at the Compliance
Calendar's "Station Supplies Count" reminder tried to fake an unbounded "most recent count
ever" lookup by widening that endpoint's window to 730 days — every request 422'd silently,
`useApi` correctly nulled out the data on error, and the reminder rendered as if no count
had ever happened (with no visible error), and its click target (built from the same dead
data) stopped opening anything. Fixed by switching to `GET /checks/daily/location/{location_id}`
(new `supervisorApi.getLocationCheckHistory`), which is scoped to one location and has no
date-range limit at all — the correct tool whenever "all-time most recent" is the actual
requirement, regardless of how wide a range-bounded endpoint's window is stretched. Both the
reminder's display text and its click target now read from this single fetch.

No backend changes were needed for Session AE's member-management merge — `station_members.py`
was already correct (member_id-based, ACC-B7-compliant). The bug was entirely in the frontend's
`adminApi.js`, which had a second, stale, user_id-based set of member endpoints that never got
updated when ACC-B7 changed the unique constraint and route shape.

### Key shared patterns (deps.py)
```python
from ems_readykit.routers.deps import (
    ALL_ROLES,        # (RESPONDER, SUPERVISOR, ADMINISTRATOR)
    SUPERVISOR_PLUS,  # (SUPERVISOR, ADMINISTRATOR)
    ADMIN_ONLY,       # (ADMINISTRATOR,)
    get_current_user,
    require_role,
    get_vehicle_or_404,
    require_station_membership,
)
```

---

## Backend — Models (app/ems_readykit/models/)

| File | Key Model | Notes |
|------|-----------|-------|
| `station.py` | `Station` | primary_color (0011), call_sign (0012), allow_check_modification (0022, default True); retired_at/by/reason (0023) |
| `vehicle.py` | `Vehicle` | vehicle_color (0011); status ACTIVE/OOS; `active` and `retired_at` are independent fields — see docstring: "RET-M1: permanent retirement (distinct from temporary OOS via active=False)". `check_type_value` property normalises enum→str (CQ-B1) |
| `inventory_location.py` | `InventoryLocation` | LocationType: VEHICLE, JUMP_BAG, STATION_SUPPLY_ROOM; retired_at/by/reason (0023) |
| `compartment.py` | `Compartment` | sort_order, location_descriptor, `requires_full_check` (bool, migration 0015) — when True, No Change is blocked for that compartment (Truck Operations uses this) |
| `par_level.py` | `ParLevel` | item ↔ compartment; min/max quantity; active flag (0010); `priority_check` + `priority_question` (0015); `is_damaged` (bool); `deactivated_at` + `deactivation_reason` (0024). `uq_par_item_compartment (item_id, compartment_id)` has no `active` awareness — see PAR-B1 above. No changes needed for ITM-1..8 — this model is already correctly scoped via `location_id`/`compartment_id`. |
| `stock_lot.py` | `StockLot` | lot_number, expiration_date, quantity; retired_at/by/reason (0023) |
| `item.py` | `Item` | **✅ ITM-1 + ITM-3 done (migrations 0028, 0029):** `station_id` FK (NOT NULL → stations) + `UniqueConstraint("station_id", "name", name="uq_items_station_name")` (0028); `category_group` VARCHAR(100) nullable (0029) — seven values: "Airway & Respiratory", "Wound Care & Trauma Supplies", "PPE & Cleaning", "Diagnostic & Monitoring Equipment", "Medications & Controlled Substances", "Documents, Linens & Patient Comfort", "Vehicle Operations". ItemCheckType enum: SUPPLY, MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, EXPIRY_DATE (stored as VARCHAR); `station_supply` bool (0017); `measurement_minimum`/`measurement_maximum`; `recurrence_days`; `check_type_value` property (CQ-B1). Supply catalog scoped to station. |
| `daily_inventory_check.py` | `DailyInventoryCheck` | CheckStatus: PASS/NEEDS_RESTOCK/FAIL; status computed server-side; vehicle_id nullable + location_id (0013) for portable checks; soft-delete fields (deleted_at/by/reason, force_deleted) |
| `check_line_item.py` | `CheckLineItem` | LineItemStatus: OK/SHORT/LOW/MISSING/EXPIRED/FAIL/OVERDUE; quantity_found/needed; measurement_value; functional_pass; date_value. `item_id` → item → (via check → compartment/location) one unambiguous station, same as ParLevel — no model change needed for ITM-1..8. |
| `controlled_substance_check.py` | `ControlledSubstanceCheck` | dual-signature; ALS vehicles only |
| `repair_request.py` | `RepairRequest` | OPEN → IN_PROGRESS → RESOLVED; `resolution_notes` required on resolve |
| `station_member.py` | `StationMember` | user_id = email (JWT preferred_username); ACC-B7 unique constraint is `(station_id, user_id, role)` — supports multiple roles per person via multiple rows |
| `audit_event.py` | `AuditEvent` | Immutable; write via `core/audit.py::write_audit_event(actor=, metadata=)`. `timestamp` always `datetime.now(timezone.utc)` at write time — never derived from a request payload's own date fields. |
| `stock_lot.py` | `StockLot` | Transfer record: from/to location, item, qty, FIFO lot snapshot |
| `usage_event.py` | `UsageEvent`, `UsageEventItem` | After-call usage log. UsageEvent → station/vehicle/performed_by/timestamp/notes. UsageEventItem → item_id + quantity_used. Lazy selectin on vehicle + items. `UsageEvent.station_id` is direct — no model change needed for ITM-1..8. |

### ⚠ Critical frontend convention: active vs retired_at (BUG-AD1, Session AD)
`active` (temporary, reversible — Mark Out of Service / Return to Service) and
`retired_at` (permanent — Settings → Retire) are **independent fields** on Vehicle,
InventoryLocation, Station, and StockLot. Retiring sets `active=False` as a side
effect, so checking `active` alone happens to exclude retired records *today*, but
that's incidental, not guaranteed. **Every frontend list/action that touches one of
these models must filter `!v.retired_at` explicitly**, the same way `usage-log/index.jsx`
already did before this was a documented rule. Already fixed: `VehiclesScreen.jsx`,
`vehicles/index.jsx` + `VehicleCard.jsx`, `HomePage.jsx`'s `useStationIssues`,
`check-wizard/components/Step1Vehicle.jsx`, and (Session AF) `supervisorApi.getTodayCompliance`
+ `ComplianceCalendar.jsx` + `supervisor/index.jsx`. If a new screen lists vehicles/locations,
check this convention before shipping it.

### ⚠ Critical frontend convention: member_id, not user_id, for member PATCH/DELETE (Session AE)
`StationMember` rows are addressed by `member_id` (integer PK) for PATCH and DELETE,
never by `user_id` (email string) — see ACC-B7's docstring in `station_members.py`.
A person can hold multiple roles, each as a separate row with the same `user_id`, so
`user_id` alone is no longer a unique key. The only frontend API module that should
call these endpoints is `modules/admin/api/membersApi.js`. Don't add a second
member-CRUD API module elsewhere — that's exactly how the bug fixed in MERGE-1
(Session AE) happened: a second, stale, user_id-based copy in `adminApi.js`.

### ⚠ Critical frontend convention: date-range vs unbounded check lookups (BUG-AF2, Session AF)
`checks.py` exposes two shapes of "list checks" endpoint and they are NOT interchangeable.
`GET /checks/daily/station/{id}` is a date-range query, capped at 90 days, intended for
calendar/dashboard views over a bounded window — widening the range past 90 days doesn't
make it unbounded, it makes it 422. `GET /checks/daily/location/{id}` and
`GET /checks/daily/vehicle/{id}` are entity-scoped with no range limit at all — use one of
these whenever the actual requirement is "the most recent check ever for this thing,"
regardless of how long ago. Before adding a new "last counted"/"last checked" feature,
check which shape the requirement actually needs; this is exactly the mistake BUG-AF2 fixed.

### Domain model hierarchy
```
Station
 └── Vehicle (ALS / BLS / QRV)
      ├── InventoryLocation (VEHICLE — auto-created)
      │    └── Compartment (requires_full_check on Truck Operations)
      │         ├── ParLevel  (item → min/max qty; priority_check; is_damaged)
      │         └── StockLot  (lot# + expiry + qty)
      └── DailyInventoryCheck
           ├── CheckLineItem  (per-item result; LineItemStatus)
           ├── ControlledSubstanceCheck
           └── RepairRequest (OPEN→IN_PROGRESS→RESOLVED)

InventoryLocation (JUMP_BAG / STATION_SUPPLY_ROOM — station-scoped)
 └── DailyInventoryCheck (via location_id — portable location checks)

StationMember  (user ↔ station; one row per role held, ACC-B7)
AuditEvent     (immutable log)
```

---

## Backend — Core (app/ems_readykit/core/)

| File | Purpose |
|------|---------|
| `config.py` | `get_settings()` — env vars, feature flags, is_production, is_sqlite |
| `auth.py` | `resolve_current_user()`, `CurrentUser`, role constants, Azure AD JWT RS256 validation; test tokens: `Bearer test-{role}` → `test-{role}@ems.local` |
| `database.py` | `get_db()` FastAPI dependency; engine + session factory |
| `audit.py` | `write_audit_event(actor=, metadata=)` — always use this, never inline AuditEvent(). `timestamp` is always `datetime.now(timezone.utc)` — any test computing a date boundary to compare against it must also use UTC "today", not local `date.today()` (see Session AF fix in test_routers.py's TestAuditEndpoints). |
| `logging.py` | `configure_logging()`, `set_request_id()` |
| `limiter.py` | `slowapi` Limiter singleton; `DAILY_CHECK_RATE_LIMIT` constant. `TESTING=true` (set by conftest.py) switches to 99999/min so tests never exhaust the counter. |

---

## Backend — Tests (app/tests/)

| File | Size | Coverage | DB Fixture |
|------|------|----------|------------|
| `conftest.py` | 5 KB | Fixtures: in-memory SQLite (`db`), seeded dev DB (`seeded_db`), test client, auth headers | — |
| `test_routers.py` | 67 KB | Main router integration tests. Session AF: `TestAuditEndpoints::test_audit_from_date_tomorrow_returns_empty` / `test_audit_to_date_yesterday_returns_empty` scoped to a station the test itself creates (`station_id=` query param), AND their `tomorrow`/`yesterday` boundary is computed from `datetime.now(timezone.utc).date()` rather than local `date.today()` — two separate fixes for two separate root causes found across the session (global-table pollution, then a local/UTC day-boundary mismatch). See `docs/backlog_completed.md` Session AF write-up for the full diagnosis. | `db` |
| `test_par_level_reactivation.py` | — | NEW (Session AF). PAR-B1: assign→deactivate→re-assign reactivates the original par_id on both `POST /admin/items/{id}/assign` and `POST /inventory/par-levels`; reactivated row clears deactivation fields; reactivated item reappears in the wizard-facing `GET .../par-levels`; active duplicates still correctly blocked. `compartment` fixture is created fresh per test (named after `request.node.name`) rather than get-or-create, because route handlers call `db.commit()` and a shared compartment would leak active par levels across tests in the same file. | `db` |
| `test_supply_room.py` | 12 KB | Supply room SR-B1/B2/B3/B4 | `db` |
| `test_repair_requests.py` | 17 KB | Repair request lifecycle | `db` |
| `test_station_membership.py` | 15 KB | RBAC + station membership enforcement | `db` |
| `test_member_management.py` | — | ACC-B6/B7/B8: edit member name, multi-role, CSV import; 32 tests | `db` |
| `test_check_history.py` | 15 KB | Check history, soft-delete, acknowledgement | `db` |
| `test_admin_items.py` | 12 KB | Admin item management, par levels, CSV | `db` |
| `test_models.py` | 7 KB | Model-level unit tests | `db` |
| `test_priority_items.py` | — | AED + LUCAS all check types; legal immutability; FAIL preservation; priority flag DB persistence | `db` |
| `test_persona_responder.py` | — | Jamie (Responder): all 5 check types; FAIL+comment+continue; multiple checks/day; role boundary | `db` |
| `test_persona_supervisor.py` | — | Earl (Supervisor): check history; damaged item regression; repair requests; station today view | `db` |
| `test_persona_admin.py` | — | Jennifer (Admin): supply room decrement; FUNCTIONAL items excluded; role alias regression; admin-only deactivation boundary | `db` |
| `test_safety_checks.py` | — | O2 PSI below minimum → LOW; date recurrence overdue → OVERDUE; requires_full_check enforcement (422 on missing items) | `db` |
| `test_seed_integrity.py` | — | Verifies seeded dev DB: Unit 712, PC 8, AED/LUCAS items, O2 PSI minimums, Truck Operations, jump bags | `seeded_db` |
| `test_usage.py` | — | POST /checks/usage happy path, FIFO decrement, non-SUPPLY rejection, 403/404 guards; GET history + frequent items | `db` |
| `test_retirement.py` | — | RET-B1–B6: retire vehicle/location/station/lot; list retired; 403/409 enforcement. | `db` |
| `test_damaged_items.py` | — | SUP-DMG1: damaged items endpoint; happy path; retired excluded; inactive excluded; station isolation; RBAC. 13 tests. | `db` |
| `test_email_alignment.py` | — | LAUNCH-OPS9: `GET /admin/email-alignment-check` — valid emails pass clean; display-name/malformed/uppercase/blank user_id flagged; inactive row inclusion toggle; cross-station scan; RBAC (Admin only). 12 tests. (Session AC) | `db` |

**Run:** `cd app; pytest` — 484 tests collected, **484 passing** (expected after `alembic upgrade head; python seed.py`). ⚠ ITM-5..8 still ahead — `test_item_station_scoping.py` (ITM-8) will add to this count once backend scoping (ITM-5) and frontend (ITM-6) are done. `ruff check .` and `black --check .` confirmed green at Session AF close; run again after ITM-5 changes.

**Two DB fixtures — do not mix:**
- `db` — in-memory SQLite, empty, rolls back after each test. Use for all API/logic tests.
- `seeded_db` — read-only connection to `ems_readykit_dev.db`. Use ONLY in `test_seed_integrity.py`. Skips if dev DB absent. Never write to it.

**Test isolation note:** Route handlers that call `db.commit()` release the active SQLAlchemy savepoint — committed rows are NEVER rolled back between tests within a pytest session; this is permanent for the rest of that `pytest` invocation, not just "until the next fixture teardown." Any fixture creating a row with a UNIQUE constraint must use get-or-create semantics (see `test_item` and `vehicle_location` fixtures in `test_supply_room.py`), AND any test asserting against a broad/global query (e.g. unscoped `GET /audit`) must instead scope its own query (station_id, vehicle_id, etc.) to the data it itself created — see `test_par_level_reactivation.py`'s per-test `compartment` fixture and `test_routers.py`'s Session AF audit-date-range fixes for two different examples of this same underlying constraint.

**Timezone note (Session AF):** any test that computes a date boundary to compare against
an `AuditEvent.timestamp` (or any other UTC-stamped column) must derive that boundary from
`datetime.now(timezone.utc).date()`, not local `date.today()`. The two differ whenever the
test machine's local wall-clock time has already crossed a UTC midnight boundary (common in
evening hours in US timezones) — see `TestAuditEndpoints::test_audit_from_date_tomorrow_returns_empty`
for a worked example of the failure mode this caused.

---

## Frontend — Modules (frontend/src/modules/)

Each module is self-contained with its own `index.jsx`, `api/`, `components/`.

### check-wizard/  (PWA 5-step check flow)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 15 KB | Wizard orchestration, step routing, draft state. Passes `selectionLabel` to `WizardProgress`. |
| `components/Step1Vehicle.jsx` | 14 KB | Vehicle/location selection + CS check toggle; detects `draft._supplyRoom` for supply room wizard path. `isCheckableVehicle(v)` helper checks both `active !== false` AND `!retired_at` (defensive fix, BUG-AD1 Session AD — this path was already safe via a side effect of the server-side `active=true` filter, but now checks `retired_at` directly instead of relying on that). |
| `components/Step2Compartments.jsx` | 14 KB | Priority items section (inline confirm) + compartment list with reading confirmations; No Change / Modify / stock preview. Short count based on last check quantity_found. Reading confirmation rows are suppressed for `requires_full_check` compartments. Calls `onCompartmentsLoaded(compartments)` via `useEffect` so wizard index can populate `compartmentList` for progress bar, Step3 nav, and Step5 summary. Correctly filters `pl.active !== false` everywhere already. |
| `components/Step3Items.jsx` | 7 KB | Item counting per compartment. Reads par levels from the already-`active`-filtered backend response, so it reflects whatever is currently active for the compartment — see PAR-B1 above for why a "removed but still expected" item was actually a server-side reactivation bug, not a frontend filtering bug. |
| `components/ItemRow.jsx` | 16 KB | Per-item row — all check types (supply/measurement/functional/date) |
| `components/Step4Reconcile.jsx` | 13 KB | Flagged items review |
| `components/Step4Review.jsx` | 7 KB | Final summary before submit |
| `components/Step5Submit.jsx` | 9 KB | Submission + CS check dual-sign. `checkSubject` uses `selectionLabel` for supply room checks. `displayDate` has `todayIso()` fallback. |
| `components/SubmittedScreen.jsx` | 6 KB | Post-submit confirmation |
| `components/DraftBanner.jsx` | 5 KB | Resume-draft prompt on load; last-known station cached in localStorage |
| `components/WizardProgress.jsx` | 3 KB | Top progress bar. Step 1 label uses `selectionLabel` prop (defaults to 'Vehicle'). |

### supervisor/  (Compliance dashboard)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 7 KB | Dashboard entry; loads supply alerts (SR-B3) for SupplyLowStockPanel. Session AF: `vehicles` re-filtered defensively by `!v.retired_at` (source-of-truth fix is in `supervisorApi.js`, this is a second defensive layer matching the BUG-AD1 convention). |
| `components/ComplianceCalendar.jsx` | — | Calendar view of check compliance. Rewritten Session AF: week view = active (non-retired) vehicles + jump bags only; Station Supply Room intentionally excluded from week view (periodic count, not daily — would just be empty space). Month view = combined vehicle/jump-bag picker (`EntityPicker`) + traditional grid. The `SupplyRoomReminder` strip lives directly under the Week/Month toggle (visible in both views, moved there mid-session per Jennifer's UAT feedback that a chip buried in month view would get seen far less often). Supply room fetched via `supervisorApi.getSupplyRoomLocation`, which filters out a retired supply room client-side; its check history is fetched via `supervisorApi.getLocationCheckHistory` (BUG-AF2 fix — NOT `getComplianceRange`, which is range-capped and cannot answer "most recent ever"). Has an explicit error state (`.cal__supply-reminder--error`) instead of silently rendering as if no count existed. No test file yet — see TEST-AF1 in `docs/backlog.md`. |
| `components/CheckDetailPanel.jsx` | 9 KB | Drill-down check detail — read-only + comments only |
| `components/VehicleComplianceCard.jsx` | 7 KB | Per-vehicle compliance summary card |
| `components/PortableComplianceCard.jsx` | — | Per-portable-location compliance summary card |
| `components/ExpiringItemsPanel.jsx` | — | SUP-F3: expandable expiring lots panel |
| `components/SupplyLowStockPanel.jsx` | — | SR-F5: expandable supply low-stock panel; red if out, amber if below par |
| `components/DamagedItemsPanel.jsx` | — | SUP-DMG1: collapsible panel listing damaged items (item name, vehicle, compartment). allClear only when no FAIL + no damaged items. |
| `api/supervisorApi.js` | — | Session AF: `getTodayCompliance` now filters `vehicles = vehiclesRaw.filter(v => !v.retired_at)` at the source, since `GET /stations/{id}/vehicles` returns retired vehicles unless `active=true` is passed. `getSupplyRoomLocation(stationId, getToken)` fetches the station's supply room and returns `null` if missing OR retired (`!loc.retired_at` checked client-side, since the backend endpoint has no such filter). `getLocationCheckHistory(locationId, getToken)` (BUG-AF2) — all checks ever recorded at one location, no date-range limit; the correct source for "when was this last counted," unlike `getComplianceRange` which is capped at 90 days and exists for windowed calendar views, not all-time lookups. |

### admin/  (Station administration — Option B layout: station header + nav cards)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 21 KB | Admin hub: nav cards → Members / Items / Vehicles / Supplies / Jump Bags screens |
| `components/MembersScreen.jsx` | — | **Station Administration -> Members** — the single member-management entry point (Session AE, MERGE-1). Wraps `MemberManagementSection` (visible to Supervisor+) and `EmailAlignmentSection` (Admin only). Replaces the old flat-list MemberList/AddMemberForm pair, which called a broken user_id-based removal endpoint. |
| `components/MemberManagementSection.jsx` | — | Moved from `settings/` (Session AE). Member list grouped by person, edit name, multi-role chips with per-role remove, CSV import. ACC-B6/B7/B8. No test file yet — see TEST-AE1 in `docs/backlog.md`. |
| `components/EmailAlignmentSection.jsx` | — | Moved from `settings/` (Session AE). LAUNCH-OPS9 diagnostic — flags malformed `user_id` entries; notify-panel with mailto draft. Admin only. |
| `components/VehiclesScreen.jsx` | 25 KB | Vehicle + compartment CRUD, par assignment entry. Display filter excludes retired vehicles outright (`!v.retired_at`), independent of the "Show out-of-service vehicles" toggle (BUG-AD1, Session AD). `VehicleAdminCard` shows a "Retired" badge + retirement reason and hides Edit/Color-still-shown/OOS-RTS/compartment-edit controls for retired vehicles. |
| `components/ItemCatalog.jsx` | 9 KB | Item search + list (also reused as View Supplies interface in supply room). ⚠ Currently fetches the unscoped global catalog — no `station_id` passed to `adminApi.listItems`. See ITM-6 in `docs/backlog.md`. |
| `components/ItemForm.jsx` | 16 KB | Add/edit item form |
| `components/ItemAssignments.jsx` | 18 KB | Par level assignment — item-centric. "Add assignment" goes through `adminApi.assignItem` → `POST /admin/items/{id}/assign`, which now reactivates a soft-deactivated row instead of erroring (PAR-B1, Session AF). ⚠ `AddAssignmentForm`/`EditRow` currently render a vehicle-only `<select>` — no jump bag or supply room option, even though the backend endpoint already accepts `location_id` for either. See ITM-6 in `docs/backlog.md` — this is the planning session's confirmed UI gap, frontend-only fix. |
| `components/CompartmentParLevels.jsx` | — | Par level assignment — per-compartment item list. Accepts `vehicleId` OR `locationId` (for supply room / portable locations). Priority checkbox + question field (RX-F12). Remove → re-add round trip fixed by PAR-B1 (Session AF) — this was the exact UI path the bug was reported through. |
| `components/StationSuppliesScreen.jsx` | — | SS-F1: Admin screen — manage supply room shelves and their par levels. Fetches supply room → compartments → CompartmentParLevels per shelf. |
| `components/PortableLocationsScreen.jsx` | — | ADMIN-F7: Full CRUD for portable locations (Jump Bags). List → create → rename + ShelfManager (compartment CRUD + par levels). |
| `components/CsvImport.jsx` | 8 KB | Bulk item import with template download |
| `api/adminApi.js` | — | Station CRUD, item catalog, par levels, vehicles, portable locations. **No longer has member endpoints** — those moved to `api/membersApi.js` (Session AE). `listItems` has no `station_id` param yet — see ITM-6. |
| `api/membersApi.js` | — | Moved from `settings/api/` (Session AE). Member CRUD by `member_id` + CSV import/template (ACC-B6/B7/B8); `checkEmailAlignment` (LAUNCH-OPS9). The only frontend module that should call `/stations/{id}/members*` endpoints. |

### supply-room/  (Station Supplies — redesigned Session K)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 6 KB | Landing: 3 large cards (View Supplies, Count Supplies, Usage Log). Detects 404 → setup state with "Set Up Supply Room" button (calls POST supply-room). |
| `supply-room.css` | — | All supply-room CSS using design tokens |
| `api/supplyApi.js` | 3 KB | getSupplyRoom, createSupplyRoom (POST), catalog (SR-B1), patchCount (SR-B2), putLot (SR-F7), retireLot (RET-B5), CSV, station locations |
| `components/SupplyCatalogView.jsx` | — | SR-F3: catalog from SR-B1; items grouped by shelf; ⚠ Damaged badge (DMG-F3); per-shelf CompartmentParLevels add button for Supervisor+ (SS-F2). |
| `components/ReceiveStockPanel.jsx` | 8 KB | Manual add + CSV bulk upload |
| `components/TransferHistory.jsx` | 4 KB | Inbound/outbound transfer log |
| `components/UsageLogView.jsx` | — | Session N: Usage history — event rows with date/user/vehicle/items. |

### usage-log/  (After-Call Reset — Session N)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Orchestrator: loading → vehicle (if multiple) → item picker → submitting → done. Auto-skips vehicle step for single-vehicle stations. Filters: `v.active === true && !v.retired_at` — this was always correct and served as the reference pattern for fixing BUG-AD1 elsewhere (Session AD). |
| `api/usageApi.js` | — | logUsage (POST /checks/usage), getHistory (GET), getFrequentItems (GET frequent) |
| `components/UsageItemPicker.jsx` | — | Item picker with sections: "Used most often" (from history) or "Common items" (hardcoded defaults) + "All items". +/− controls. Selected items highlighted. 60px tap targets. |
| `usage-log.css` | — | All usage-log + history CSS using design tokens |

### vehicles/  (V&E Status)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 4 KB | Vehicle list with open-issue badges. `displayVehicles` filters out `v.retired_at` before computing in-service/out-of-service counts (BUG-AD1, Session AD). |
| `components/VehicleCard.jsx` | 9 KB | Vehicle detail + OOS/RTS toggle. Shows "Retired" badge instead of "Out of Service" and hides Report an Issue / Mark Out of Service / Return to Service entirely when `vehicle.retired_at` is set (BUG-AD1, Session AD — defensive layer in case a retired vehicle ever reaches this component). |
| `components/RepairRequestList.jsx` | 12 KB | Repair request list + status lifecycle |
| `components/RepairRequestForm.jsx` | 4 KB | File new repair request |

### check-history/
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 6 KB | My Checks / All Checks tabs + detail navigation |
| `components/` | — | Check list items and detail view |

### settings/  (Station configuration — Admin-only config; Session Q/R, narrowed Session AE)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Settings screen orchestration. Visible to Supervisor+ for the check-workflow toggle row; everything else (StationManagementSection, VehicleManagementSection, RetiredListSection) is Admin only. Member management and the Email Alignment Check moved to Station Administration -> Members (Session AE, MERGE-1) — Settings no longer has any member UI. |
| `api/settingsApi.js` | — | `getSettings(stationId, getToken)`, `updateSettings(stationId, payload, getToken)` |
| `api/retirementApi.js` | — | `getStationVehicles`, `getStationLocations`, `retireVehicle`, `retireLocation`, `retireStation`, `getRetired` |
| `components/VehicleManagementSection.jsx` | — | S-F7/RET-F1/F2: lists active vehicles + portable locations with Retire buttons |
| `components/StationManagementSection.jsx` | — | S-F6/RET-F4: station info + Retire Station button |
| `components/RetiredListSection.jsx` | — | RET-F5: collapsible ▲/▼ section; three sub-lists |
| `settings.css` | — | Settings-screen-only styles (shell, toggle, retirement). Cross-module classes (`.settings-section`, `.settings-row`, `.badge`, `.member-*`, `.email-alignment__*`) moved to `index.css` (Session AE) since they're now used by both `settings/` and `admin/`. |

**Member management is no longer split across two screens.** Previously: Admin -> Members
(broken, user_id-based removal, no multi-role/CSV) and Settings -> Team Members (working,
fuller-featured). Session AE (MERGE-1) consolidated everything into Station Administration ->
Members. Supervisors can manage their own station's members — add, edit name, add additional
roles, CSV import — without Administrator access; only the Email Alignment Check stays
Admin-gated within that same screen.

---

## Frontend — Tests (frontend/src/)

Vitest + React Testing Library. Run: `cd frontend && npm test` — **confirmed green by
Jennifer at Session AF close** (2026-06-19), re-verified after this session's frontend
changes to ComplianceCalendar.jsx, supervisorApi.js, and supervisor/index.jsx (including
the same-day BUG-AF2 follow-up).

| File | Tests | Coverage |
|------|-------|----------|
| `shared/utils/__tests__/statusCalc.test.js` | 40 | Status calc pure functions |
| `shared/utils/__tests__/dateHelpers.test.js` | 24 | Date formatting/clamping |
| `shared/utils/__tests__/roleGuard.test.js` | 14 | `canAccess()` all roles + 'admin' alias |
| `shared/hooks/__tests__/useDraft.test.js` | 3 | `draftKey()` uniqueness |
| `shared/components/__tests__/StatusBadge.test.jsx` | 16 | Check + item level badges |
| `modules/check-wizard/__tests__/WizardProgress.test.jsx` | 11 | Step labels, active/done, progress bar |
| `modules/check-wizard/__tests__/DraftBanner.test.jsx` | 10 | Hidden/shown, single/multi draft, resume |
| `modules/check-wizard/__tests__/ItemRow.test.jsx` | 15 | All 5 check types, confirmed state, damaged badge |
| `modules/check-wizard/__tests__/Step1Vehicle.test.jsx` | 8 | Vehicle list, supply room auto-advance, OOS |
| `modules/supervisor/__tests__/SupplyLowStockPanel.test.jsx` | 11 | Hidden, amber/red alerts, expand/collapse |
| `modules/vehicles/__tests__/VehicleCard.test.jsx` | 12 | OOS badge, repair count, RTS/OOS role-gating, Report an Issue. Session AD adds 4 regression cases for retired vehicles (BUG-AD1): Retired badge, no Return to Service, no Report an Issue, retirement reason shown. |
| `modules/admin/__tests__/ItemCatalog.test.jsx` | 11 | Item list, search, Add button role-gating |
| `modules/admin/__tests__/VehiclesScreen.test.jsx` | 3 | New file, Session AD (BUG-AD1) — this screen had no prior test coverage. Retired vehicle excluded by default; still excluded after toggling "Show out-of-service vehicles"; empty-state message reflects only active vehicles. |
| `modules/admin/__tests__/EmailAlignmentSection.test.jsx` | 17 | Moved from `modules/settings/__tests__/` (Session AE) — same coverage, new home. LAUNCH-OPS9 UI: Run Check button + clean/flagged states; Notify panel recipient checkboxes (excludes flagged person); custom email chips; Draft Email enable/disable; drafted preview with mailto link. |
| `modules/check-history/__tests__/CheckHistory.test.jsx` | 9 | My Checks, All Checks tab (Supervisor+), Deleted tab |
| `modules/usage-log/__tests__/UsageItemPicker.test.jsx` | 13 | Catalog, search, +/- controls, selected, sections |
| `modules/usage-log/__tests__/UsageLogScreen.test.jsx` | 6 | Multi-vehicle picker, single-vehicle skip, payload, error |

No test file exists yet for `MemberManagementSection.jsx` or the new `MembersScreen.jsx`
(neither the old admin flat-list nor the old settings version had one) — see `docs/backlog.md`
(TEST-AE1). Also no test file yet for the rewritten `ComplianceCalendar.jsx` (Session AF,
including the BUG-AF2 data-source fix) — see TEST-AF1 in the same backlog.

**Mock infrastructure:**
- `src/shared/hooks/__mocks__/useAuth.jsx` — configurable useAuth with Jamie/Earl/Jennifer personas
- `__mocks__/@azure/msal-react.js` — MSAL React stubs
- `__mocks__/@azure/msal-browser.js` — MSAL browser stubs

---

## Frontend — Shared (frontend/src/shared/)

### api/
| File | Purpose |
|------|---------|
| `client.js` | Axios instance; base URL from VITE_API_BASE_URL; auth token injector |
| `authConfig.js` | MSAL config: tenant ID, client ID, scopes |
| `stationsApi.js` | Shared `getMyStations` — imported by checkApi + adminApi |

### hooks/
| File | Purpose |
|------|---------|
| `useAuth.jsx` | MSAL integration; returns `{ user, token, isAuthenticated, role }` |
| `useRoleMode.jsx` | Display-only role switcher for supervisors in crew mode |
| `useDraft.js` | localStorage draft persistence; key includes `started_at` for multi-draft support |
| `useApi.js` | Thin wrapper: `{ data, loading, error }` for API calls. On error, `data` is set to `null` and stays `null` until the next successful fetch — any UI consuming this must handle the `error` field explicitly, since a null `data` is otherwise indistinguishable from "fetched successfully, found nothing" (see BUG-AF2 for the bug this caused when nobody checked `error`). |

### components/
| File | Purpose |
|------|---------|
| `UserPill.jsx` | Auth'd user display + role badge; role switcher fetches `/stations/my/roles` (ACC-B7) |
| `ItemSearchCombobox.jsx` | Typeahead search with 150ms debounce, keyboard nav, text highlighting |
| `LastCheckBanner.jsx` | Last check status banner for home screen |
| `ColorPickerWidget.jsx` | Station/vehicle color picker |
| `ErrorBoundary.jsx` | Top-level error boundary |
| `Modal.jsx` | Reusable modal dialog |
| `DevBanner.jsx` | Dev/staging environment indicator (reads VITE_API_BASE_URL) |
| `StatusBadge.jsx` | Check/repair status badge |
| `Spinner.jsx` | Loading indicator |

### utils/
| File | Purpose |
|------|---------|
| `roleGuard.js` | `canAccess(user, requiredRole)` — includes 'admin' alias for 'Administrator' |
| `statusCalc.js` | `deriveDraftItemStatus()` — frontend mirror of `_compute_line_item_status` in checks.py. Must stay in sync. |

### pages/
| File | Purpose |
|------|---------|
| `HomePage.jsx` | Post-auth landing: station picker, module cards, last-check banner, issue badges. `onCountSupplies` includes `selection_label: 'Station Supply Room'` in initialDraft. `useStationIssues` excludes retired vehicles before checking for open repair requests (BUG-AD1, Session AD) — a retired vehicle's old repair history no longer triggers the "Unresolved Issue" badge. |
| `NotFoundPage.jsx` | 404 page |

---

## Migrations (app/alembic/versions/)

29 migrations applied (0001–0029, plus 0003a branch). Run automatically at startup via `startup.sh`.
To add a new migration: `cd app && alembic revision --autogenerate -m "description"`

No further schema changes planned until ITM-4 closes (seed.py rewrite — schema-only, no migration needed).

| Migration | Description |
|-----------|-------------|
| 0001–0009 | Initial schema, stations, vehicles, checks, audit, items (ai_tags, alternate_names, barcode) |
| 0010 | `active` flag on par_levels |
| 0011 | `primary_color` on stations; `vehicle_color` on vehicles |
| 0012 | `call_sign` on stations |
| 0013 | `vehicle_id` nullable on daily_inventory_checks; `location_id` FK for portable checks |
| 0014 | `stock_transfers` table; backfills 4 default compartments for supply rooms with zero |
| 0015 | `priority_check` + `priority_question` on par_levels; `requires_full_check` on compartments |
| 0016 | `is_damaged` (bool) on check_line_items; batch mode |
| 0017 | `station_supply` (bool NOT NULL DEFAULT TRUE) on items; batch mode; SR-M1 |
| 0018 | Backfills STATION_SUPPLY_ROOM location + Shelf 1–4 compartments for active stations lacking one |
| 0019 | `ix_check_station_date` composite index on `daily_inventory_checks(station_id, check_date)` |
| 0020 | `usage_events` + `usage_event_items` tables; indexes on station_id and timestamp (Session N) |
| 0021 | UPDATE items: AED Pads Adult/Pediatric → `check_type = 'EXPIRY_DATE'`, `recurrence_days = NULL` (Session O) |
| 0022 | `allow_check_modification` Boolean column on `stations` (NOT NULL, server_default=True). Batch mode. (Session Q, B-M10) |
| 0023 | `retired_at`, `retired_by`, `retirement_reason` columns on `vehicles`, `inventory_locations`, `stations`, `stock_lots`. All nullable. Batch mode. (Session R, RET-M1/M2/M3) |
| 0024 | `deactivated_at` (DateTime, nullable) and `deactivation_reason` (String 500, nullable) on `par_levels`. Batch mode. (Session T, B-M6) |
| 0025 | check_date Date type fix; inline unnamed FK removed from batch_alter_table for SQLite + PostgreSQL compat (Session X/AB, CQ-B6, BUG-AB1) |
| 0026 | `check_date` `String(10)` → `Date` type (Session X, CQ-B6) |
| 0027 | `station_members` unique constraint changed to `(station_id, user_id, role)` — supports multiple roles per person (Session Z, ACC-B7) |
| 0028 | `items.station_id` FK (NOT NULL → stations); `uq_items_station_name(station_id, name)` replaces global unique on name. **Raw SQL** (not batch mode) — Alembic batch was re-carrying the inline UNIQUE from sqlite_master DDL through every table recreation; raw CREATE TABLE + INSERT SELECT + DROP + RENAME bypasses reflection entirely. (Session AG/AI, ITM-1) |
| 0029 | `items.category_group` VARCHAR(100) nullable; batch mode (Session AH, ITM-3) |

No new migration in Session AE or Session AF (both frontend + application-logic changes only;
PAR-B1's reactivation fix is router logic, not a schema change; BUG-AF2 is purely a frontend
data-source swap between two pre-existing, unmodified backend endpoints).
Migrations 0028 (Session AG) and 0029 (Session AH) added for ITM-1 and ITM-3. No further
schema migrations planned through ITM-6 — ITM-4 is seed.py only.

---

## Seed Data (app/seed.py, app/seed_training.py)

`seed.py` — **ITM-4 rewrite complete (Session AI).** Idempotent, dev-only.
Reseed sequence: `cd app; Remove-Item ems_readykit_dev.db; alembic upgrade head; python seed.py`

**Structure:** `BASE_ITEM_SEED` (~100+ canonical items) → `seed_station_catalog(db, station_id)` bootstraps each station → `build_ambulance_inventory`/`build_jump_bag` add Newberg's real par levels.

| Station | Vehicles / Locations | Notes |
|---------|---------------------|-------|
| Newberg Township Station 1 | Unit 712 (BLS) + Unit 712 Jump Bag + Supply Room | Full par levels from real 712 + jump bag inventory forms. PC 8 has all 6 AED/LUCAS items (LUCAS Device merged). |
| Marcellus Township Station 1 | Unit 540 (ALS) + Supply Room | Catalog only — supervisor assigns par levels via admin UI (ITM-6). |
| Newberg Training Station (orange) | Training Unit A/B + Jump Bag A/B + Supply Room | Catalog only — par levels assigned via admin UI. |
| ⚠ TEST STATION | Unit TEST (QRV) + Supply Room | Catalog + 7 `[TEST]`-prefixed items; no par levels; dev only. |

**Key seed decisions (ITM-2/4):**
- One canonical item per real-world thing reused across compartments via separate `ParLevel` rows (e.g. "Gauze, 3x3" → ambulance PC18 + jump bag Front Pocket + supply room shelf).
- O2 PSI: On-Board 500–2200 (large tank, unchanged); Stretcher + Jump Bag 200–500 (small tank, corrected).
- LUCAS Device merges former "LUCAS Device Ready Check" — one FUNCTIONAL priority item, `priority_check=True`.
- Fire Extinguisher: SUPPLY (not FUNCTIONAL) in both PS EC2 and Truck Operations — Jennifer-confirmed.
- New item: "Stretcher Battery Date of Last Charge" (DATE_RECORD, recurrence=90).
- `station_supply=False` baked into `BASE_ITEM_SEED` for AED/LUCAS/medication items.

**Unit 710 Jump Bag:** removed from seed (v1.66) — Unit 710 has no ambulance yet.

`seed_training.py` — always seeded including production via `startup.sh` Pass 2 (Session AB). Newberg Training Station (orange, `#e65100`): two BLS ambulances (Training Unit A/B) + two jump bags (Training Jump Bag A/B), ~1/3 of Unit 712's inventory across nine compartments, all six check types including AED/LUCAS priority items.

---

## Deployment

| Resource | Value |
|----------|-------|
| Backend (Azure App Service B1) | https://app-ems-readykit-dev.azurewebsites.net |
| Frontend (Azure Static Web Apps) | https://lively-bush-0ed75ca10.7.azurestaticapps.net |
| API docs (non-prod only) | https://app-ems-readykit-dev.azurewebsites.net/docs |
| CI/CD trigger | Push to `main` → GitHub Actions |
| Terraform | `iac/Terraform/` — delete delete-lock before apply |

**Session AF deploy confirmed live** (2026-06-19) — Compliance Calendar fixes, PAR-B1
par-level reactivation, and the audit date-range test fix all verified in production by
Jennifer, alongside a separate quick dependency fix (`pydantic-settings` 2.14.1 → 2.14.2,
GHSA-4xgf-cpjx-pc3j, raised by the `pip-audit` CI gate). `cd app; pytest` (484/484),
`cd app; ruff check .`, `cd app; black --check .`, and `cd frontend; npm test` all
confirmed green before this deploy. **BUG-AF2 redeploy also confirmed live the same day** —
Jennifer re-tested the Station Supplies Count reminder after the first deploy, found the
data-source bug, and confirmed the `getLocationCheckHistory` fix after redeploying.

⚠ No deploy since this planning session — ITM-1..8 has not been built yet.

---

## Files Flagged for Attention

| File | Issue |
|------|-------|
| `app/ems_readykit_dev.db` | Should not be committed; `git rm --cached app/ems_readykit_dev.db`. Will also be wiped and reseeded for ITM-1..8 — no need to preserve current contents (no production data exists). |
| `deploy.zip` | Build artifact in repo root; add to .gitignore + `git rm --cached deploy.zip` |
| `app/tests/test_routers.py` | 67 KB — split by domain when it next needs major additions |
| `frontend/src/modules/admin/components/VehiclesScreen.jsx` | 25 KB — extract sub-components when next modified |
| `frontend/src/styles/wizard.css` | Consolidated from 3 old patch files; ideally moves to `modules/check-wizard/` — defer until next modification |
| `app/tests/_par_level_fix.py` | Stray placeholder file ("# placeholder — this file can be deleted"), not part of the real test suite. Not touched this session. Safe to delete whenever convenient. |

`_session_AE_removed/` (Session AE's staging folder for superseded member-management
files) has been reviewed and deleted — no longer flagged.

---

## Next Session

| Session | Focus | Key Items |
|---------|-------|-----------|
| ✅ **AG** (done) | ITM-1: migration | Added `station_id` FK + per-station unique on `items` (migration 0028); supply catalog scoped to station; all non-seed tests passing (452/484; 32 seed_integrity expected until ITM-4). |
| ✅ **AH** (done) | ITM-3: category_group | Added `category_group` VARCHAR(100) nullable to `Item` (migration 0029); schema updated. 452/484 still passing. |
| ✅ **AI** (done) | ITM-4: seed.py rewrite | `seed.py` fully rewritten: `BASE_ITEM_SEED`, `get_or_create_item(station_id=...)`, `seed_station_catalog()`, canonical names, O2 PSI corrections, LUCAS merge, Fire Extinguisher SUPPLY. `test_seed_integrity.py` 6 test corrections. 484/484 expected after reseed. |
| **AJ** | ITM-5 + ITM-6 | Backend item-endpoint station scoping; frontend Item Catalog scoping + jump-bag/supply-room assignment UI. |
| AJ/AK | ITM-8 | `test_item_station_scoping.py` + doc updates; close the reopened launch gate. |
| *(deferred)* | Post-launch engineering backlog | F-5G3 (CSV export), ADMIN-F10 (member search), TEST-AE1, TEST-AF1, or operational walkthroughs (LAUNCH-OPS1-6) handled directly by the chief — all still waiting behind ITM-1..8. |
