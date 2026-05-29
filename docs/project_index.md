# EMS ReadyKit — Project Index
# Last updated: 2026-05-29

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
| Azure AD authentication | ✅ Live | RS256 JWT; three app roles |
| RBAC enforcement | ✅ Live | Role + station membership enforced on all endpoints |
| GitHub Actions CI/CD | ✅ Live | pip-audit → test → build → deploy on push to main |
| Alembic migrations | ✅ Live | 8 migrations applied; runs automatically on startup |

### What's built — backend

| Area | Status |
|------|--------|
| Stations, vehicles, inventory locations | ✅ Complete |
| Compartments and par levels | ✅ Complete |
| Daily inventory checks (all 5 check types) | ✅ Complete |
| Controlled substance checks | ✅ Complete |
| Repair requests (full lifecycle) | ✅ Complete |
| Check history, acknowledgement, soft-delete | ✅ Complete |
| Audit events | ✅ Complete |
| Station membership and access control | ✅ Complete |
| Date-range compliance query | ✅ Complete |
| Notifications, feedback, user requests | 📋 Backlog |

### What's built — frontend

| Module | Status |
|--------|--------|
| Check wizard (5 steps, all check types, draft save) | ✅ Complete |
| Vehicle & Equipment Status (repair requests, inactive toggle) | ✅ Complete |
| Check history (My Checks, All Checks, detail view) | ✅ Complete |
| Supervisor compliance dashboard | ✅ Complete |
| Station administration (membership management) | ✅ Complete |
| Help system, item management, notifications | 📋 Backlog |

### Test suite

| Metric | Value |
|--------|-------|
| Total tests passing | 191 |
| Known CVEs (pip-audit) | 0 |
| Test database | SQLite in-memory; no external services required |
| Coverage areas | Models, routers, RBAC, business rules, station membership, repair requests, check history |

---

## Architecture Decision Records

Short records of the significant decisions made and why. Read these if you want
to understand the reasoning behind the design, not just what was built.

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](adr/ADR-001-Architecture.md) | Single-app, single-datastore, single-region — justified by domain size | Accepted |
| [ADR-002](adr/ADR-002-RBAC.md) | Group-based Azure AD RBAC + application-layer station membership | Accepted |
| [ADR-003](adr/ADR-003-Logging-and-Audit.md) | Explicit audit events (not DB-derived); centralized Log Analytics | Accepted |
| [ADR-004](adr/ADR-004-Terraform-Module-Structure.md) | Modular Terraform organized by architectural responsibility | Accepted |
| [ADR-005](adr/ADR-005-Frontend-Architecture.md) | React PWA, modular architecture, localStorage draft with station scoping | Accepted |
| ADR-006 | DDoS Protection Standard cost/benefit tradeoff | 📋 Needed |

---

## Key Design Decisions

Decisions that shaped the system but don't warrant a full ADR.

| Decision | Rationale |
|----------|-----------|
| Status computed server-side | Tamper-resistant; enforces correct semantics regardless of client |
| EXPIRED beats MISSING | Conservative compliance — an expired item is a failure regardless of count |
| Worst-case check status | One FAIL item makes the whole check FAIL; NEEDS_RESTOCK is second |
| `performed_by` from JWT | Identity cannot be spoofed — bound server-side at submission time |
| Station membership enforced per-request | Crews can only access their assigned station; Admins bypass for cross-station reporting |
| Soft-delete with 90-day retention | Checks can be removed immediately but are recoverable; matches EMS record retention norms |
| Repair request: all roles can mark In Progress | An oil change or AC repair doesn't require a supervisor to acknowledge it's being handled |
| `getResolutionState` sentinel pattern | Resolution state derived from `corrective_action` prefix — no additional DB column needed |
| `useStationIssues` fails silently | Home screen badge is additive; a failed fetch must never block the primary workflow |
| Draft key includes `started_at` | Enables multiple in-progress checks for the same vehicle on the same day |
| Last-known station cached in localStorage | Draft banners show immediately on load, before the station API returns |
| Build zip on Linux in CI | Windows `Compress-Archive` creates backslash paths that Oryx cannot extract |
| `pip-audit` as CI gate | Dependency CVEs are caught before deploy, not discovered in production |

---

## Domain Model

```
Station
 └── Vehicle (ALS / BLS / QRV)
      ├── InventoryLocation (VEHICLE type, auto-created)
      │    └── Compartment
      │         ├── ParLevel  (item → min/max quantity required)
      │         └── StockLot  (lot number + expiration date)
      └── DailyInventoryCheck
           ├── CheckLineItem  (item → found/needed/status per check)
           ├── ControlledSubstanceCheck (dual-signature, ALS only)
           └── RepairRequest  (OPEN → IN_PROGRESS → RESOLVED)

InventoryLocation (JUMP_BAG / STATION_SUPPLY_ROOM types)
StationMember  (user ↔ station assignment with role)
AuditEvent     (immutable record of all material actions)
```

---

## API Structure

All routes are prefixed `/api/v1/`. Key endpoint groups:

| Group | Prefix | Access |
|-------|--------|--------|
| Stations | `/stations` | Admin (list all); All roles (list own) |
| Vehicles | `/vehicles` | Admin+; station membership enforced |
| Inventory | `/inventory` | Admin+; station membership enforced |
| Daily checks | `/checks/daily` | Submit: all roles; Detail: Supervisor+ |
| CS checks | `/checks/controlled-substance` | All roles (ALS vehicles only) |
| Repair requests | `/vehicles/{id}/repair-requests` | File: all roles; Resolve: Supervisor+ |
| Check history | `/checks/daily/my-history` | Own history: all roles |
| Compliance query | `/checks/daily/station/{id}` | All roles + membership; max 90-day range |
| Station members | `/stations/{id}/members` | Supervisor+ |
| Audit | `/audit` | Supervisor+ |

Full interactive docs: https://app-ems-readykit-dev.azurewebsites.net/docs

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
| Database | PostgreSQL (Azure Flexible Server) | 16 |
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
| [docs/project_index.md](project_index.md) | Technical reference — decisions, state, API structure |
| [docs/architecture.md](architecture.md) | Component diagram and networking overview |
| [docs/runbook.md](runbook.md) | Infrastructure deployment, validation, teardown |
| [docs/osi_security_review.md](osi_security_review.md) | Security analysis with gap/action list |
| [docs/backlog.md](backlog.md) | All open work items |
| [docs/adr/](adr/) | Architecture Decision Records |
