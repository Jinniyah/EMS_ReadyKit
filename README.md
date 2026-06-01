# EMS ReadyKit

[![CI/CD — Test, Build, Deploy](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml/badge.svg)](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3110/)
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
that every ambulance is stocked, nothing is expired, and controlled substances are
properly accounted for — before every shift goes out the door.

### For crews

| Feature | Description |
|---------|-------------|
| **Guided daily check wizard** | Step-by-step walkthrough — select vehicle, check each compartment, count and validate every item |
| **Five item check types** | Supply counts, measurements (O₂ PSI), functional tests (AED battery), date records (defibrillator service), and documents |
| **Expiration tracking** | Items flagged EXPIRED when past date; lot number and expiry visible per item |
| **Controlled substance checks** | Dual-signature verification for ALS vehicles; second crew member captured on record |
| **Auto-save draft** | Progress saved after every item — if a call comes in mid-check, pick up exactly where you left off |
| **Multiple checks per day** | Supports shift-start and post-call restock checks on the same vehicle |
| **Repair reporting** | File routine or urgent repair requests from the check wizard or vehicle status screen; add notes at any time |
| **Jump bag support** | Portable equipment and jump bags checked on the same workflow as vehicles |
| **Check history** | View your own past checks; add notes to any check you submitted |

### For supervisors and administrators

| Feature | Description |
|---------|-------------|
| **Compliance dashboard** | Today's check status across all vehicles — pass, needs restock, fail, or not yet checked |
| **Check history — all station** | View all checks at the station filtered by status; defaults to FAIL on open so nothing is missed |
| **FAIL visibility** | Failed checks surface immediately; a direct link navigates to V&E Status to manage the repair |
| **Check notes** | Add corrective action notes to any check; visible to all roles |
| **Date-range compliance query** | Query check history across any date range up to 90 days |
| **Vehicle lifecycle management** | Mark vehicles out of service with a mandatory reason; return to service with an optional note |
| **Repair request tracking** | Open → In Progress → Resolved lifecycle with notes; all roles can advance; supervisors resolve |
| **Open issue badge** | Home screen shows a red badge on V&E Status when any vehicle has an unresolved repair request |
| **Soft-delete with retention** | Checks removed with a mandatory reason; preserved for 90 days before permanent deletion |
| **Station administration** | Manage station membership — control which crew members access which station's data |
| **Full audit trail** | Every material action — checks, repairs, notes, deletions — logged with actor, timestamp, and entity |
| **Item catalog** | Manage the full inventory item list; bulk import via CSV with template download |
| **Par level assignment** | Assign items to vehicle compartments with minimum and restock-to quantities |
| **Vehicle & compartment management** | Add vehicles, define compartments, manage out-of-service status — all through the UI |

---

## What this project demonstrates

| Capability | Implementation |
|------------|----------------|
| Infrastructure-as-Code | Terraform modules for network, identity, policy, logging, app, data, and storage |
| Cloud governance | Azure Policy (required tags, region lock, deny public IP), budget alerts |
| Authentication | Azure AD JWT (RS256), JWKS caching, full claim validation |
| Authorization | Group-based RBAC (Azure AD) + application-layer station membership enforcement |
| API design | FastAPI, versioned REST endpoints, Pydantic v2 validation, OpenAPI docs |
| Domain modeling | Station → Vehicle → Compartment → Item → StockLot hierarchy |
| Data integrity | SQLAlchemy 2.0, Alembic migrations, DB-level constraints |
| Audit trail | First-class audit events with actor, entity, severity, and metadata |
| Security | OWASP Top 10 reviewed; 0 known CVEs (pip-audit in CI); security headers; production hardening |
| Testing | 200+ automated tests — models, routers, RBAC, business rules, station membership |
| CI/CD | GitHub Actions: pip-audit → pytest → build on Linux → deploy → health check |
| Observability | Log Analytics, structured logging, diagnostic settings |
| Cost discipline | F1/Free dev tiers; short log retention; budget alerts; B1 upgrade is one variable change |
| Frontend | React PWA — mobile-first, modular architecture, isolated error boundaries, accessible |
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
│  Azure App Service (Python 3.11)                            │
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
│  Alembic migrations run automatically on startup            │
└─────────────────────────────────────────────────────────────┘
```

All infrastructure is provisioned via Terraform. No manual portal configuration.

---

## Role model

| Role | What they can do |
|------|-----------------|
| **Responder** | Submit daily checks, view own check history, add notes to own checks, file repair requests, mark repairs in progress |
| **Supervisor** | Everything a Responder can do, plus: view all station checks, manage repair lifecycle, manage vehicles and compartments, manage station membership, bulk import items |
| **Administrator** | Full system access — all supervisor capabilities plus station creation, user management, item catalog management, audit access, and soft-delete management |

Roles are assigned via Azure AD groups. No user-level role assignments. Group membership is managed via Terraform.

---

## Key business rules

- Station membership is enforced on every endpoint — crews can only access their assigned station's data
- `performed_by` is bound to the JWT identity server-side — cannot be spoofed by the client
- Line item status is computed server-side (OK / SHORT / MISSING / EXPIRED / LOW / OVERDUE / FAIL) — never client-supplied
- EXPIRED takes priority over MISSING — an expired item is a compliance failure regardless of quantity
- Overall check status is worst-case across all line items (PASS / NEEDS_RESTOCK / FAIL)
- Controlled substance checks require a different primary and secondary signer — enforced at application layer
- Soft-deleted checks are hidden immediately but retained for 90 days before permanent deletion
- Resolving a repair request requires Supervisor+; marking In Progress is available to all roles
- Responders can add notes only to their own checks; Supervisors can note any check
- Out-of-service vehicles require a mandatory reason; return to service accepts an optional note

---

## Getting started

See [CONTRIBUTING.md](CONTRIBUTING.md) for full local setup instructions.

**Quick start:**

```bash
cd app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
pytest tests/ -v
uvicorn ems_readykit.main:app --reload
```

API explorer: http://localhost:8000/docs

---

## Running tests

```bash
cd app
pytest tests/ -v                      # all 200+ tests
pytest tests/test_repair_requests.py -v   # repair request lifecycle
pytest tests/test_admin_items.py -v       # item catalog and CSV import
pytest tests/test_check_history.py -v     # check history and notes
pytest tests/test_station_membership.py -v  # access control
pytest tests/ -v -k "RBAC"           # RBAC enforcement only
```

Tests use an in-memory SQLite database with savepoint isolation. No external services required.

---

## Deployment

Deployment is fully automated via GitHub Actions on every push to `main`:

1. `pip-audit` — 0 known CVEs required to proceed
2. `pytest` — all tests must pass
3. Build zip on Linux (forward-slash paths — required for Azure Oryx)
4. Deploy API to Azure App Service
5. Build and deploy frontend to Azure Static Web Apps
6. Health check: `GET /health` must return HTTP 200

Manual API deploy (Linux or WSL only):

```bash
cd app
zip -r /tmp/deploy.zip alembic ems_readykit alembic.ini app.py \
    Procfile pyproject.toml requirements.txt startup.sh

az webapp deploy \
    --resource-group rg-ems-readykit-dev \
    --name app-ems-readykit-dev \
    --src-path /tmp/deploy.zip \
    --type zip
```

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
| File upload | python-multipart | 0.0.27 |
| Database | PostgreSQL (Azure Flexible Server) | 16 |
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
| [docs/project_index.md](docs/project_index.md) | Current system state, technology decisions, and what's built vs. planned |
| [docs/architecture.md](docs/architecture.md) | Component diagram and networking notes |
| [docs/runbook.md](docs/runbook.md) | Infrastructure deployment, validation, and teardown |
| [docs/osi_security_review.md](docs/osi_security_review.md) | Layer-by-layer security analysis with gap/action list |
| [docs/backlog.md](docs/backlog.md) | All open work items, session plan, and deferred items |
| [docs/adr/](docs/adr/) | Architecture Decision Records — key decisions with rationale |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local setup, dev workflow, and contribution guidelines |

---

## Known limitations — development deployment

| Limitation | Detail | Production path |
|------------|--------|----------------|
| F1 App Service tier | No Always On; cold starts possible | Upgrade to B1 — one Terraform variable |
| Public DB connection on F1 | App reaches PostgreSQL over Azure services firewall | Enable VNet integration on B1+ |
| No Azure Firewall | Outbound traffic is unfiltered | Add Firewall module (see backlog I-1) |
| Short log retention | 7–14 days | Increase retention in logging Terraform module |
| Single region | No geo-redundancy | Multi-region Terraform for production |

---

## License

MIT — see [LICENSE](LICENSE)
