# EMS ReadyKit

[![CI/CD — Test, Build, Deploy](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml/badge.svg)](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml)
[![Backend tests — 530 passing](https://img.shields.io/badge/backend%20tests-530%20passing-brightgreen?logo=pytest&logoColor=white)](app/tests/)
[![Frontend tests — 233 passing](https://img.shields.io/badge/frontend%20tests-233%20passing-brightgreen?logo=vitest&logoColor=white)](frontend/src/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![PWA](https://img.shields.io/badge/PWA-enabled-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![Deployed on Azure](https://img.shields.io/badge/deployed%20on-Azure-0078D4?logo=microsoftazure&logoColor=white)](https://lively-bush-0ed75ca10.7.azurestaticapps.net)
[![Security — 0 CVEs](https://img.shields.io/badge/security-0%20CVEs-brightgreen?logo=shield)](https://pypi.org/project/pip-audit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Cloud-native inventory and vehicle readiness platform for Fire and EMS operations.
Built to replace paper-based daily vehicle checks with a mobile-first digital
workflow -- designed for real crews, in real stations, under real time pressure.

**Live in UAT Testing** with a real volunteer EMS team (Newberg Township) since
2026-06-23.

**Live app:** https://lively-bush-0ed75ca10.7.azurestaticapps.net
**Live API:** https://app-ems-readykit-dev.azurewebsites.net
**API docs (non-prod):** https://app-ems-readykit-dev.azurewebsites.net/docs
**Repository:** https://github.com/Jinniyah/EMS_ReadyKit

📁 **Reviewing this as a portfolio piece?** Skip straight to the [**evidence — screenshots, diagrams, and UAT records**](#portfolio-evidence).

---

## Portfolio evidence

The proof that this is a real, working, deployed system -- not just source code -- lives in [`docs/evidence/`](docs/evidence). It's organized into three folders so you don't have to dig through code to find it:

| Folder | What's inside |
|--------|----------------|
| 🏗️ [**Architecture & design**](docs/evidence/arch_and_design) | System architecture diagram, authentication flow diagram, full database schema (ERD), API surface overview, migration history |
| 🖥️ [**Live deployment**](docs/evidence/live_deployment) | Screenshots of the running app -- home screen, check wizard, compliance dashboard -- plus the live Azure resources behind it (App Service, PostgreSQL, Static Web Apps) |
| ✅ [**UAT records**](docs/evidence/uat) | Completed user-acceptance test cases from the real Newberg Township EMS team, one file per role (Admin / Supervisor / Responder) |

For the complete itemized breakdown of what's been captured, why it matters, and what's still in progress, see the [Portfolio Evidence Checklist](docs/evidence/Portfolio_Evidence_Checklist.csv).

---

## What it does

EMS ReadyKit gives crews and supervisors a structured, accountable way to verify that every ambulance is stocked, nothing is expired, and critical equipment is ready -- before every shift goes out the door.

### For crews (Responders)

| Feature | Description |
|---------|-------------|
| **Guided daily check wizard** | Step-by-step walkthrough -- select vehicle, check each compartment, count and validate every item |
| **Six item check types** | Supply counts, measurements (O2 PSI), functional tests (AED battery), date records (defibrillator service), documents, and expiry-date tracking |
| **Priority items** | AED and LUCAS surface at the top of every check with a custom confirmation question -- must be verified before the compartment walk |
| **Expiration tracking** | Items flagged EXPIRED or OVERDUE when past date or recurrence window; lot number and expiry visible per item |
| **O2 PSI validation** | Readings below minimum (500 PSI on-board, 200 PSI portable) are flagged LOW -- the truck does not get a passing check with insufficient oxygen |
| **Controlled substance checks** | Dual-signature verification for ALS vehicles; second crew member captured on record |
| **Auto-save draft** | Progress saved after every item -- if a call comes in mid-check, pick up exactly where you left off; supports multiple in-progress checks per day |
| **Multiple checks per day** | Supports shift-start and post-call restock checks on the same vehicle |
| **After-call usage log** | Log items consumed on a call in under 60 seconds; FIFO stock decrement fires automatically |
| **Repair reporting** | File routine or urgent repair requests from the check wizard or vehicle status screen |
| **Jump bag support** | Portable equipment checked on the same wizard as vehicles |
| **Check history** | View your own past checks; submitted checks are read-only legal records |
| **In-app Help & Tutorial** | Role-aware help screen with accordion guidance for every workflow, plus a replayable first-run tutorial overlay |

### For supervisors and administrators

| Feature | Description |
|---------|-------------|
| **Compliance dashboard** | Today's check status across all vehicles -- pass, needs restock, fail, or not yet checked |
| **Inline low-stock alerts** | Supply shortfalls visible on the dashboard without extra taps |
| **Expiring items panel** | Items expiring within 30-90 days surfaced proactively with lot and location context |
| **Damaged items panel** | Collapsible dashboard panel surfacing items flagged damaged, with vehicle and compartment context |
| **Compliance calendar** | Week and month views showing check history per vehicle and portable location; tap any cell to open the check detail |
| **FAIL acknowledgement** | Supervisors record resolution notes directly on the FAIL check record |
| **Vehicle lifecycle management** | Mark vehicles out of service; return to service; retire permanently |
| **Portable location management** | Create, rename, and retire jump bags and portable equipment locations |
| **Repair request tracking** | Open to In Progress to Resolved lifecycle; all roles advance; supervisors resolve |
| **Supply room management** | Station-level stock with shelves; receive stock; correct counts; dispose expired lots |
| **After-call usage history** | Full log of items consumed per call, per vehicle, with frequent-item shortcuts |
| **Station settings** | Allow or lock check modification after submission; per-station toggle |
| **Station administration** | Single Members screen for managing station membership -- multi-role support, name edits, and bulk CSV import/template download |
| **Email alignment check** | Admin diagnostic flagging member records whose login identifier doesn't look like a valid email (manual-entry or CSV mistakes) |
| **Full audit trail** | Every material action logged with actor, timestamp, and entity -- legally defensible; paginated with date-range filtering |
| **Station-scoped item catalog** | Per-station item catalog with cabinet-group categorization; bulk import via CSV with template download; AI identification fields |
| **Par level assignment** | Assign items to any location type (vehicle, jump bag, or supply room) with min/restock quantities; mark priority items; deactivate with reason and reactivate without losing history |
| **Soft-delete with retention** | Checks removed with mandatory reason; preserved for 90 days |

---

## What this project demonstrates

| Capability | Implementation |
|------------|----------------|
| Infrastructure-as-Code | Terraform modules for network, identity, policy, logging, app, data, and storage |
| Cloud governance | Azure Policy (required tags, region lock, deny public IP), budget alerts |
| Authentication | Azure AD JWT (RS256), JWKS caching, full claim validation |
| Authorization | Group-based RBAC (Azure AD) + application-layer station membership enforcement |
| API design | FastAPI, versioned REST endpoints, Pydantic v2 validation, OpenAPI (disabled in production) |
| Domain modeling | Station to Vehicle to Compartment to Item hierarchy; 6 check types; 7 line item statuses; per-station item scoping |
| Data integrity | SQLAlchemy 2.0, Alembic (29 migrations applied), DB-level constraints |
| Audit trail | First-class audit events with actor, entity, severity, and metadata; immutable records |
| Security | OWASP Top 10 reviewed; 0 known CVEs (pip-audit in CI); security headers split correctly across API and SWA; rate limiting; production hardening; dedicated RS256 JWT validation test coverage |
| Testing | 530 backend + 233 frontend automated tests -- persona-based (Responder/Supervisor/Admin), safety-critical (O2 PSI, AED dates), seed integrity, RBAC, station scoping, retirement, usage log |
| CI/CD | GitHub Actions: pip-audit to pytest to build on Linux to deploy to health check |
| Observability | Log Analytics, structured logging with request correlation IDs, diagnostic settings |
| Cost discipline | B1 App Service; short log retention; budget alerts |
| Frontend | React PWA -- mobile-first, modular architecture with ErrorBoundary isolation, 60px tap targets, accessible |
| Bulk data loading | CSV import with template download, row-level validation, BOM-safe Excel handling (items and station members) |
| Rate limiting | slowapi per-endpoint rate limiting; test environment override via TESTING env var |

---

## Architecture

```
+-------------------------------------------------------------+
|  Azure Active Directory                                     |
|  Group-based RBAC: Administrator / Supervisor / Responder   |
|  RS256 JWT tokens                                           |
+----------------------------+--------------------------------+
                             | HTTPS + Bearer token
+----------------------------v--------------------------------+
|  Azure Static Web Apps                                      |
|  React PWA -- mobile-first, MSAL authentication             |
+----------------------------+--------------------------------+
                             | HTTPS API calls
+----------------------------v--------------------------------+
|  Azure App Service B1 (Python 3.11)                         |
|  FastAPI + Gunicorn + UvicornWorker                         |
|  /api/v1: stations, vehicles, inventory, checks,            |
|           repair requests, usage, admin, audit              |
|                                                             |
|  +-------------------+   +------------------------------+   |
|  |  Azure Key Vault  |   |  Log Analytics Workspace     |   |
|  |  Managed identity |   |  Structured audit log + KQL  |   |
|  +-------------------+   +------------------------------+   |
+----------------------------+--------------------------------+
                             | Private connection
+----------------------------v--------------------------------+
|  Azure Database for PostgreSQL Flexible Server              |
|  29 Alembic migrations -- run automatically on startup      |
+-------------------------------------------------------------+
```

All infrastructure is provisioned via Terraform. No manual portal configuration.

---

## Role model

| Role | What they can do |
|------|-----------------|
| **Responder** | Submit daily checks; log after-call usage; view own check history; file repair requests; mark repairs in progress |
| **Supervisor** | All Responder actions plus: view all station checks; manage repair lifecycle; manage vehicles and compartments; manage station membership (add, edit, multi-role, CSV import); create and edit items; correct supply counts; expiring items alerts |
| **Administrator** | Full system access -- all Supervisor capabilities plus station creation; item deactivation; par level deactivation; audit access; vehicle and location retirement; station retirement; email alignment diagnostics; hard-delete management |

Roles are assigned via Azure AD groups. Station membership is managed via the Station Administration -> Members screen.

---

## Key business rules

- Station membership is enforced on every endpoint -- crews can only access their assigned station
- Items are scoped per-station -- one station's catalog and naming never collides with another's
- `performed_by` is bound to the JWT identity server-side -- cannot be spoofed
- Line item status is computed server-side -- never accepted from the client
  - `OK` / `SHORT` / `LOW` / `MISSING` / `EXPIRED` / `OVERDUE` / `FAIL`
- Overall check status is worst-case: `PASS` to `NEEDS_RESTOCK` to `FAIL`
- `EXPIRED` and `OVERDUE` both escalate to `FAIL` at the check level
- O2 PSI below minimum triggers `LOW` -- check fails, not silently OK
- AED and LUCAS date records past recurrence window trigger `OVERDUE` and `FAIL`
- Submitted checks are immutable read-only legal records
- FAIL checks preserve the original record -- resolution is documented separately
- Controlled substance checks require different primary and secondary signers
- Resolving a repair request requires `resolution_notes` and Supervisor+
- No Change is blocked on compartments with `requires_full_check = True` (e.g. Truck Operations)
- Supply room auto-decrement fires on vehicle check submit only; supply-room-only checks do not trigger it
- After-call usage FIFO: oldest lots decremented first; depletion stops at zero, never blocks submission
- Deactivating a par level preserves its history; re-adding the same item to the same compartment reactivates the original record instead of creating a duplicate
- Retirement (vehicle, location, station, stock lot) is permanent and distinct from temporary out-of-service status

---

## Getting started

See [CONTRIBUTING.md](CONTRIBUTING.md) for full local setup instructions.

**Quick start (Windows PowerShell):**

```powershell
cd app
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python seed.py             # seeds Newberg Township, Marcellus Township, Training, TEST stations
python seed_training.py    # seeds the always-on Training station catalog
pytest tests/ -q
uvicorn ems_readykit.main:app --reload
```

API explorer: http://localhost:8000/docs

---

## Running tests

```powershell
cd app

# Full backend suite (530 tests)
pytest tests/ -q

# Verbose with short tracebacks
pytest tests/ -v --tb=short

# Save output to file
pytest tests/ -v --tb=long 2>&1 | Out-File -FilePath test_results.txt -Encoding utf8

# Specific files
pytest tests/test_priority_items.py -v
pytest tests/test_safety_checks.py -v
pytest tests/test_persona_responder.py -v
pytest tests/test_retirement.py -v
pytest tests/test_usage.py -v
pytest tests/test_item_station_scoping.py -v

# Seed integrity (requires seeded dev DB)
pytest tests/test_seed_integrity.py -v

# Keyword filter
pytest tests/ -v -k "AED"
pytest tests/ -v -k "RBAC"
```

```powershell
cd frontend

# Full frontend suite (233 tests)
npm test
```

Tests use either an in-memory SQLite database (`db` fixture, resets between tests)
or the seeded dev database (`seeded_db` fixture, read-only). No external services required.

---

## Deployment

Deployment is fully automated via GitHub Actions on every push to `main`:

1. `pip-audit` -- 0 known CVEs required to proceed
2. `pytest` -- all 530 backend tests must pass
3. Build zip on Linux (forward-slash paths required for Azure Oryx)
4. Deploy API to Azure App Service
5. Build and deploy frontend to Azure Static Web Apps
6. Health check: `GET /health` must return HTTP 200

> **Always build the zip on Linux.** Windows `Compress-Archive` creates
> backslash paths that Oryx cannot extract as directories.

---

## Technology stack

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
| Testing | pytest / Vitest + React Testing Library | 9.0 / -- |

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/evidence/](docs/evidence) | Portfolio evidence -- architecture diagrams, live deployment screenshots, and UAT records (see [Portfolio evidence](#portfolio-evidence) above) |
| [docs/project_index.md](docs/project_index.md) | Current system state, decisions, API structure |
| [docs/architecture.md](docs/architecture.md) | Component diagram and networking notes |
| [docs/runbook.md](docs/runbook.md) | Infrastructure deployment, validation, and teardown |
| [docs/osi_security_review.md](docs/osi_security_review.md) | OSI layer security analysis with gap/action list |
| [docs/backlog.md](docs/backlog.md) | All open work items -- single source of truth |
| [docs/backlog_completed.md](docs/backlog_completed.md) | Portfolio-ready changelog of completed sessions |
| [docs/adr/](docs/adr/) | Architecture Decision Records (ADR-001 through ADR-006) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local setup, dev workflow, and contribution guidelines |
| [CLAUDE.md](CLAUDE.md) | Rules and patterns for AI-assisted development |
| [CODEBASE_INDEX.md](CODEBASE_INDEX.md) | File map, test suite, migrations, flagged debt |

---

## Known limitations -- current deployment

| Limitation | Detail | Production path |
|------------|--------|----------------|
| Public DB connection | App reaches PostgreSQL over Azure services firewall | Enable VNet integration + Private DNS Zone |
| No Azure Firewall | Outbound traffic is unfiltered | Add Firewall module (backlog I-1) |
| Short log retention | 7-14 days | Increase retention in logging Terraform module |
| Single region | No geo-redundancy | Multi-region Terraform for production |
| No offline submission queue | Checks require connectivity to submit | IndexedDB-backed retry queue (backlog TECH-3) |

---

## License

MIT -- see [LICENSE](LICENSE)
