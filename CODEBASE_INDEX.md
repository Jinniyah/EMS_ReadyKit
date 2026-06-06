# EMS ReadyKit — Codebase Index
# Last updated: 2026-06-06 (Session K post-close: migration 0018 fix, POST /stations/{id}/supply-room, supply room setup state)
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
│   ├── tests/                  # pytest suite (250 tests passing)
│   ├── seed.py                 # Dev seed data
│   ├── initial_stock.csv       # 10 seed stock items — upload via Receive New Stock → CSV
│   └── pyproject.toml          # Dependencies + pytest config
├── frontend/                   # React 18 + Vite PWA
│   └── src/
│       ├── modules/            # Feature modules (self-contained)
│       ├── pages/              # Top-level page components
│       ├── shared/             # Cross-module: api, components, hooks, utils
│       └── App.jsx             # Router, auth guard, top-level layout
├── docs/                       # All project documentation
│   ├── backlog.md              # ALL open work items (sessions G–J planned)
│   ├── project_index.md        # Technical reference, API structure, stack
│   ├── backlog_completed.md    # Completed items (Sessions A–F)
│   ├── uat_test_cases.md       # UAT test cases
│   └── adr/                   # Architecture Decision Records (ADR-001–005)
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
| `stations.py` | 9 KB | `/stations` | All / Admin | CRUD; GET /my; GET supply-room (404 if missing); POST supply-room (get-or-create + Shelf 1–4) |
| `station_members.py` | 8 KB | `/stations/{id}/members` | Supervisor+ | Membership management |
| `vehicles.py` | 6 KB | `/vehicles` | All + membership | Vehicle CRUD; OOS/RTS status toggle |
| `checks.py` | 20 KB | `/checks/daily` | All + membership | Check wizard: create, draft save, line-item updates, submit; `GET /daily/last-readings` returns last quantity_found + readings per item for vehicle/location |
| `check_history.py` | 7 KB | `/checks/daily` | All / Supervisor+ | Read-only history; soft-delete; acknowledgement; `my-history` accepts optional `station_id` filter |
| `repair_requests.py` | 9 KB | `/vehicles/{id}/repair-requests` | All roles | File, update, resolve repair requests |
| `inventory.py` | 28 KB | `/inventory` | All + membership | Locations, compartments, par levels, lots, stock summary, CSV receive. `GET /supply-catalog?station_id=` (SR-B1). `PATCH /supply-catalog/items/{id}/count` (SR-B2). `PUT /lots/{id}` (Supervisor+). Transfer endpoint removed (SR-B5). |
| `items.py` | 3 KB | `/items` | All | Item catalog search and detail |
| `admin.py` | 29 KB | `/admin` | Admin (most) / Supervisor+ | Stations, vehicles, items, par levels, CSV import, members |
| `audit.py` | 2 KB | `/audit` | Supervisor+ | Paginated audit event log |

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
| `station.py` | `Station` | primary_color (0011), call_sign (0012) |
| `vehicle.py` | `Vehicle` | vehicle_color (0011); status ACTIVE/OOS |
| `inventory_location.py` | `InventoryLocation` | LocationType: VEHICLE, JUMP_BAG, STATION_SUPPLY_ROOM |
| `compartment.py` | `Compartment` | sort_order, location_description |
| `par_level.py` | `ParLevel` | item ↔ compartment; min/max quantity; active flag (0010); priority_check + priority_question (0015) |
| `stock_lot.py` | `StockLot` | lot_number, expiration_date, quantity |
| `item.py` | `Item` | ItemCheckType enum: SUPPLY, MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT; `station_supply` bool (migration 0017) |
| `daily_inventory_check.py` | `DailyInventoryCheck` | status computed server-side; started_by/completed_by; vehicle_id nullable + location_id (0013) for portable checks |
| `check_line_item.py` | `CheckLineItem` | quantity_found/needed; measurement_value; functional_pass; LineItemStatus |
| `controlled_substance_check.py` | `ControlledSubstanceCheck` | dual-signature; ALS vehicles only |
| `repair_request.py` | `RepairRequest` | OPEN → IN_PROGRESS → RESOLVED; corrective_action prefix sentinel |
| `station_member.py` | `StationMember` | user_id = email (JWT preferred_username) |
| `audit_event.py` | `AuditEvent` | Immutable; write via `core/audit.py` |
| `stock_transfer.py` | `StockTransfer` | Transfer record: from/to location, item, qty, FIFO lot snapshot; from_location_id nullable (null = external receipt) |

### Domain model hierarchy
```
Station
 └── Vehicle (ALS / BLS / QRV)
      ├── InventoryLocation (VEHICLE — auto-created)
      │    └── Compartment
      │         ├── ParLevel  (item → min/max qty; active flag)
      │         └── StockLot  (lot# + expiry + qty)
      └── DailyInventoryCheck (vehicle_id nullable since 0013)
           ├── CheckLineItem  (per-item result)
           ├── ControlledSubstanceCheck
           └── RepairRequest (OPEN→IN_PROGRESS→RESOLVED)

InventoryLocation (JUMP_BAG / STATION_SUPPLY_ROOM — station-scoped)
 └── DailyInventoryCheck (via location_id — portable location checks, 0013)

StationMember  (user ↔ station)
AuditEvent     (immutable log)
```

---

## Backend — Core (app/ems_readykit/core/)

| File | Purpose |
|------|---------|
| `config.py` | `get_settings()` — env vars, feature flags, is_production, is_sqlite |
| `auth.py` | `resolve_current_user()`, `CurrentUser`, role constants, Azure AD JWT RS256 validation |
| `database.py` | `get_db()` FastAPI dependency; engine + session factory |
| `audit.py` | `write_audit_event()` — use this everywhere, not inline AuditEvent() |
| `logging.py` | `configure_logging()`, `set_request_id()` |

---

## Backend — Tests (app/tests/)

| File | Size | Coverage |
|------|------|----------|
| `test_routers.py` | 67 KB | Main router integration tests (bulk of 217 tests) |
| `test_supply_room.py` | 12 KB | Supply room: SR-B1/B2/B3/B4 (10+4+2+1 tests), transfer history; SR-B5 transfer removed |
| `test_repair_requests.py` | 17 KB | Repair request lifecycle |
| `test_station_membership.py` | 15 KB | RBAC + station membership enforcement |
| `test_check_history.py` | 15 KB | Check history, soft-delete, acknowledgement |
| `test_admin_items.py` | 12 KB | Admin item management, par levels, CSV |
| `test_models.py` | 7 KB | Model-level unit tests |
| `conftest.py` | 4 KB | Shared fixtures: in-memory SQLite, test client, user factories |

Run tests: `cd app && pytest` (uses SQLite in-memory; no external services needed) — **250 tests passing**

**Test isolation note:** Route handlers that call `db.commit()` release the active SQLAlchemy savepoint. SQLite's in-memory engine does not fully undo released savepoints on outer transaction rollback. Any fixture creating a row with a UNIQUE constraint must use **get-or-create semantics** (see `test_item` and `vehicle_location` fixtures in `test_supply_room.py` for the pattern).

---

## Frontend — Modules (frontend/src/modules/)

Each module is self-contained with its own `index.jsx`, `api/`, `components/`.

### check-wizard/  (PWA 5-step check flow)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 15 KB | Wizard orchestration, step routing, draft state |
| `components/Step1Vehicle.jsx` | 14 KB | Vehicle selection + CS check toggle |
| `components/Step2Compartments.jsx` | 14 KB | Priority items section (inline confirm) + compartment list with reading confirmations (MEASUREMENT/FUNCTIONAL/DATE_RECORD with last values), No Change / Modify / stock preview. Short count based on last check quantity_found, not stock lots. |
| `components/Step3Items.jsx` | 7 KB | Item counting per compartment |
| `components/ItemRow.jsx` | 16 KB | Per-item row — all check types (supply/measurement/functional/date) |
| `components/Step4Reconcile.jsx` | 13 KB | Flagged items review |
| `components/Step4Review.jsx` | 7 KB | Final summary before submit |
| `components/Step5Submit.jsx` | 9 KB | Submission + CS check dual-sign |
| `components/SubmittedScreen.jsx` | 6 KB | Post-submit confirmation |
| `components/DraftBanner.jsx` | 5 KB | Resume-draft prompt on load |
| `components/WizardProgress.jsx` | 3 KB | Top progress bar |

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

### admin/  (Station administration)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 21 KB | Admin hub: 3 nav cards → Members / Items / Vehicles screens |
| `components/MembersScreen.jsx` | 3 KB | Member management entry |
| `components/MemberList.jsx` | 3 KB | Active members list |
| `components/AddMemberForm.jsx` | 4 KB | Add/invite member form |
| `components/VehiclesScreen.jsx` | 25 KB | Vehicle + compartment CRUD, par assignment entry |
| `components/ItemCatalog.jsx` | 9 KB | Item search + list |
| `components/ItemForm.jsx` | 16 KB | Add/edit item form |
| `components/ItemAssignments.jsx` | 18 KB | Par level assignment — item-centric (vehicle→compartment cascade) |
| `components/CompartmentParLevels.jsx` | — | Par level assignment — vehicle-centric (per-compartment item list with add/edit/remove) |
| `components/CsvImport.jsx` | 8 KB | Bulk item import with template download |

### supply-room/  (Station Supplies — redesigned Session K)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 6 KB | Landing: 2 large cards (View Supplies, Count Supplies) + secondary text links. Detects 404 → shows setup state with "Set Up Supply Room" button (calls POST supply-room). |
| `supply-room.css` | — | All supply-room CSS using design tokens. RestockVehicle styles removed (SR-F6). `.sr-setup` setup-state styles added. |
| `api/supplyApi.js` | 3 KB | API: getSupplyRoom, createSupplyRoom (POST), catalog (SR-B1), patchCount (SR-B2), putLot (SR-F7), CSV, station locations |
| `components/SupplyCatalogView.jsx` | — | SR-F3: catalog from SR-B1; "On hand / Par" color-coded; inline count correction (Supervisor+); lot expiry editor (SR-F7) |
| `components/StockSummaryView.jsx` | 6 KB | Legacy stock summary view — superseded by SupplyCatalogView for View Supplies |
| `components/RestockVehiclePanel.jsx` | 9 KB | Retired — no longer imported or routed. Kept for historical reference. |
| `components/ReceiveStockPanel.jsx` | 8 KB | Manual add + CSV bulk upload |
| `components/TransferHistory.jsx` | 4 KB | Inbound/outbound transfer log |

**Key architectural note — vehicle location_id:** `VehicleRead` does not expose `location_id`. To get a vehicle's inventory location ID, call `GET /inventory/locations?station_id=` and match on `vehicle_id + location_type === 'VEHICLE'`. This is the same pattern used by the check wizard.

### vehicles/  (V&E Status)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 4 KB | Vehicle list with open-issue badges |
| `components/VehicleCard.jsx` | 9 KB | Vehicle detail + OOS/RTS toggle |
| `components/RepairRequestList.jsx` | 12 KB | Repair request list + status lifecycle |
| `components/RepairRequestForm.jsx` | 4 KB | File new repair request |

### check-history/
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 6 KB | My Checks / All Checks tabs + detail navigation |
| `components/` | — | Check list items and detail view |

---

## Frontend — Shared (frontend/src/shared/)

### api/
| File | Purpose |
|------|---------|
| `client.js` | Axios instance; base URL from VITE_API_BASE_URL; auth token injector |
| `authConfig.js` | MSAL config: tenant ID, client ID, scopes |
| `stationsApi.js` | Shared `getMyStations` — imported by checkApi + adminApi (deduplication) |

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
| `UserPill.jsx` | Auth'd user display + role badge (top-right of every screen) |
| `ItemSearchCombobox.jsx` | Typeahead search with 150ms debounce, keyboard nav, text highlighting |
| `LastCheckBanner.jsx` | Last check status banner for home screen |
| `ColorPickerWidget.jsx` | Station/vehicle color picker (shared across admin screens) |
| `ErrorBoundary.jsx` | Top-level error boundary |
| `Modal.jsx` | Reusable modal dialog |
| `DevBanner.jsx` | Dev/staging environment indicator |
| `StatusBadge.jsx` | Check/repair status badge |
| `Spinner.jsx` | Loading indicator |

### pages/
| File | Purpose |
|------|---------|
| `HomePage.jsx` | Post-auth landing: station picker, module cards, last-check banner, issue badges |
| `NotFoundPage.jsx` | 404 page |

---

## Migrations (app/alembic/versions/)

18 migrations applied (0001–0018, plus 0003a branch). Run automatically at startup via `startup.sh`.
To add a new migration: `cd app && alembic revision --autogenerate -m "description"`

Key recent migrations:
- **0013** — `vehicle_id` nullable on `daily_inventory_checks`; adds `location_id` FK for portable checks
- **0014** — `stock_transfers` table; backfills 4 default compartments for any supply room with zero compartments
- **0015** — `priority_check` + `priority_question` on `par_levels`; `requires_full_check` on `compartments`
- **0016** — `is_damaged` (bool) on `check_line_items`; batch mode
- **0017** — `station_supply` (bool NOT NULL DEFAULT TRUE) on `items`; batch mode; SR-M1
- **0018** — backfills `STATION_SUPPLY_ROOM` location + Shelf 1–4 compartments for active stations that lack one

---

## Deployment

| Resource | Value |
|----------|-------|
| Backend (Azure App Service) | https://app-ems-readykit-dev.azurewebsites.net |
| Frontend (Azure Static Web Apps) | https://lively-bush-0ed75ca10.7.azurestaticapps.net |
| API docs (non-prod only) | https://app-ems-readykit-dev.azurewebsites.net/docs |
| CI/CD trigger | Push to `main` → GitHub Actions |

---

## Files Flagged for Attention

| File | Issue |
|------|-------|
| `app/ems_readykit_dev.db` | Should not be committed; add to .gitignore, run `git rm --cached` |
| `deploy.zip` | Build artifact in repo root; should be in .gitignore |
| `app/tests/test_routers.py` | 67 KB — candidate for splitting by domain area |
| `frontend/src/modules/admin/index.jsx` | 21 KB — candidate for sub-screen extraction |
| `frontend/src/modules/admin/components/VehiclesScreen.jsx` | 25 KB — candidate for splitting |
| `frontend/src/modules/check-wizard/components/ItemRow.jsx` | 16 KB — complex, touch carefully |
| `frontend/staticwebapp.config.json` | NEW — CSP, HSTS, X-Frame-Options, SWA routing fallback (SEC-PRE1) |
| `frontend/.eslintrc.cjs` | NEW — ESLint 8 config (eslint:recommended + react-hooks) |

---

## Next Sessions (from backlog.md)

| Session | Focus | Key Items |
|---------|-------|-----------|
| **G** | Supply Room & Restocking | ✅ Complete |
| **Pre-H** | Code Cleanup + Security | ✅ Complete |
| **H** | Security + Deployment + RX-F7/F1/F2/F8/F9 | ✅ Complete |
| **I** | Reading confirmations, vehicle on-hand fix, No Change bugs | ✅ Complete |
| **J** | UX Polish, CH-F7/F8 CSS, B-E8, DMG-F1 | ✅ Complete |
| **K** | Supply Room Redesign (SR-M1/SEED1/B1–B5/F1–F7) | ✅ Complete — 250 tests passing |
| **L** | Priority Admin UI + Deferred UX | RX-B2, RX-F12, RX-F3/F4/F5, RX-F9b, F-UX10 |
