# EMS ReadyKit — Project Index
# Last updated: 2026-06-08 (Session L post-close)

This document is the technical reference for EMS ReadyKit. It covers what is
currently built and deployed, the key decisions made along the way, and where
to find more detail.

For a feature overview and getting started, see the [README](../README.md).

---

## Current System State

### Deployed and running

| Component | Status | Notes |
|-----------|--------|-------|
| Azure infrastructure (Terraform) | ✅ Live | North Central US |
| FastAPI backend | ✅ Live | https://app-ems-readykit-dev.azurewebsites.net |
| React PWA frontend | ✅ Live | https://lively-bush-0ed75ca10.7.azurestaticapps.net |
| Azure AD authentication | ✅ Live | RS256 JWT; three app roles (Administrator, Supervisor, Responder) |
| RBAC enforcement | ✅ Live | Role + station membership enforced on all endpoints |
| GitHub Actions CI/CD | ✅ Live | pip-audit → test → build → deploy on push to main |
| Alembic migrations | ✅ Live | 18 migrations applied; runs automatically on startup |

### What's built — backend

| Area | Status | Notes |
|------|--------|-------|
| Stations, vehicles, inventory locations | ✅ Complete | Three location types: VEHICLE, JUMP_BAG, STATION_SUPPLY_ROOM |
| Compartments and par levels | ✅ Complete | priority_check, priority_question, requires_full_check, is_damaged |
| Daily inventory checks (all 5 check types) | ✅ Complete | SUPPLY, MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT |
| Controlled substance checks | ✅ Complete | Dual-signature; ALS vehicles only |
| Repair requests (full lifecycle) | ✅ Complete | OPEN → IN_PROGRESS → RESOLVED; resolution_notes required |
| Check history, acknowledgement, soft-delete | ✅ Complete | Supervisor+ soft-delete; Admin hard-delete; 90-day retention |
| Audit events | ✅ Complete | Immutable; all material actions logged with actor + metadata |
| Station membership and access control | ✅ Complete | Role + station-scoped; Administrator bypasses station check |
| Date-range compliance query | ✅ Complete | Max 90-day range; all roles with membership |
| Supply room | ✅ Complete | Auto-created on station create; SR-B1/B2/B3/B4; auto-decrement on vehicle check |
| Supply room: item catalog view | ✅ Complete | SR-B1: station_supply=True + excludes FUNCTIONAL items |
| Supply room: stock count correction | ✅ Complete | SR-B2: PATCH /supply-catalog/items/{id}/count (Supervisor+) |
| Supply room: low-stock alerts | ✅ Complete | SR-B3: inline on supervisor dashboard, no extra tap |
| Supply room: auto-decrement | ✅ Complete | SR-B4: fires on vehicle check submit when qty goes up vs previous check |
| Admin item catalog (CRUD + CSV import) | ✅ Complete | SUPERVISOR_PLUS create/edit; ADMIN_ONLY deactivate |
| Admin par level assignment | ✅ Complete | Vehicle-centric and item-centric views; priority flags |
| Notifications, after-call reset | 📋 Backlog | Session M (RX-B1, RX-F6) |

### What's built — frontend

| Module | Status | Notes |
|--------|--------|-------|
| Check wizard (5 steps, all check types, draft save) | ✅ Complete | Priority items section; No Change / Modify flow; reading confirmations |
| Vehicle & Equipment Status (repair requests, OOS toggle) | ✅ Complete | Full repair lifecycle UI |
| Check history (My Checks, All Checks, detail view) | ✅ Complete | Read-only; acknowledgement for Supervisor+ |
| Supervisor compliance dashboard | ✅ Complete | Low-stock alerts inline (SR-F5); expiring items panel (SUP-F3) |
| Station administration (membership, items, vehicles) | ✅ Complete | Option B layout: 3 nav cards → full-screen sub-screens |
| Supply room (View Supplies, Count Supplies) | ✅ Complete | Session K redesign; supply room setup state for new stations |
| After-call reset (Log Items Used) | 📋 Backlog | Session M (RX-F6) |
| First-run tutorial | 📋 Backlog | RX-F11: 3 screens, shown once |
| Responder language replacement | 📋 Backlog | RX-F10: jargon → plain English throughout |

### Test suite

| Metric | Value |
|--------|-------|
| Total tests passing | 349 |
| Known xfails | 1 (`requires_full_check` enforcement — SEED-GAP2, must fix before launch) |
| Known CVEs (pip-audit) | 0 |
| Test database (unit/integration) | SQLite in-memory (`db` fixture); no external services required |
| Test database (seed integrity) | `ems_readykit_dev.db` (`seeded_db` fixture, read-only) |
| Coverage areas | All 5 check types; RBAC; station membership; repair requests; check history; supply room; persona flows (Jamie/Earl/Jennifer); safety checks (O2 PSI, date recurrence); seed data integrity (Unit 712, PC 8, AED/LUCAS, Truck Operations) |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](adr/ADR-001-Architecture.md) | Single-app, single-datastore, single-region | Accepted |
| [ADR-002](adr/ADR-002-RBAC.md) | Group-based Azure AD RBAC + application-layer station membership | Accepted |
| [ADR-003](adr/ADR-003-Logging-and-Audit.md) | Explicit audit events; centralized Log Analytics | Accepted |
| [ADR-004](adr/ADR-004-Terraform-Module-Structure.md) | Modular Terraform by architectural responsibility | Accepted |
| [ADR-005](adr/ADR-005-Frontend-Architecture.md) | React PWA; modular; localStorage draft with station scoping | Accepted |
| ADR-006 | DDoS Protection Standard cost/benefit | 📋 Needed |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Status computed server-side | Tamper-resistant; correct semantics regardless of client |
| EXPIRED beats MISSING | Conservative compliance — expired item is a failure regardless of count |
| Worst-case check status | One FAIL → whole check FAIL; NEEDS_RESTOCK is second worst; OVERDUE → FAIL |
| `performed_by` from JWT | Identity cannot be spoofed; bound server-side at submission time |
| Station membership enforced per-request | Crews only access assigned station; Admins bypass for cross-station reporting |
| Soft-delete with 90-day retention | Checks recoverable; matches EMS record retention norms |
| Repair request: all roles can mark In Progress | Routine repairs don't require supervisor to acknowledge being handled |
| `draft._supplyRoom` sentinel | Supply room uses same check wizard; Step1Vehicle detects flag and skips vehicle selection |
| `station_supply=False` on AED/LUCAS/meds | These are not stockable consumables; excluded from supply catalog by SR-B1 |
| Auto-decrement: vehicle checks only | `_auto_decrement_supply_room` fires only when `payload.vehicle_id` is set; supply-room-only checks do not trigger it |
| Draft key includes `started_at` | Enables multiple in-progress checks for same vehicle on same day |
| Last-known station cached in localStorage | Draft banners show immediately before station API returns |
| Build zip on Linux in CI | Windows Compress-Archive creates backslash paths that Oryx cannot extract |
| `pip-audit` as CI gate | Dependency CVEs caught before deploy |
| Check history is read-only legal record | Submitted checks cannot be modified; repair resolution creates a separate record |
| `requires_full_check` on compartments | Truck Operations blocks No Change — responder must physically verify every item. **Router enforcement not yet implemented (SEED-GAP2).** |
| Persona-based test suite | Tests mirror real user flows: Jamie (tired responder), Earl (non-tech supervisor), Jennifer (volunteer admin) |
| `seeded_db` fixture for seed integrity | Connects to real dev DB; skips if absent; never writes; isolated from in-memory test DB |

---

## Domain Model

```
Station
 └── Vehicle (ALS / BLS / QRV)
      ├── InventoryLocation (VEHICLE type, auto-created)
      │    └── Compartment (requires_full_check on Truck Operations)
      │         ├── ParLevel  (item → min/max qty; priority_check; is_damaged)
      │         └── StockLot  (lot# + expiry + qty)
      └── DailyInventoryCheck (check_date, status, performed_by from JWT)
           ├── CheckLineItem  (item → LineItemStatus: OK/SHORT/LOW/MISSING/EXPIRED/FAIL/OVERDUE)
           ├── ControlledSubstanceCheck (dual-signature, ALS only)
           └── RepairRequest  (OPEN → IN_PROGRESS → RESOLVED)

InventoryLocation (JUMP_BAG / STATION_SUPPLY_ROOM — station-scoped)
 └── DailyInventoryCheck (via location_id for portable checks)

StationMember  (user ↔ station assignment with role)
AuditEvent     (immutable; actor= + metadata=; written via core/audit.py)
```

---

## API Structure

All routes are prefixed `/api/v1/`.

| Group | Prefix | Access | Notes |
|-------|--------|--------|-------|
| Stations | `/stations` | Admin (list all); All (list own via /my) | POST /stations/{id}/supply-room: get-or-create (Supervisor+) |
| Vehicles | `/vehicles` | All + membership | OOS/RTS toggle (Supervisor+) |
| Inventory | `/inventory` | All + membership | Supply catalog, par levels, lots, stock summary |
| Daily checks | `/checks/daily` | Submit: all roles; Detail: Supervisor+ | Single POST with embedded line_items; status computed server-side |
| CS checks | `/checks/controlled-substance` | All roles (ALS only) | Dual-signature required |
| Repair requests | `/vehicles/{id}/repair-requests` | File: all; Resolve: Supervisor+ | resolution_notes required on RESOLVED |
| Check history | `/checks/daily/{id}` | Supervisor+ | Read-only; soft-delete; acknowledgement |
| My history | `/checks/daily/my-history` | All roles | Own history; optional station_id filter |
| Compliance query | `/checks/daily/station/{id}` | All + membership | Max 90-day range |
| Station today | `/checks/daily/station/{id}/today` | All + membership | Used for shift handoff and home screen badge |
| Items | `/items` | Supervisor+ (write); All (read) | POST /items is SUPERVISOR_PLUS — not admin-only |
| Admin | `/admin` | Supervisor+ (most); Admin (deactivate, create station) | PATCH /admin/par-levels/{id} requires min_quantity + max_quantity |
| Station members | `/stations/{id}/members` | Supervisor+ | |
| Audit | `/audit` | Supervisor+ | Paginated |

Full interactive docs (non-prod): https://app-ems-readykit-dev.azurewebsites.net/docs

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Cloud | Microsoft Azure | — |
| IaC | Terraform | 1.6+ |
| Backend | FastAPI | 0.136.1 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13+ |
| Validation | Pydantic | 2.13.4 |
| Database (prod) | PostgreSQL (Azure Flexible Server) | 16 |
| Database (dev/test) | SQLite | — |
| Runtime | Python | 3.11 |
| ASGI server | Gunicorn + UvicornWorker | — |
| Authentication | Azure Active Directory | RS256 JWT |
| CI/CD | GitHub Actions | — |
| Frontend | React 18 + Vite (PWA) | — |
| Frontend hosting | Azure Static Web Apps | Free tier |
| Testing | pytest | 9.0 |

---

## Document Map

| Document | For |
|----------|-----|
| [README.md](../README.md) | Anyone evaluating or getting started |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Developers setting up locally or contributing |
| [CLAUDE.md](../CLAUDE.md) | AI-assisted development rules and patterns |
| [CODEBASE_INDEX.md](../CODEBASE_INDEX.md) | File map, test suite, migrations, flagged debt |
| [docs/project_index.md](project_index.md) | System state, decisions, API structure, stack |
| [docs/backlog.md](backlog.md) | All open work items — single source of truth |
| [docs/backlog_completed.md](backlog_completed.md) | Completed items (Sessions A–L) |
| [docs/uat_test_cases.md](uat_test_cases.md) | UAT test cases |
| [docs/adr/](adr/) | Architecture Decision Records (ADR-001–005) |
| [docs/architecture.md](architecture.md) | Component diagram and networking overview |
| [docs/runbook.md](runbook.md) | Infrastructure deployment, validation, teardown |
| [docs/osi_security_review.md](osi_security_review.md) | Security analysis with gap/action list |
