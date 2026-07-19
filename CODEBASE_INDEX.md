# EMS ReadyKit — Codebase Index

# After reading this, load only the sections relevant to the current task.
# Full project state → docs/project_index.md | Open work → docs/backlog.md

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
│   ├── tests/                  # pytest suite (562 collected; 562 passing — ITM-4 resolved 32 seed_integrity failures; ITM-5 added 14; Session AO added 32; Session AS/ONBOARD-1 net +27: 28 new Marcellus tests, -1 obsolete test_unit_540_is_als)
│   ├── seed.py                 # Dev seed data — ITM-4 rewrite complete (Session AI). BASE_ITEM_SEED, station-scoped items, Newberg + Marcellus full par levels (Session AS/ONBOARD-1), Training/Test catalog only.
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
│   ├── backlog_completed.md    # Completed items (Sessions A–AR) + changelog archive
│   ├── architecture.md         # Component diagram and networking notes
│   ├── runbook.md              # Infrastructure deployment, validation, teardown
│   ├── osi_security_review.md  # OSI layer security analysis with gap/action list
│   ├── models/                 # Real inventory checklist photos (712, jump bag) — ITM-2 source
│   ├── evidence/                # UAT screenshots and supporting artifacts
│   ├── templates/               # Document templates
│   └── adr/                   # Architecture Decision Records (ADR-001–006)
├── iac/                        # Terraform (Azure infra)
├── .github/workflows/          # CI/CD (pip-audit → test → build → deploy)
├── CLAUDE.md                   # Rules for AI-assisted development
├── CODEBASE_INDEX.md           # This file
├── CONTRIBUTING.md             # Local setup, dev workflow, contribution guidelines
└── README.md                   # Public-facing project overview
```

---

## Backend — Routers (app/ems_readykit/routers/)

All routes are prefixed `/api/v1/`. Router registration order in main.py matters (station_members before stations; check_history before checks).

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
| `items.py` | 3 KB | `/items` | Supervisor+ (create/edit) / All (read) | Item catalog; `POST /items` is SUPERVISOR_PLUS (not admin-only); deactivation is ADMIN_ONLY via admin router. Note: `GET /items` is not station-scoped (it's a lightweight read-only catalog; scoping lives in the admin routes via ITM-5). |
| `admin_items.py` | — | `/admin` | Admin (most) / Supervisor+ | Item catalog admin, par levels, CSV import (split from monolithic admin.py, CQ-B5). **ITM-5 ✅ (Session AJ):** All 11 routes now require `station_id` and call `require_station_membership` before any data access. `_conflict_on_name` is per-station; `_conflict_on_barcode` remains global. `POST /admin/items/{id}/assign` (`assign_item_to_compartment`) reactivates a matching soft-deactivated `(item_id, compartment_id)` par level instead of inserting a duplicate (PAR-B1, Session AF) — see note below. Already accepts `location_id` for any `InventoryLocation` (vehicle, jump bag, or supply room) — the frontend (`ItemAssignments.jsx`) just never exposes jump-bag/supply-room options yet (ITM-6). |
| `admin_vehicles.py` | — | `/admin` | Admin | Vehicle color and details admin (split from monolithic admin.py, CQ-B5) |
| `admin_stations.py` | — | `/admin` | Admin | `POST /admin/stations` (ADMIN-B15, auto-creates supply room + StationMember). `PATCH /admin/locations/{id}` renames a location label (SS-B1). `GET /admin/retired?type=&station_id=` lists retired vehicles/locations/stations (RET-B4). `GET /admin/email-alignment-check?station_id=&include_inactive=` — flags StationMember rows whose `user_id` doesn't look like a valid email (blank, contains whitespace, missing `@`/domain, not lowercase); read-only diagnostic for catching display-name-instead-of-email mistakes from manual add or CSV import (LAUNCH-OPS9, Session AC). |
| `usage.py` | 9 KB | `/checks` | All + membership | `POST /checks/usage` (log items used, FIFO decrement); `GET /checks/usage/station/{id}` (history); `GET /checks/usage/station/{id}/frequent` (top 10 items, 90-day window) |
| `audit.py` | 2 KB | `/audit` | Supervisor+ | Paginated audit event log; `GET /audit?from_date=&to_date=` date-range filter (B-E18). Unmodified across Session AF — two separate suspicions about a naive/aware datetime comparison here were each checked via isolated repro and ruled out; the real bug both times was on the test side (global-table pollution, then a local-vs-UTC date computed in the wrong timezone). See `docs/backlog_completed.md` Session AF write-up for the full two-pass diagnosis before touching this file's date filters. |

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
| `config.py` | `get_settings()` — env vars, feature flags, is_production, is_sqlite, enable_api_docs (secure-by-default, decoupled from is_production — SEC-03, Session AR) |
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
| `test_admin_items.py` | 12 KB | Admin item management, par levels, CSV. Session AJ: 2 test fixes (role case "SUPERVISOR"→"Supervisor" in station_id fixture; missing `station_id=` param in deactivated-item list test). | `db` |
| `test_item_station_scoping.py` | — | NEW (Session AJ, ITM-5/8). 14 tests, 5 classes: list/search scoped to station; create without membership → 403; per-station name uniqueness; get/edit cross-station → 403; Admin bypasses all checks. `two_stations` fixture creates Station A+B, adds supervisor to A only. | `db` |
| `test_models.py` | 7 KB | Model-level unit tests | `db` |
| `test_priority_items.py` | — | AED + LUCAS all check types; legal immutability; FAIL preservation; priority flag DB persistence | `db` |
| `test_persona_responder.py` | — | Responder: all 5 check types; FAIL+comment+continue; multiple checks/day; role boundary | `db` |
| `test_persona_supervisor.py` | — | Supervisor: check history; damaged item regression; repair requests; station today view | `db` |
| `test_persona_admin.py` | — | Admin: supply room decrement; FUNCTIONAL items excluded; role alias regression; admin-only deactivation boundary | `db` |
| `test_safety_checks.py` | — | O2 PSI below minimum → LOW; date recurrence overdue → OVERDUE; requires_full_check enforcement (422 on missing items) | `db` |
| `test_seed_integrity.py` | — | Verifies seeded dev DB: Unit 712, PC 8, AED/LUCAS items, O2 PSI minimums, Truck Operations, jump bags. Session AS (ONBOARD-1) added 28 tests: Marcellus fleet composition (612/632/621), Unit 612's 21-compartment/153-par-level layout incl. `requires_full_check`, reused-item spot checks (Run Box, Blankets, Duct Tape, AED/LUCAS priority wording), and Fuel Level as a FUNCTIONAL pass/fail check; Units 632/621's compartment/par-level counts, shared Under Hood items, Tire Pressure & Depth (16 items, PSI gauge confirmed, threshold still open), Gas Meter Reading (PSI gauge confirmed, threshold still open), `station_supply=False` on fire-truck items. Uses a new `_item_for_station()` helper (station-scoped, unlike the pre-existing `_item()`) since BASE_ITEM_SEED items are created once per station (ITM-1) and a bare name lookup is ambiguous for anything shared across stations. Same session: a clean reseed surfaced that this file's pre-existing (pre-ONBOARD-1) station-name lookups had silently drifted from current `seed.py` -- `"Newberg Township Station 1"`/`"Marcellus Township Station 1"` (trailing "1") only ever matched a long-stale local dev DB, never the actual current seed data; corrected to `"Newberg Township Station"`/`"Marcellus Township Station"` and removed the now-obsolete `test_unit_540_is_als` (Unit 540 no longer exists, renamed to 612/BLS). | `seeded_db` |
| `test_usage.py` | — | POST /checks/usage happy path, FIFO decrement, non-SUPPLY rejection, 403/404 guards; GET history + frequent items | `db` |
| `test_retirement.py` | — | RET-B1–B6: retire vehicle/location/station/lot; list retired; 403/409 enforcement. | `db` |
| `test_damaged_items.py` | — | SUP-DMG1: damaged items endpoint; happy path; retired excluded; inactive excluded; station isolation; RBAC. 13 tests. | `db` |
| `test_email_alignment.py` | — | LAUNCH-OPS9: `GET /admin/email-alignment-check` — valid emails pass clean; display-name/malformed/uppercase/blank user_id flagged; inactive row inclusion toggle; cross-station scan; RBAC (Admin only). 12 tests. (Session AC) | `db` |

**Run:** `cd app; pytest` — 562 tests collected, **562 passing** (Session AS: net +27 from ONBOARD-1 — 28 new Marcellus tests, -1 obsolete `test_unit_540_is_als` removed since Unit 540 no longer exists). `ruff check .` confirmed green; `black` is not installed in the current venv (not run this session).

**Two DB fixtures — do not mix:**
- `db` — in-memory SQLite, empty, rolls back after each test. Use for all API/logic tests.
- `seeded_db` — read-only connection to `ems_readykit_dev.db`. Use ONLY in `test_seed_integrity.py`. Skips if dev DB absent. Never write to it.

**Test isolation note:** Route handlers that call `db.commit()` release the active SQLAlchemy savepoint — committed rows are NEVER rolled back between tests within a pytest session; this is permanent for the rest of that `pytest` invocation, not just "until the next fixture teardown." Any fixture creating a row with a UNIQUE constraint must use get-or-create semantics (see `test_item` and `vehicle_location` fixtures in `test_supply_room.py`), AND any test asserting against a broad/global query (e.g. unscoped `GET /audit`) must instead scope its own query (station_id, vehicle_id, etc.) to the data it itself created — see `test_par_level_reactivation.py`'s per-test `compartment` fixture and `test_routers.py`'s Session AF audit-date-range fixes for two different examples of this same underlying constraint.

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
| `components/ComplianceCalendar.jsx` | — | Calendar view of check compliance. Rewritten Session AF: week view = active (non-retired) vehicles + jump bags only; Station Supply Room intentionally excluded from week view (periodic count, not daily — would just be empty space). Month view = combined vehicle/jump-bag picker (`EntityPicker`) + traditional grid. The `SupplyRoomReminder` strip lives directly under the Week/Month toggle (visible in both views, moved there mid-session per UAT feedback that a chip buried in month view would get seen far less often). Supply room fetched via `supervisorApi.getSupplyRoomLocation`, which filters out a retired supply room client-side; its check history is fetched via `supervisorApi.getLocationCheckHistory` (BUG-AF2 fix — NOT `getComplianceRange`, which is range-capped and cannot answer "most recent ever"). Has an explicit error state (`.cal__supply-reminder--error`) instead of silently rendering as if no count existed. No test file yet — see TEST-AF1 in `docs/backlog.md`. |
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
| `components/ItemCatalog.jsx` | — | Item catalog browser. **ITM-6 ✅ (Session AK):** station-scoped (`stationId` → `adminApi.listItems`); 7 cabinet-group chip filters (Airway/Wound Care/PPE/Diagnostic/Medications/Documents/Vehicle Ops) replace old 4-category chips; groups items by `category_group` (falls back to `category` when null); fetches `getStationLocations` and passes `locations` to each `ItemAssignments`. |
| `components/ItemForm.jsx` | 16 KB | Add/edit item form |
| `components/ItemAssignments.jsx` | — | Par level assignment — item-centric. **ITM-6 ✅ (Session AK):** `AddAssignmentForm`/`EditRow` now have a "Where" picker (Vehicle / Jump Bag / Station Supply Room). Vehicles use `vehicle_id`; jump bags and supply room use `location_id`. Supply room auto-selects. Compartments loaded via `getVehicleCompartments` (vehicle) or `getLocationCompartments` (other). Assignment display row shows `vehicle_number ?? location_label`. Button renamed to "+ Add assignment". **ITM-7 ✅ (Session AN):** After a successful assign, shows inline confirmation ("✓ Assigned to …") with "+ Assign to another location" (resets form, carries min/max) and "Done" (closes panel) instead of collapsing. |
| `components/CompartmentParLevels.jsx` | — | Par level assignment — per-compartment item list. Accepts `vehicleId` OR `locationId` (for supply room / portable locations). Priority checkbox + question field (RX-F12). Remove → re-add round trip fixed by PAR-B1 (Session AF) — this was the exact UI path the bug was reported through. |
| `components/StationSuppliesScreen.jsx` | — | SS-F1: Admin screen — manage supply room shelves and their par levels. Fetches supply room → compartments → CompartmentParLevels per shelf. |
| `components/PortableLocationsScreen.jsx` | — | ADMIN-F7: Full CRUD for portable locations (Jump Bags). List → create → rename + ShelfManager (compartment CRUD + par levels). |
| `components/CsvImport.jsx` | 8 KB | Bulk item import with template download |
| `api/adminApi.js` | — | Station CRUD, item catalog, par levels, vehicles, portable locations. **No longer has member endpoints** — those moved to `api/membersApi.js` (Session AE). **ITM-6 ✅:** `listItems` and `searchItems` now accept `stationId` option and append `station_id=` to the query string. |
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

### help/  (Help & Tutorial screen — Session AQ)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Role-aware help screen. Crew-member section (7 accordions: shift-start check, after-call logging, status colors, missed checks, missing/expired items, repair reporting, auto-save draft). Supervisor section (4 accordions: compliance dashboard, FAIL triage, adding members, supply room stock — shown only when `canAccess(user, 'supervisor')`). Quick Reference grid (home screen buttons, role-filtered). "Show me the basics again" button + header button render `Tutorial` as overlay; `onDone` stays on Help screen, does not clear `ems_tutorial_complete`. No API calls — all content is static JSX. |
| `help.css` | — | Scoped to `.help-screen`. Accordion trigger/body/chevron, 2-col quick-reference grid (`.help-quick-grid`/`.help-quick-item`), replay button. Tokens only — no hardcoded hex/px. |

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


---

## Frontend — Tests (frontend/src/)

Vitest + React Testing Library. Run: `cd frontend && npm test` — **233 tests passing**
(Session AN, 2026-06-22). 9 new `ItemAssignments` tests added this session.

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
| `modules/admin/__tests__/ItemCatalog.test.jsx` | 15 | Item list, search, Add button role-gating, Admin inactive toggle. **ITM-6 ✅ (Session AK):** 3-mock `setupApiMocks` (vehicles/items/locations); `ITEMS_WITH_CABINET` fixture; 4 new cabinet chip filter tests. |
| `modules/admin/__tests__/ItemAssignments.test.jsx` | 9 | NEW (Session AN, ITM-7/8). Vehicle/jump bag/supply room assignment payload shapes; supply room auto-select; assignment display row (`location_label` for non-vehicle). Confirmation state after assign (Done button, Assign gone, text contains vehicle+compartment); "+ Assign to another location" resets form + carries min/max; Done closes panel. `mockImplementation` by `typeof deps[0]` distinguishes assignments vs. compartments `useApi` calls. |
| `modules/admin/__tests__/VehiclesScreen.test.jsx` | 3 | New file, Session AD (BUG-AD1) — this screen had no prior test coverage. Retired vehicle excluded by default; still excluded after toggling "Show out-of-service vehicles"; empty-state message reflects only active vehicles. |
| `modules/admin/__tests__/EmailAlignmentSection.test.jsx` | 17 | Moved from `modules/settings/__tests__/` (Session AE) — same coverage, new home. LAUNCH-OPS9 UI: Run Check button + clean/flagged states; Notify panel recipient checkboxes (excludes flagged person); custom email chips; Draft Email enable/disable; drafted preview with mailto link. |
| `modules/check-history/__tests__/CheckHistory.test.jsx` | 9 | My Checks, All Checks tab (Supervisor+), Deleted tab |
| `modules/usage-log/__tests__/UsageItemPicker.test.jsx` | 13 | Catalog, search, +/- controls, selected, sections |
| `modules/usage-log/__tests__/UsageLogScreen.test.jsx` | 6 | Multi-vehicle picker, single-vehicle skip, payload, error |


**Mock infrastructure:**
- `src/shared/hooks/__mocks__/useAuth.jsx` — configurable useAuth with Responder/Supervisor/Admin personas
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
| `ItemSearchCombobox.jsx` | Typeahead search with 150ms debounce, keyboard nav, text highlighting. **ITM-6 ✅:** `stationId` prop (optional) passed to `adminApi.searchItems` so results are scoped to the caller's station. Threaded through all callers: `CompartmentParLevels` + `ReceiveStockPanel`. |
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


---

## Seed Data (app/seed.py, app/seed_training.py)

Reseed sequence: `cd app; Remove-Item ems_readykit_dev.db; alembic upgrade head; python seed.py`

**Structure:** `BASE_ITEM_SEED` (~100+ canonical items) → `seed_station_catalog(db, station_id)` bootstraps each station → `build_ambulance_inventory`/`build_jump_bag` add Newberg's real par levels.

| Station | Vehicles / Locations | Notes |
|---------|---------------------|-------|
| Newberg Township Station | Unit 712 (BLS) + Unit 712 Jump Bag + Supply Room | Full par levels from real 712 + jump bag inventory forms. PC 8 has all 6 AED/LUCAS items (LUCAS Device merged). |
| Marcellus Township Station | Unit 612 (BLS, renamed in place from placeholder "540"/ALS) + Unit 632 (QRV fire engine) + Unit 621 (QRV fire engine) + Supply Room | ONBOARD-1 (Session AS): full par levels from Jennifer's real inventory forms. 33 compartments / 264 par levels across the 3 vehicles (612: 21 compartments/153 par levels incl. Fuel Level as a FUNCTIONAL pass/fail check; 632: 5/56; 621: 7/55). Built via `build_marcellus_ambulance_inventory`/`build_fire_truck_632_inventory`/`build_fire_truck_621_inventory` — not `build_ambulance_inventory` (612's layout is not 712's PC1-PC18). Fire-truck items live in the shared `BASE_ITEM_SEED` (category_group="Vehicle Operations", station_supply=False) so Newberg's/Training's not-yet-onboarded fire trucks pick them up automatically. Open items: Tire PSI (632) and Gas Meter Reading (621) are both confirmed PSI gauges (same pattern as On-Board O2 PSI) but still have no confirmed min/max threshold — see `docs/backlog_completed.md` Session AS write-up. |
| Newberg Training Station (orange) | Training Unit A/B + Jump Bag A/B + Supply Room | Catalog only — par levels assigned via admin UI. |
| ⚠ TEST STATION | Unit TEST (QRV) + Supply Room | Catalog + 7 `[TEST]`-prefixed items; no par levels; dev only. |

**Key seed decisions (ITM-2/4):**
- One canonical item per real-world thing reused across compartments via separate `ParLevel` rows (e.g. "Gauze, 3x3" → ambulance PC18 + jump bag Front Pocket + supply room shelf).
- O2 PSI: On-Board 500–2200 (large tank, unchanged); Stretcher + Jump Bag 200–500 (small tank, corrected).
- LUCAS Device merges former "LUCAS Device Ready Check" — one FUNCTIONAL priority item, `priority_check=True`.
- Fire Extinguisher: SUPPLY (not FUNCTIONAL) in both PS EC2 and Truck Operations.
- New item: "Stretcher Battery Date of Last Charge" (DATE_RECORD, recurrence=90).
- `station_supply=False` baked into `BASE_ITEM_SEED` for AED/LUCAS/medication items.

`seed_training.py` — always seeded including production via `startup.sh` Pass 2 (Session AB). Newberg Training Station (orange, `#e65100`): two BLS ambulances (Training Unit A/B) + two jump bags (Training Jump Bag A/B), ~1/3 of Unit 712's inventory across nine compartments, all six check types including AED/LUCAS priority items.

---

## Deployment

| Resource | Value |
|----------|-------|
| Backend (Azure App Service B1) | https://app-ems-readykit-dev.azurewebsites.net |
| Frontend (Azure Static Web Apps) | https://lively-bush-0ed75ca10.7.azurestaticapps.net |
| API docs (opt-in, ENABLE_API_DOCS=false by default) | https://app-ems-readykit-dev.azurewebsites.net/docs — 404 unless ENABLE_API_DOCS=true, decoupled from APP_ENV (SEC-03, Session AR) |
| CI/CD trigger | Push to `main` → GitHub Actions |
| Terraform | `iac/Terraform/` — delete delete-lock before apply |
| Key Vault network access | App subnet (`snet-app`) must have the `Microsoft.KeyVault` service endpoint AND be listed in the Key Vault's `network_acls.virtual_network_subnet_ids` — `bypass="AzureServices"` alone does NOT cover a generic App Service reading its own secrets. Missing this pairing caused a full outage (SEC-03 incident, Session AR): managed identity Key Vault calls failed with `ForbiddenByFirewall`, `DATABASE_URL` never resolved, app failed to boot. |

---

## Files Flagged for Attention

| File | Issue |
|------|-------|
| `app/tests/test_routers.py` | 67 KB — split by domain when it next needs major additions |
| `frontend/src/modules/admin/components/VehiclesScreen.jsx` | 25 KB — extract sub-components when next modified |
| `frontend/src/styles/wizard.css` | Consolidated from 3 old patch files; ideally moves to `modules/check-wizard/` — defer until next modification |

