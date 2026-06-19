# EMS ReadyKit — Codebase Index
# Last updated: 2026-06-19 (Session AD: BUG-AD1 retired vehicle leak fixed across 4 frontend files)
# PURPOSE: Load this file at the start of every session to orient quickly.
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
│   ├── tests/                  # pytest suite (468+ tests — see CLAUDE.md for current baseline)
│   ├── seed.py                 # Dev seed data (Newberg 712 BLS + 712 Jump Bag; Marcellus 540 ALS; TEST station)
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
│   ├── backlog_completed.md    # Completed items (Sessions A–AD)
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
| `stations.py` | 11 KB | `/stations` | All / Admin | CRUD; GET /my; GET supply-room (404 if missing); POST supply-room (get-or-create + Shelf 1–4); `GET /stations/{id}/expiring-soon` includes EXPIRY_DATE check-type items (SUP-F3); `GET /stations/{id}/settings` (Supervisor+, CH-B8); `PATCH /stations/{id}/settings` (Admin only, CH-B7); `PATCH /stations/{id}/retire` (Admin, RET-B3); `GET /stations/{id}/damaged-items` (Supervisor+, SUP-DMG1). |
| `station_members.py` | 8 KB | `/stations/{id}/members` | Supervisor+ | Membership management; CSV bulk import + template download (ACC-B8) |
| `vehicles.py` | 6 KB | `/vehicles` | All + membership | Vehicle CRUD; OOS/RTS status toggle; `PATCH /vehicles/{id}/retire` (Admin, RET-B1) — sets `retired_at`, `retired_by`, `retirement_reason`, AND `active=False`. Frontend must check `retired_at` directly, not just `active` (see BUG-AD1, Session AD). |
| `checks.py` | 26 KB | `/checks/daily` | All + membership | Check wizard: create with embedded line_items; `_compute_line_item_status`; `_auto_decrement_supply_room` (SR-B4, N+1 batched PERF-1); `_reconcile_supply_room_check` (SR-B5 — called on STATION_SUPPLY_ROOM submission; reconciles quantity_found back to StockLot quantities FIFO); helpers: `_resolve_check_location`, `_enforce_full_check_compartments`, `_build_lot_map`, `_build_line_items` (CQ-B3); `GET /daily/last-readings` |
| `check_history.py` | 7 KB | `/checks/daily` | All / Supervisor+ | Read-only history; soft-delete; acknowledgement; hard-delete (Admin only); `my-history` accepts optional `station_id` filter |
| `repair_requests.py` | 9 KB | `/vehicles/{id}/repair-requests` | All roles | File, update, resolve repair requests; `resolution_notes` required on RESOLVED |
| `inventory.py` | 28 KB | `/inventory` | All + membership | Locations, compartments, par levels, lots, stock summary, CSV receive. `GET /supply-catalog?station_id=` (SR-B1). `PATCH /supply-catalog/items/{id}/count` (SR-B2). `PUT /lots/{id}` (SR-F7). `PATCH /inventory/items/{id}/status` marks/clears damaged. `PATCH /locations/{id}/retire` (Admin, RET-B2). `GET /lots/retired?location_id=` (Supervisor+, RET-B6). `PATCH /lots/{id}/retire` (Supervisor+, RET-B5) — registered BEFORE `/lots/{lot_id}` to avoid path ambiguity. `PATCH /par-levels/{id}` soft-deactivate with reason + membership check (B-E9). |
| `items.py` | 3 KB | `/items` | Supervisor+ (create/edit) / All (read) | Item catalog; `POST /items` is SUPERVISOR_PLUS (not admin-only); deactivation is ADMIN_ONLY via admin router |
| `admin_items.py` | — | `/admin` | Admin (most) / Supervisor+ | Item catalog admin, par levels, CSV import (split from monolithic admin.py, CQ-B5) |
| `admin_vehicles.py` | — | `/admin` | Admin | Vehicle color and details admin (split from monolithic admin.py, CQ-B5) |
| `admin_stations.py` | — | `/admin` | Admin | `POST /admin/stations` (ADMIN-B15, auto-creates supply room + StationMember). `PATCH /admin/locations/{id}` renames a location label (SS-B1). `GET /admin/retired?type=&station_id=` lists retired vehicles/locations/stations (RET-B4). `GET /admin/email-alignment-check?station_id=&include_inactive=` — flags StationMember rows whose `user_id` doesn't look like a valid email (blank, contains whitespace, missing `@`/domain, not lowercase); read-only diagnostic for catching display-name-instead-of-email mistakes from manual add or CSV import (LAUNCH-OPS9, Session AC). |
| `usage.py` | 9 KB | `/checks` | All + membership | `POST /checks/usage` (log items used, FIFO decrement); `GET /checks/usage/station/{id}` (history); `GET /checks/usage/station/{id}/frequent` (top 10 items, 90-day window) |
| `audit.py` | 2 KB | `/audit` | Supervisor+ | Paginated audit event log; `GET /audit?from_date=&to_date=` date-range filter (B-E18) |

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
| `par_level.py` | `ParLevel` | item ↔ compartment; min/max quantity; active flag (0010); `priority_check` + `priority_question` (0015); `is_damaged` (bool); `deactivated_at` + `deactivation_reason` (0024) |
| `stock_lot.py` | `StockLot` | lot_number, expiration_date, quantity; retired_at/by/reason (0023) |
| `item.py` | `Item` | ItemCheckType enum: SUPPLY, MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, EXPIRY_DATE (Session O — stored as VARCHAR, no migration); `station_supply` bool (migration 0017, default True); `measurement_minimum`/`measurement_maximum`; `recurrence_days`; `check_type_value` property (CQ-B1) |
| `daily_inventory_check.py` | `DailyInventoryCheck` | CheckStatus: PASS/NEEDS_RESTOCK/FAIL; status computed server-side; vehicle_id nullable + location_id (0013) for portable checks; soft-delete fields (deleted_at/by/reason, force_deleted) |
| `check_line_item.py` | `CheckLineItem` | LineItemStatus: OK/SHORT/LOW/MISSING/EXPIRED/FAIL/OVERDUE; quantity_found/needed; measurement_value; functional_pass; date_value |
| `controlled_substance_check.py` | `ControlledSubstanceCheck` | dual-signature; ALS vehicles only |
| `repair_request.py` | `RepairRequest` | OPEN → IN_PROGRESS → RESOLVED; `resolution_notes` required on resolve |
| `station_member.py` | `StationMember` | user_id = email (JWT preferred_username); ACC-B7 unique constraint is `(station_id, user_id, role)` — supports multiple roles per person via multiple rows |
| `audit_event.py` | `AuditEvent` | Immutable; write via `core/audit.py::write_audit_event(actor=, metadata=)` |
| `stock_lot.py` | `StockLot` | Transfer record: from/to location, item, qty, FIFO lot snapshot |
| `usage_event.py` | `UsageEvent`, `UsageEventItem` | After-call usage log. UsageEvent → station/vehicle/performed_by/timestamp/notes. UsageEventItem → item_id + quantity_used. Lazy selectin on vehicle + items. |

### ⚠ Critical frontend convention: active vs retired_at (BUG-AD1, Session AD)
`active` (temporary, reversible — Mark Out of Service / Return to Service) and
`retired_at` (permanent — Settings → Retire) are **independent fields** on Vehicle,
InventoryLocation, Station, and StockLot. Retiring sets `active=False` as a side
effect, so checking `active` alone happens to exclude retired records *today*, but
that's incidental, not guaranteed. **Every frontend list/action that touches one of
these models must filter `!v.retired_at` explicitly**, the same way `usage-log/index.jsx`
already did before this was a documented rule. Already fixed: `VehiclesScreen.jsx`,
`vehicles/index.jsx` + `VehicleCard.jsx`, `HomePage.jsx`'s `useStationIssues`,
`check-wizard/components/Step1Vehicle.jsx`. If a new screen lists vehicles/locations,
check this convention before shipping it.

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
| `audit.py` | `write_audit_event(actor=, metadata=)` — always use this, never inline AuditEvent() |
| `logging.py` | `configure_logging()`, `set_request_id()` |
| `limiter.py` | `slowapi` Limiter singleton; `DAILY_CHECK_RATE_LIMIT` constant. `TESTING=true` (set by conftest.py) switches to 99999/min so tests never exhaust the counter. |

---

## Backend — Tests (app/tests/)

| File | Size | Coverage | DB Fixture |
|------|------|----------|------------|
| `conftest.py` | 5 KB | Fixtures: in-memory SQLite (`db`), seeded dev DB (`seeded_db`), test client, auth headers | — |
| `test_routers.py` | 67 KB | Main router integration tests | `db` |
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

**Run:** `cd app; pytest` — see `backlog.md` / `CLAUDE.md` for current passing-count baseline (468+ as of Session AB; Session AC adds 12 new tests in `test_email_alignment.py`). Session AD (BUG-AD1) was a frontend-only fix — no backend tests added.

**Two DB fixtures — do not mix:**
- `db` — in-memory SQLite, empty, rolls back after each test. Use for all API/logic tests.
- `seeded_db` — read-only connection to `ems_readykit_dev.db`. Use ONLY in `test_seed_integrity.py`. Skips if dev DB absent. Never write to it.

**Test isolation note:** Route handlers that call `db.commit()` release the active SQLAlchemy savepoint. Any fixture creating a row with a UNIQUE constraint must use get-or-create semantics. See `test_item` and `vehicle_location` fixtures in `test_supply_room.py`.

---

## Frontend — Modules (frontend/src/modules/)

Each module is self-contained with its own `index.jsx`, `api/`, `components/`.

### check-wizard/  (PWA 5-step check flow)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 15 KB | Wizard orchestration, step routing, draft state. Passes `selectionLabel` to `WizardProgress`. |
| `components/Step1Vehicle.jsx` | 14 KB | Vehicle/location selection + CS check toggle; detects `draft._supplyRoom` for supply room wizard path. `isCheckableVehicle(v)` helper checks both `active !== false` AND `!retired_at` (defensive fix, BUG-AD1 Session AD — this path was already safe via a side effect of the server-side `active=true` filter, but now checks `retired_at` directly instead of relying on that). |
| `components/Step2Compartments.jsx` | 14 KB | Priority items section (inline confirm) + compartment list with reading confirmations; No Change / Modify / stock preview. Short count based on last check quantity_found. Reading confirmation rows are suppressed for `requires_full_check` compartments. Calls `onCompartmentsLoaded(compartments)` via `useEffect` so wizard index can populate `compartmentList` for progress bar, Step3 nav, and Step5 summary. |
| `components/Step3Items.jsx` | 7 KB | Item counting per compartment |
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
| `index.jsx` | 7 KB | Dashboard entry; loads supply alerts (SR-B3) for SupplyLowStockPanel |
| `components/ComplianceCalendar.jsx` | 15 KB | Calendar view of check compliance |
| `components/CheckDetailPanel.jsx` | 9 KB | Drill-down check detail — read-only + comments only |
| `components/VehicleComplianceCard.jsx` | 7 KB | Per-vehicle compliance summary card |
| `components/PortableComplianceCard.jsx` | — | Per-portable-location compliance summary card |
| `components/ExpiringItemsPanel.jsx` | — | SUP-F3: expandable expiring lots panel |
| `components/SupplyLowStockPanel.jsx` | — | SR-F5: expandable supply low-stock panel; red if out, amber if below par |
| `components/DamagedItemsPanel.jsx` | — | SUP-DMG1: collapsible panel listing damaged items (item name, vehicle, compartment). allClear only when no FAIL + no damaged items. |

### admin/  (Station administration — Option B layout: station header + 3 nav cards)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 21 KB | Admin hub: 3 nav cards → Members / Items / Vehicles screens |
| `components/MembersScreen.jsx` | 3 KB | Member management entry |
| `components/MemberList.jsx` | 3 KB | Active members list |
| `components/AddMemberForm.jsx` | 4 KB | Add/invite member form |
| `components/VehiclesScreen.jsx` | 25 KB | Vehicle + compartment CRUD, par assignment entry. Display filter excludes retired vehicles outright (`!v.retired_at`), independent of the "Show out-of-service vehicles" toggle (BUG-AD1, Session AD). `VehicleAdminCard` shows a "Retired" badge + retirement reason and hides Edit/Color-still-shown/OOS-RTS/compartment-edit controls for retired vehicles. |
| `components/ItemCatalog.jsx` | 9 KB | Item search + list (also reused as View Supplies interface in supply room) |
| `components/ItemForm.jsx` | 16 KB | Add/edit item form |
| `components/ItemAssignments.jsx` | 18 KB | Par level assignment — item-centric |
| `components/CompartmentParLevels.jsx` | — | Par level assignment — per-compartment item list. Accepts `vehicleId` OR `locationId` (for supply room / portable locations). Priority checkbox + question field (RX-F12). |
| `components/StationSuppliesScreen.jsx` | — | SS-F1: Admin screen — manage supply room shelves and their par levels. Fetches supply room → compartments → CompartmentParLevels per shelf. |
| `components/PortableLocationsScreen.jsx` | — | ADMIN-F7: Full CRUD for portable locations (Jump Bags). List → create → rename + ShelfManager (compartment CRUD + par levels). |
| `components/CsvImport.jsx` | 8 KB | Bulk item import with template download |

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

### settings/  (Station configuration — Session Q, Supervisor+; Admin sections — Session R)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Settings screen orchestration. Admin: EmailAlignmentSection + StationManagementSection + VehicleManagementSection + RetiredListSection. allow_check_modification toggle for all admins. Supervisor: read-only label. |
| `api/settingsApi.js` | — | `getSettings(stationId, getToken)`, `updateSettings(stationId, payload, getToken)` |
| `api/membersApi.js` | — | Member CRUD + CSV import/template (ACC-B6/B7/B8). `checkEmailAlignment(stationId, getToken)` — calls `GET /admin/email-alignment-check?station_id=` (LAUNCH-OPS9). |
| `api/retirementApi.js` | — | `getStationVehicles`, `getStationLocations`, `retireVehicle`, `retireLocation`, `retireStation`, `getRetired` |
| `components/VehicleManagementSection.jsx` | — | S-F7/RET-F1/F2: lists active vehicles + portable locations with Retire buttons |
| `components/StationManagementSection.jsx` | — | S-F6/RET-F4: station info + Retire Station button |
| `components/RetiredListSection.jsx` | — | RET-F5: collapsible ▲/▼ section; three sub-lists |
| `components/MemberManagementSection.jsx` | — | ACC-B6/B7/B8: member list, edit name, multi-role display, CSV import |
| `components/EmailAlignmentSection.jsx` | — | LAUNCH-OPS9, Admin only. "Run Check" button calls `membersApi.checkEmailAlignment`; shows clean state or flagged-issue list. On flagged result, "Notify Someone About This" expands a panel: checkbox-select existing Administrators/Supervisors (excluding anyone themselves flagged) via `membersApi.listMembers`, or add freeform emails. "Draft Email" builds a plain-text body summarizing the issues and renders a preview with a `mailto:` link ("Open in Mail App") — no email account is connected in this environment, so nothing sends automatically. |
| `settings.css` | — | Token-based CSS. 60px tap targets. `.email-alignment__*` classes added Session AC. |

---

## Frontend — Tests (frontend/src/)

Vitest + React Testing Library. Run: `cd frontend && npm test` — see `backlog.md` for current passing-count baseline.

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
| `modules/check-history/__tests__/CheckHistory.test.jsx` | 9 | My Checks, All Checks tab (Supervisor+), Deleted tab |
| `modules/usage-log/__tests__/UsageItemPicker.test.jsx` | 13 | Catalog, search, +/- controls, selected, sections |
| `modules/usage-log/__tests__/UsageLogScreen.test.jsx` | 6 | Multi-vehicle picker, single-vehicle skip, payload, error |
| `modules/settings/__tests__/EmailAlignmentSection.test.jsx` | 17 | LAUNCH-OPS9 UI: Run Check button + clean/flagged states; Notify panel recipient checkboxes (excludes flagged person); custom email chips; Draft Email enable/disable; drafted preview with mailto link. (Session AC) |

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
| `useApi.js` | Thin wrapper: `{ data, loading, error }` for API calls |

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

27 migrations applied (0001–0027, plus 0003a branch). Run automatically at startup via `startup.sh`.
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

---

## Seed Data (app/seed.py, app/seed_training.py)

`seed.py` — idempotent operational seed, dev-only. Reseed sequence: `Remove-Item ems_readykit_dev.db; alembic upgrade head; python seed.py`

| Station | Vehicles / Locations | Notes |
|---------|---------------------|-------|
| Newberg Township Station 1 | Unit 712 (BLS) + Unit 712 Jump Bag | 26+ compartments on 712; PC 8 has all AED/LUCAS items |
| Marcellus Township Station 1 | Unit 540 (ALS) | ALS drug cabinet (PC 9 ALS) |
| ⚠ TEST STATION | Unit TEST (QRV) | 2 compartments, 7 items, all check types; dev only |

**Unit 710 Jump Bag:** removed from seed (v1.66) — Unit 710 has no ambulance yet.

`seed_training.py` — always seeded, including production, via `startup.sh` Pass 2 (Session AB). Newberg Training Station (orange, `#e65100`): two BLS ambulances (Training Unit A/B) + two jump bags (Training Jump Bag A/B), ~1/3 of Unit 712's inventory across nine compartments, all six check types represented including AED/LUCAS priority items.

**Priority items seeded:** AED Battery (`priority_check=True`, `priority_question="AED shows READY?"`); LUCAS Device (`priority_check=True`, `priority_question="LUCAS shows READY?"`).

**Non-supply items** (`station_supply=False`): AED/LUCAS items, all medications and drug bags.

---

## Deployment

| Resource | Value |
|----------|-------|
| Backend (Azure App Service B1) | https://app-ems-readykit-dev.azurewebsites.net |
| Frontend (Azure Static Web Apps) | https://lively-bush-0ed75ca10.7.azurestaticapps.net |
| API docs (non-prod only) | https://app-ems-readykit-dev.azurewebsites.net/docs |
| CI/CD trigger | Push to `main` → GitHub Actions |
| Terraform | `iac/Terraform/` — delete delete-lock before apply |

---

## Files Flagged for Attention

| File | Issue |
|------|-------|
| `app/ems_readykit_dev.db` | Should not be committed; `git rm --cached app/ems_readykit_dev.db` |
| `deploy.zip` | Build artifact in repo root; add to .gitignore + `git rm --cached deploy.zip` |
| `app/tests/test_routers.py` | 67 KB — split by domain when it next needs major additions |
| `frontend/src/modules/admin/components/VehiclesScreen.jsx` | 25 KB — extract sub-components when next modified |
| `frontend/src/styles/wizard.css` | Consolidated from 3 old patch files; ideally moves to `modules/check-wizard/` — defer until next modification |

---

## Next Session

| Session | Focus | Key Items |
|---------|-------|-----------|
| **AE** | Post-launch engineering backlog | F-5G3 (CSV export), ADMIN-F10 (member search), or operational walkthroughs (LAUNCH-OPS1-6) handled directly by the chief |
