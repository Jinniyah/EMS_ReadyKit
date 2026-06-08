# EMS ReadyKit

[![CI/CD — Test, Build, Deploy](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml/badge.svg)](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml)
[![Tests — 349 passing](https://img.shields.io/badge/tests-349%20passing-brightgreen?logo=pytest&logoColor=white)](app/tests/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![PWA](https://img.shields.io/badge/PWA-enabled-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![Deployed on Azure](https://img.shields.io/badge/deployed%20on-Azure-0078D4?logo=microsoftazure&logoColor=white)](https://lively-bush-0ed75ca10.7.azurestaticapps.net)
[![Security — 0 CVEs](https://img.shields.io/badge/security-0%20CVEs-brightgreen?logo=shield)](https://pypi.org/project/pip-audit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Cloud-native inventory and vehicle readiness platform for Fire and EMS operations.
Built to replace paper-based daily vehicle checks with a mobile-first digital
workflow — designed for real crews, in real stations, under real time pressure.

**Live app:** https://lively-bush-0ed75ca10.7.azurestaticapps.net
**Live API:** https://app-ems-readykit-dev.azurewebsites.net
**API docs:** https://app-ems-readykit-dev.azurewebsites.net/docs
**Repository:** https://github.com/Jinniyah/EMS_ReadyKit

---

## What it does

EMS ReadyKit gives crews and supervisors a structured, accountable way to verify
that every ambulance is stocked, nothing is expired, and critical equipment is
ready — before every shift goes out the door.

### For crews

| Feature | Description |
|---------|-------------|
| **Guided daily check wizard** | Step-by-step walkthrough — select vehicle, check each compartment, count and validate every item |
| **Five item check types** | Supply counts, measurements (O₂ PSI), functional tests (AED battery), date records (defibrillator service), and documents |
| **Priority items** | AED and LUCAS surface at the top of every check with a custom confirmation question — they must be verified before anything else |
| **Expiration tracking** | Items flagged EXPIRED or OVERDUE when past date or recurrence window; lot number and expiry visible per item |
| **O₂ PSI validation** | Readings below minimum (500 PSI) are flagged LOW — the truck does not get a passing check with insufficient oxygen |
| **Controlled substance checks** | Dual-signature verification for ALS vehicles; second crew member captured on record |
| **Auto-save draft** | Progress saved after every item — if a call comes in mid-check, pick up exactly where you left off |
| **Multiple checks per day** | Supports shift-start and post-call restock checks on the same vehicle |
| **Repair reporting** | File routine or urgent repair requests from the check wizard or vehicle status screen |
| **Jump bag support** | Portable equipment and jump bags checked on the same workflow as vehicles |
| **Check history** | View your own past checks; submitted checks are read-only legal records |

### For supervisors and administrators

| Feature | Description |
|---------|-------------|
| **Compliance dashboard** | Today's check status across all vehicles — pass, needs restock, fail, or not yet checked |
| **Inline low-stock alerts** | Supply shortfalls visible on the dashboard without any extra taps — Earl sees them the moment he opens the app |
| **FAIL visibility** | Failed checks surface immediately; direct navigation to V&E Status to manage the repair |
| **Date-range compliance query** | Query check history across any date range up to 90 days |
| **Vehicle lifecycle management** | Mark vehicles out of service with a mandatory reason; return to service with an optional note |
| **Repair request tracking** | Open → In Progress → Resolved lifecycle; all roles advance; supervisors resolve |
| **Soft-delete with retention** | Checks removed with a mandatory reason; preserved for 90 days |
| **Station administration** | Manage station membership — control which crew members access which station's data |
| **Full audit trail** | Every material action logged with actor, timestamp, and entity — legally defensible |
| **Item catalog** | Manage the full inventory item list; bulk import via CSV with template download |
| **Par level assignment** | Assign items to vehicle compartments with minimum and restock-to quantities; mark priority items |
| **Supply room** | Station-level stock tracking with auto-decrement when vehicles are restocked after checks |

---

## What this project demonstrates

| Capability | Implementation |
|------------|----------------|
| Infrastructure-as-Code | Terraform modules for network, identity, policy, logging, app, data, and storage |
| Cloud governance | Azure Policy (required tags, region lock, deny public IP), budget alerts |
| Authentication | Azure AD JWT (RS256), JWKS caching, full claim validation |
| Authorization | Group-based RBAC (Azure AD) + application-layer station membership enforcement |
| API design | FastAPI, versioned REST endpoints, Pydantic v2 validation, OpenAPI docs |
| Domain modeling | Station → Vehicle → Compartment → Item hierarchy; 5 check types; 7 line item statuses |
| Data integrity | SQLAlchemy 2.0, Alembic migrations (18 applied), DB-level constraints |
| Audit trail | First-class audit events with actor, entity, severity, and metadata |
| Security | OWASP Top 10 reviewed; 0 known CVEs (pip-audit in CI); security headers; production hardening |
| Testing | 349 automated tests — persona-based (Jamie/Earl/Jennifer), safety-critical (O₂ PSI, AED dates), seed integrity, RBAC, business rules |
| CI/CD | GitHub Actions: pip-audit → pytest → build on Linux → deploy → health check |
| Observability | Log Analytics, structured logging, diagnostic settings |
| Cost discipline | B1 App Service; short log retention; budget alerts |
| Frontend | React PWA — mobile-first, modular architecture, 60px tap targets, accessible |
| Bulk data loading | CSV import with template download, row-level validation, BOM-safe Excel handling |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Azure Active Directory                                     │
│  Group-based RBAC: Administrator / Supervisor / Responder   │
│  RS256 JWT tokens                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS + Bearer token
┌──────────────────────────▼──────────────────────────────────┐
│  Azure Static Web Apps                                      │
│  React PWA — mobile-first, MSAL authentication              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS API calls
┌──────────────────────────▼──────────────────────────────────┐
│  Azure App Service B1 (Python 3.11)                         │
│  FastAPI + Gunicorn + UvicornWorker                         │
│  /api/v1: stations, vehicles, inventory, checks,            │
│           repair requests, admin, audit                     │
│                                                             │
│  ┌───────────────────┐   ┌──────────────────────────────┐   │
│  │  Azure Key Vault  │   │  Log Analytics Workspace     │   │
│  │  Managed identity │   │  Structured audit log + KQL  │   │
│  └───────────────────┘   └──────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ Private connection
┌──────────────────────────▼──────────────────────────────────┐
│  Azure Database for PostgreSQL Flexible Server              │
│  18 Alembic migrations — run automatically on startup       │
└─────────────────────────────────────────────────────────────┘
```

All infrastructure is provisioned via Terraform. No manual portal configuration.

---

## Role model

| Role | What they can do |
|------|-----------------|
| **Responder** | Submit daily checks, view own check history, file repair requests, mark repairs in progress |
| **Supervisor** | Everything a Responder can do, plus: view all station checks, manage repair lifecycle, manage vehicles and compartments, manage station membership, create/edit items, correct supply counts |
| **Administrator** | Full system access — all supervisor capabilities plus station creation, item deactivation, audit access, hard-delete management |

Roles are assigned via Azure AD groups. Station membership is managed via the admin UI.

---

## Key business rules

- Station membership is enforced on every endpoint — crews can only access their assigned station's data
- `performed_by` is bound to the JWT identity server-side — cannot be spoofed
- Line item status is computed server-side — never client-supplied
  - `OK` / `SHORT` / `LOW` / `MISSING` / `EXPIRED` / `OVERDUE` / `FAIL`
- Overall check status is worst-case: `PASS` → `NEEDS_RESTOCK` → `FAIL`
- `EXPIRED` and `OVERDUE` both map to `FAIL` at the check level
- O₂ PSI below minimum → `LOW` → check `NEEDS_RESTOCK` (not silently OK)
- AED and LUCAS date records past recurrence window → `OVERDUE` → check `FAIL`
- Submitted checks are immutable read-only legal records
- FAIL checks preserve the original record — repair resolution creates a separate record
- Controlled substance checks require a different primary and secondary signer
- Resolving a repair request requires `resolution_notes` and Supervisor+
- Soft-deleted checks are hidden immediately but retained for 90 days

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
python seed.py        # seeds Unit 712 + Newberg Township Station 1
pytest tests/ -q
uvicorn ems_readykit.main:app --reload
```

API explorer: http://localhost:8000/docs

---

## Running tests

```powershell
cd app

# Full suite (349 tests, ~6 seconds)
pytest tests/ -q

# Verbose with short tracebacks
pytest tests/ -v --tb=short

# Specific file
pytest tests/test_priority_items.py -v

# Safety-critical checks only
pytest tests/test_safety_checks.py -v

# Seed integrity (requires seeded dev DB)
pytest tests/test_seed_integrity.py -v

# Keyword filter
pytest tests/ -v -k "AED"
pytest tests/ -v -k "RBAC"
```

Tests use either an in-memory SQLite database (`db` fixture, resets between tests)
or the seeded dev database (`seeded_db` fixture, read-only). No external services required.
See [CONTRIBUTING.md](CONTRIBUTING.md) for details on both fixtures.

---

## Deployment

Deployment is fully automated via GitHub Actions on every push to `main`:

1. `pip-audit` — 0 known CVEs required to proceed
2. `pytest` — all 349 tests must pass
3. Build zip on Linux (forward-slash paths — required for Azure Oryx)
4. Deploy API to Azure App Service
5. Build and deploy frontend to Azure Static Web Apps
6. Health check: `GET /health` must return HTTP 200

> **Always build the zip on Linux.** Windows `Compress-Archive` creates backslash
> paths that Oryx cannot extract as directories.

---

## Technology stack

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

## Documentation

| Document | Description |
|----------|-------------|
| [docs/project_index.md](docs/project_index.md) | Current system state, decisions, API structure |
| [docs/architecture.md](docs/architecture.md) | Component diagram and networking notes |
| [docs/runbook.md](docs/runbook.md) | Infrastructure deployment, validation, and teardown |
| [docs/osi_security_review.md](docs/osi_security_review.md) | Security analysis with gap/action list |
| [docs/backlog.md](docs/backlog.md) | All open work items — single source of truth |
| [docs/adr/](docs/adr/) | Architecture Decision Records |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local setup, dev workflow, and contribution guidelines |
| [CLAUDE.md](CLAUDE.md) | Rules and patterns for AI-assisted development |

---

## Known limitations — development deployment

| Limitation | Detail | Production path |
|------------|--------|----------------|
| Public DB connection | App reaches PostgreSQL over Azure services firewall | Enable VNet integration on B1+ |
| No Azure Firewall | Outbound traffic is unfiltered | Add Firewall module (backlog I-1) |
| Short log retention | 7–14 days | Increase retention in logging Terraform module |
| Single region | No geo-redundancy | Multi-region Terraform for production |

---

## License

MIT — see [LICENSE](LICENSE)
