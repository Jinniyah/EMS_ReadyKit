# EMS ReadyKit -- Project Index
# Last updated: 2026-06-23 (Session AQ)

This document is the technical reference for EMS ReadyKit. It covers what is
currently built and deployed, the key decisions made along the way, and where
to find more detail.

For a feature overview and getting started, see the [README](../README.md).

---

## Current System State

**Production launched 2026-06-23.** EMS ReadyKit is live with a real volunteer
EMS team (Newberg Township). The pre-launch item-model rework (ITM-1 through
ITM-8) and a pre-deploy correctness/security sweep are both complete and
deployed. Remaining work is post-launch: two operational walkthrough tasks
(EMS chief's responsibility) and a post-launch engineering backlog -- see
`docs/backlog.md`.

### Deployed and running

| Component | Status | Notes |
|-----------|--------|-------|
| Azure infrastructure (Terraform) | Live | North Central US |
| FastAPI backend | Live | https://app-ems-readykit-dev.azurewebsites.net |
| React PWA frontend | Live | https://lively-bush-0ed75ca10.7.azurestaticapps.net |
| Azure AD authentication | Live | RS256 JWT; three app roles (Administrator, Supervisor, Responder) |
| RBAC enforcement | Live | Role + station membership enforced on all endpoints; items additionally scoped per-station |
| GitHub Actions CI/CD | Live | pip-audit to test to build to deploy on push to main |
| Alembic migrations | Live | 29 migrations applied; runs automatically on startup |

### What's built -- backend

| Area | Status | Notes |
|------|--------|-------|
| Stations, vehicles, inventory locations | Complete | Three location types: VEHICLE, JUMP_BAG, STATION_SUPPLY_ROOM |
| Compartments and par levels | Complete | priority_check, priority_question, requires_full_check, is_damaged, deactivated_at/reason; reactivates on re-add instead of duplicating (PAR-B1) |
| Daily inventory checks (all 6 check types) | Complete | SUPPLY, MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, EXPIRY_DATE |
| Controlled substance checks | Complete | Dual-signature; ALS vehicles only |
| Repair requests (full lifecycle) | Complete | OPEN to IN_PROGRESS to RESOLVED; resolution_notes required |
| Check history, acknowledgement, soft-delete | Complete | Supervisor+ soft-delete; Admin hard-delete; 90-day retention |
| Audit events | Complete | Immutable; all material actions logged with actor + metadata; date-range filter |
| Station membership and access control | Complete | Role + station-scoped; Administrator bypasses station check; CSV bulk import + template download; multi-role support per person |
| Email alignment diagnostic | Complete | Admin-only check flagging malformed/blank/uppercase `user_id` entries from manual add or CSV import |
| Station settings | Complete | allow_check_modification toggle (Admin write, Supervisor+ read) |
| Item catalog -- per-station scoping | Complete | `station_id` FK + per-station unique name (ITM-1); `category_group` for cabinet-style grouping (ITM-3); all admin routes enforce station membership (ITM-5) |
| Supply room | Complete | Auto-created on station create; SR-B1/B2/B3/B4; auto-decrement on vehicle check; reconcile on supply-room-only check submission (SR-B5) |
| Supply room: item catalog view | Complete | SR-B1: station_supply=True + excludes FUNCTIONAL; grouped by shelf with is_damaged |
| Supply room: stock count correction | Complete | SR-B2: PATCH /supply-catalog/items/{id}/count (Supervisor+) |
| Supply room: low-stock alerts | Complete | SR-B3: inline on supervisor dashboard |
| Supply room: auto-decrement | Complete | SR-B4: fires on vehicle check submit; FIFO; best-effort; never blocks |
| Damaged items endpoint | Complete | Station-scoped; excludes retired/inactive; surfaced on supervisor dashboard |
| After-call usage log | Complete | POST /checks/usage; FIFO decrement; GET history + frequent items (90-day window) |
| Admin item catalog (CRUD + CSV import) | Complete | SUPERVISOR_PLUS create/edit; ADMIN_ONLY deactivate; dedicated `ItemUpdate` schema (omits immutable station_id) prevents 422s on edit; AI identification fields (ADMIN_ONLY) |
| Admin par level assignment | Complete | Any location type (vehicle, jump bag, supply room); priority flags; deactivate with reason; reactivation preserves history |
| Admin location rename | Complete | PATCH /admin/locations/{id} (Admin only) |
| Portable locations CRUD | Complete | JUMP_BAG creation, rename, compartment management |
| Vehicle/location/station retirement | Complete | Soft-retire with reason; list retired endpoints; retired_at filter on list_locations |
| Stock lot retirement | Complete | PATCH /lots/{id}/retire (Supervisor+); GET /lots/retired |
| Rate limiting | Complete | slowapi on check creation; TESTING env var disables in test suite |
| Expiring soon endpoint | Complete | GET /stations/{id}/expiring-soon includes EXPIRY_DATE items |
| AI fields endpoint | Complete | PATCH /admin/items/{id}/ai-fields (Admin only) |
| Real Azure AD JWT validation | Complete | RS256 signature, audience, issuer, expiry, and tenant-claim validation; dedicated test coverage with a session-scoped test keypair (test_auth.py) |

### What's built -- frontend

| Module | Status | Notes |
|--------|--------|-------|
| Check wizard (5 steps, all check types, draft save) | Complete | Priority items section; No Change/Modify flow; reading confirmations; EXPIRY_DATE Same/Different UX; supply room path via `draft._supplyRoom` |
| Vehicle and Equipment Status | Complete | Full repair lifecycle UI; OOS/RTS toggle; retired vehicles show a Retired badge and hide OOS/RTS/repair controls |
| Check history (My Checks, All Checks, detail view) | Complete | Read-only; acknowledgement for Supervisor+; Deleted tab for Admin |
| Supervisor compliance dashboard | Complete | Low-stock alerts inline; expiring items panel; damaged items panel; vehicle + portable compliance cards |
| Compliance calendar | Complete | Week and month views; jump bags included; supply room count reminder strip; tap-to-detail |
| Station administration | Complete | Single Members screen (multi-role grouping, name edit, CSV import, email alignment check); station-scoped item catalog with cabinet-group chip filters; "Where" picker for assigning items to vehicle/jump bag/supply room in one flow with inline multi-location confirmation |
| Supply room (View Supplies, Count Supplies, Receive Stock) | Complete | Shelf grouping; damaged badge; lot expiry correction; lot retirement; usage log view |
| Station Supplies admin screen | Complete | Per-shelf par level management; add items to shelves |
| Portable locations screen | Complete | CRUD for jump bags; compartment management; par levels |
| After-call usage log | Complete | Vehicle picker (auto-skip for single-vehicle); item picker with Used Most Often section; history view |
| Settings | Complete | allow_check_modification toggle (Admin); vehicle/location/station retirement (Admin); retired list. Member UI moved entirely to Station Administration -> Members |
| Help & Tutorial screen | Complete | Role-aware accordion guidance (crew + supervisor sections); Quick Reference grid; replayable tutorial overlay; static content, no API calls |
| Responder plain-English labels | Complete | Jargon replaced; plain-English error messages throughout |

### Test suite

| Metric | Value |
|--------|-------|
| Backend tests passing | 530 |
| Frontend tests passing | 233 |
| Known xfails | 0 |
| Known CVEs (pip-audit) | 0 |
| Test database (unit/integration) | SQLite in-memory (db fixture); no external services required |
| Test database (seed integrity) | ems_readykit_dev.db (seeded_db fixture, read-only) |
| Coverage areas | All 6 check types; RBAC; station membership; per-station item scoping; repair requests; check history; supply room; usage log; retirement; damaged items; email alignment; persona flows (Responder/Supervisor/Admin); safety checks (O2 PSI, date recurrence, requires_full_check); seed data integrity; admin items; real RS256 JWT validation |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](adr/ADR-001-Architecture.md) | Single-app, single-datastore, single-region | Accepted |
| [ADR-002](adr/ADR-002-RBAC.md) | Group-based Azure AD RBAC + application-layer station membership | Accepted |
| [ADR-003](adr/ADR-003-Logging-and-Audit.md) | Explicit audit events; centralized Log Analytics | Accepted |
| [ADR-004](adr/ADR-004-Terraform-Module-Structure.md) | Modular Terraform by architectural responsibility | Accepted |
| [ADR-005](adr/ADR-005-Frontend-Architecture.md) | React PWA; modular with ErrorBoundary isolation; localStorage draft | Accepted |
| [ADR-006](adr/ADR-006-Azure-AD-Token-Lifetime.md) | Azure AD token lifetime and HTTPS redirect strategy | Accepted |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Status computed server-side | Tamper-resistant; correct semantics regardless of client |
| EXPIRED beats MISSING | Conservative compliance -- expired item is a failure regardless of count |
| Worst-case check status | One FAIL triggers whole check FAIL; NEEDS_RESTOCK is second worst; OVERDUE maps to FAIL |
| `performed_by` from JWT | Identity cannot be spoofed; bound server-side at submission time |
| Station membership enforced per-request | Crews only access assigned station; Admins bypass for cross-station reporting |
| Items scoped per-station | One station's catalog and item names never collide with another's; supply catalog and par levels inherit the scoping |
| `check_date` server-derived from timestamp | Client cannot back-date a check |
| Soft-delete with 90-day retention | Checks recoverable; matches EMS record retention norms |
| Repair requests: all roles advance to In Progress | Routine repairs do not require supervisor to acknowledge being handled |
| `draft._supplyRoom` sentinel | Supply room uses same check wizard; Step1Vehicle detects flag and skips vehicle selection |
| `station_supply=False` on AED/LUCAS/medications | Not stockable consumables; excluded from supply catalog by SR-B1 |
| Auto-decrement: vehicle checks only | `_auto_decrement_supply_room` fires only when `payload.vehicle_id` is set |
| Supply room reconcile on supply-room check | `_reconcile_supply_room_check` treats `quantity_found` as new absolute truth and FIFO-adjusts stock lots, never raises |
| Par level reactivation, not duplication | Re-adding a previously-removed item to the same compartment reactivates the original row (preserving `par_id` and history) instead of failing on a stale unique-constraint row |
| Draft key includes `started_at` | Enables multiple in-progress checks for same vehicle on same day |
| Last-known station cached in localStorage | Draft banners show immediately before station API returns |
| `active` and `retired_at` are independent | Temporary out-of-service (`active`) and permanent retirement (`retired_at`) are separate fields; every list/action touching vehicles, locations, stations, or lots must filter `retired_at` explicitly, not rely on `active` alone |
| `member_id`, not `user_id`, for membership PATCH/DELETE | A person can hold multiple roles as separate rows with the same `user_id`; only `membersApi.js` may call member endpoints |
| Build zip on Linux in CI | Windows Compress-Archive creates backslash paths that Oryx cannot extract |
| pip-audit as CI gate | Dependency CVEs caught before deploy |
| Check history is read-only legal record | Submitted checks cannot be modified; repair resolution creates a separate record |
| `requires_full_check` on Truck Operations | Blocks No Change -- responder must physically verify every item |
| Retired locations excluded from list_locations | `retired_at IS NULL` filter on GET /inventory/locations; prevents orphan UI entries |
| `ems-confirm-*` shared CSS pattern | Single confirm sheet definition in index.css; used by settings, supply-room, and any future module |
| Persona-based test suite | Tests mirror real user flows: Responder (tired responder), Supervisor (non-tech supervisor), Admin (volunteer admin) |
| `seeded_db` fixture for seed integrity | Connects to real dev DB; skips if absent; never writes; isolated from in-memory test DB |
| No Change line items skip all reading types | MEASUREMENT, FUNCTIONAL, DATE_RECORD items must be confirmed inline; submitting null values causes MISSING/FAIL |
| No hard delete on items | `items.item_id` is a NOT NULL FK across check line items, stock lots, transfers, and usage event items; the lifecycle is deactivate + "Show inactive" toggle, not delete |

---

## Domain Model

```
Station
 +-- Vehicle (ALS / BLS / QRV)
 |    +-- InventoryLocation (VEHICLE type, auto-created)
 |    |    +-- Compartment (requires_full_check on Truck Operations)
 |    |         +-- ParLevel  (item, min/max qty, priority_check, is_damaged, deactivated_at)
 |    |         +-- StockLot  (lot#, expiry, qty, retired_at)
 |    +-- DailyInventoryCheck (check_date server-derived, status, performed_by from JWT)
 |         +-- CheckLineItem  (LineItemStatus: OK/SHORT/LOW/MISSING/EXPIRED/OVERDUE/FAIL)
 |         +-- ControlledSubstanceCheck (dual-signature, ALS only)
 |         +-- RepairRequest  (OPEN to IN_PROGRESS to RESOLVED, resolution_notes required)
 |
 +-- InventoryLocation (JUMP_BAG / STATION_SUPPLY_ROOM -- station-scoped)
 |    +-- DailyInventoryCheck (via location_id for portable checks)
 |
 +-- UsageEvent (after-call log: station, vehicle, performed_by, timestamp)
      +-- UsageEventItem (item_id, quantity_used; triggers FIFO stock decrement)

Item            (station_id FK; unique per (station_id, name); category_group)
StationMember   (user_id = email from JWT preferred_username; unique per (station_id, user_id, role))
AuditEvent      (immutable; actor= + metadata=; written via core/audit.py)
```

---

## API Structure

All routes are prefixed `/api/v1/`. Router registration order in `main.py` matters
(station_members before stations; check_history before checks; lots/retired before lots/{id}).

| Group | Prefix | Access | Notes |
|-------|--------|--------|-------|
| Stations | `/stations` | Admin (list all); All (list own via /my) | POST supply-room: get-or-create (Supervisor+); GET expiring-soon; GET/PATCH settings; PATCH retire (Admin) |
| Vehicles | `/vehicles` | All + membership | OOS/RTS toggle (Supervisor+); PATCH retire (Admin) |
| Inventory | `/inventory` | All + membership | Supply catalog, par levels, lots, stock summary; retired_at filter on list_locations |
| Daily checks | `/checks/daily` | Submit: all roles; History: Supervisor+ | Single POST with embedded line_items; status computed server-side; rate-limited; date-range list (90-day cap) vs. unbounded per-vehicle/location list are separate endpoints with different intended uses |
| Usage log | `/checks/usage` | All + membership | POST log items used; GET history; GET frequent items (90-day) |
| CS checks | `/checks/controlled-substance` | All roles (ALS only) | Dual-signature required |
| Repair requests | `/vehicles/{id}/repair-requests` | File: all; Resolve: Supervisor+ | resolution_notes required on RESOLVED |
| Check history | `/checks/daily/{id}` | Supervisor+ | Read-only; soft-delete; acknowledgement; hard-delete (Admin) |
| My history | `/checks/daily/my-history` | All roles | Own history; optional station_id filter |
| Items | `/items` | Supervisor+ (write); All (read) | POST is SUPERVISOR_PLUS -- not Admin-only; read is a lightweight catalog, not itself station-scoped (scoping lives in the admin routes) |
| Admin items | `/admin` (admin_items.py) | Supervisor+ (most); Admin (deactivate) | All routes require `station_id` + station membership; dedicated `ItemUpdate` schema for edits |
| Admin vehicles | `/admin` (admin_vehicles.py) | Admin | Vehicle color and detail admin |
| Admin stations | `/admin` (admin_stations.py) | Admin | Station creation; location rename; retired list; email alignment check |
| Station members | `/stations/{id}/members` | Supervisor+ | member_id-based PATCH/DELETE; CSV bulk import + template download |
| Audit | `/audit` | Supervisor+ | Paginated; from_date/to_date filter |

Full interactive docs (non-prod): https://app-ems-readykit-dev.azurewebsites.net/docs

---

## Migrations (29 applied)

| Migration | Description |
|-----------|-------------|
| 0001-0009 | Initial schema: stations, vehicles, checks, audit, items (ai_tags, alternate_names, barcode) |
| 0010 | active flag on par_levels |
| 0011 | primary_color on stations; vehicle_color on vehicles |
| 0012 | call_sign on stations |
| 0013 | vehicle_id nullable on daily_inventory_checks; location_id FK for portable checks |
| 0014 | stock_transfers table; backfills 4 default compartments for supply rooms with zero |
| 0015 | priority_check + priority_question on par_levels; requires_full_check on compartments |
| 0016 | is_damaged (bool) on check_line_items; batch mode |
| 0017 | station_supply (bool NOT NULL DEFAULT TRUE) on items; batch mode |
| 0018 | Backfills STATION_SUPPLY_ROOM location + Shelf 1-4 for active stations lacking one |
| 0019 | Composite index on daily_inventory_checks(station_id, check_date) |
| 0020 | usage_events + usage_event_items tables; indexes on station_id and timestamp |
| 0021 | UPDATE items: AED Pads to EXPIRY_DATE check_type |
| 0022 | allow_check_modification Boolean on stations (NOT NULL, server_default=True) |
| 0023 | retired_at, retired_by, retirement_reason on vehicles, inventory_locations, stations, stock_lots |
| 0024 | deactivated_at + deactivation_reason on par_levels |
| 0025 | check_date Date type fix; inline unnamed FK removed from batch_alter_table for SQLite + PostgreSQL compat |
| 0026 | check_date String(10) to Date type |
| 0027 | station_members unique constraint changed to (station_id, user_id, role) -- supports multiple roles per person |
| 0028 | items.station_id FK (NOT NULL); uq_items_station_name(station_id, name) replaces global unique on name. Raw SQL (not batch mode) -- see Migration conventions in CONTRIBUTING.md |
| 0029 | items.category_group VARCHAR(100) nullable; batch mode |

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Cloud | Microsoft Azure | -- |
| IaC | Terraform | 1.6+ |
| Backend | FastAPI | 0.136.1 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13+ |
| Validation | Pydantic | 2.13.4 |
| Rate limiting | slowapi | -- |
| Database (prod) | PostgreSQL (Azure Flexible Server) | 16 |
| Database (dev/test) | SQLite | -- |
| Runtime | Python | 3.11 |
| ASGI server | Gunicorn + UvicornWorker | -- |
| Authentication | Azure Active Directory | RS256 JWT |
| CI/CD | GitHub Actions | -- |
| Frontend | React 18 + Vite (PWA) | -- |
| Frontend hosting | Azure Static Web Apps | Free tier |
| Testing | pytest 9.0 (backend); Vitest + React Testing Library (frontend) |

---

## Document Map

| Document | For |
|----------|-----|
| [README.md](../README.md) | Anyone evaluating or getting started |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Developers setting up locally or contributing |
| [CLAUDE.md](../CLAUDE.md) | AI-assisted development rules and patterns |
| [CODEBASE_INDEX.md](../CODEBASE_INDEX.md) | File map, test suite, migrations, flagged debt |
| [docs/project_index.md](project_index.md) | System state, decisions, API structure, stack |
| [docs/backlog.md](backlog.md) | All open work items -- single source of truth |
| [docs/backlog_completed.md](backlog_completed.md) | Completed items (Sessions A through AQ) + changelog archive |
| [docs/adr/](adr/) | Architecture Decision Records (ADR-001 through ADR-006) |
| [docs/architecture.md](architecture.md) | Component diagram and networking overview |
| [docs/runbook.md](runbook.md) | Infrastructure deployment, validation, teardown |
| [docs/osi_security_review.md](osi_security_review.md) | OSI layer security analysis with gap/action list |
