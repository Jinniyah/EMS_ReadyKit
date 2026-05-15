# EMS ReadyKit

[![CI/CD — Test, Build, Deploy](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml/badge.svg)](https://github.com/Jinniyah/EMS_ReadyKit/actions/workflows/deploy.yml)

Cloud-native inventory and vehicle readiness platform for Fire and EMS operations. Demonstrates Infrastructure-as-Code, Azure AD authentication, role-based access control, audit logging, and operational observability in a regulated domain.

**Live API:** https://app-ems-readykit-dev.azurewebsites.net  
**API docs:** https://app-ems-readykit-dev.azurewebsites.net/docs  
**Repository:** https://github.com/Jinniyah/EMS_ReadyKit

---

## What this project is

EMS ReadyKit replaces paper-based daily vehicle inventory checks for a Fire and EMS department. Crews use it on a phone or tablet to verify that every compartment on every ambulance is stocked, that nothing is expired, and that controlled substances are properly accounted for. Supervisors use it to track daily compliance, investigate discrepancies, and maintain audit-ready records.

The system is modeled after a real township Fire and EMS operation. It is a technical demonstration — it does not process patient data and is not connected to live departmental systems.

---

## What this project demonstrates

| Capability | Implementation |
|------------|---------------|
| Infrastructure-as-Code | Terraform modules for network, identity, policy, logging, app, data, storage |
| Cloud governance | Azure Policy (required tags, region lock, deny public IP), budget alerts |
| Authentication | Azure AD JWT (RS256), JWKS caching, audience/issuer verification |
| Authorization | Group-based RBAC (Azure AD) + application-layer enforcement |
| API design | FastAPI, versioned REST endpoints, Pydantic v2 validation, OpenAPI docs |
| Domain modeling | Station → Vehicle → Compartment → Item → StockLot hierarchy |
| Data integrity | SQLAlchemy 2.0, Alembic migrations, DB-level constraints |
| Audit trail | First-class audit events with actor, entity, severity, and metadata |
| Testing | 90 automated tests — models, routers, schema validation, RBAC, business rules |
| CI/CD | GitHub Actions: test → build on Linux → deploy → health check |
| Observability | Log Analytics, structured logging, diagnostic settings |
| Cost discipline | F1 dev tier, short log retention, budget alerts, right-sized compute |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Azure Active Directory                              │
│ Group-based RBAC: Administrator / Supervisor /      │
│ Responder — JWT RS256 tokens                        │
└─────────────────────┬───────────────────────────────┘
                      │ HTTPS + Bearer token
┌─────────────────────▼───────────────────────────────┐
│ Azure App Service (Python 3.11)                     │
│ FastAPI + Gunicorn + UvicornWorker                  │
│ /api/v1: stations, vehicles, inventory,             │
│          checks, audit                              │
│                                                     │
│  ┌─────────────────┐   ┌──────────────────────┐    │
│  │ Azure Key Vault  │   │ Log Analytics        │    │
│  │ Managed identity │   │ Structured audit log │    │
│  └─────────────────┘   └──────────────────────┘    │
└─────────────────────┬───────────────────────────────┘
                      │ Private connection
┌─────────────────────▼───────────────────────────────┐
│ Azure Database for PostgreSQL Flexible Server       │
│ Alembic migrations run on every startup             │
└─────────────────────────────────────────────────────┘
```

All infrastructure is provisioned via Terraform. No manual portal configuration.

---

## Project structure

```
EMS_ReadyKit/
├── app/                        # FastAPI application
│   ├── ems_readykit/
│   │   ├── core/               # Config, auth, database, logging
│   │   ├── models/             # SQLAlchemy ORM models (11 entities)
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   └── routers/            # API route handlers (6 routers)
│   ├── alembic/                # Database migrations
│   ├── tests/                  # 90 automated tests
│   ├── requirements.txt
│   ├── startup.sh              # Container startup: migrate then serve
│   └── pyproject.toml
├── iac/
│   └── Terraform/
│       ├── main.tf             # Root module
│       └── modules/
│           ├── network/        # VNet, subnets, NSGs
│           ├── identity_rbac/  # Azure AD groups, app roles, RBAC
│           ├── policy/         # Required tags, region lock, deny public IP
│           ├── logging/        # Log Analytics workspace
│           ├── app/            # App Service, Key Vault, managed identity
│           ├── data/           # PostgreSQL Flexible Server
│           ├── storage/        # Blob storage
│           └── siem/           # Security Onion (optional)
├── docs/
│   ├── project_index.md        # Master documentation index
│   ├── phase1_platform_foundation.md
│   ├── phase2_backend_api.md
│   ├── phase3_auth_cicd.md
│   ├── phase4_compartments_line_items.md
│   ├── phase5_frontend_pwa.md  # Frontend plan (in progress)
│   ├── phase6_backend_extensions.md
│   ├── adr/                    # Architecture Decision Records
│   │   ├── ADR-001-Architecture.md
│   │   ├── ADR-002-RBAC.md
│   │   ├── ADR-003-Logging-and-Audit.md
│   │   ├── ADR-004-Terraform-Module-Structure.md
│   │   └── ADR-005-Frontend-Architecture.md
│   └── runbook.md
├── .github/
│   └── workflows/deploy.yml    # CI/CD pipeline
└── CONTRIBUTING.md
```

---

## Domain model

```
Station
 └── Vehicle (ALS / BLS / QRV)
      ├── InventoryLocation
      │    └── Compartment ("Compartment #1", "Drug Bag", "Narcotic Lock Bag"...)
      │         ├── ParLevel (item → min/max required quantity)
      │         └── CheckLineItem (item → Need/Have/status per daily check)
      ├── DailyInventoryCheck (one per vehicle per calendar day)
      │    └── CheckLineItem → StockLot (lot number + expiration date)
      └── ControlledSubstanceCheck (dual-signature, ALS only)

StockLot (quantity + lot number + expiration date at a location)
AuditEvent (immutable record of all material actions)
```

---

## Role model

| Role | Platform scope | What they can do |
|------|---------------|-----------------|
| Administrator | Subscription-level Reader | Full system access — create and configure everything |
| Supervisor | Resource group Contributor | Station-level — review compliance, manage inventory, approve requests |
| Responder | Authenticated access only | Vehicle-level — submit daily checks, read inventory |

Roles are assigned via Azure AD groups. No user-level role assignments. Group membership is managed via Terraform.

---

## Key business rules

- One daily check per vehicle per calendar day (enforced at DB level)
- CS checks require ALS vehicle type — enforced at application layer
- CS checks require two different signers — enforced at application layer
- `performed_by` is bound to the JWT identity server-side — cannot be overridden by the client
- Line item status is computed server-side (OK / SHORT / MISSING / EXPIRED) — never client-supplied
- EXPIRED takes priority over MISSING — an expired item is a compliance failure regardless of count
- Overall check status is worst-case across all line items (PASS / NEEDS_RESTOCK / FAIL)

---

## Getting started

See [CONTRIBUTING.md](CONTRIBUTING.md) for full local setup instructions.

Quick start:

```bash
cd app
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
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
pytest tests/ -v                    # all 90 tests
pytest tests/test_models.py -v      # model tests only
pytest tests/test_routers.py -v     # router + RBAC tests only
pytest tests/ -v -k "RBAC"          # RBAC tests only
```

Tests use an in-memory SQLite database with savepoint isolation. No external services required.

---

## Deployment

Deployment is automated via GitHub Actions on every push to `main`:

1. Test job runs all 90 tests on `ubuntu-latest`
2. On pass: build zip on Linux (forward-slash paths — required for Oryx)
3. Deploy to Azure App Service via `azure/webapps-deploy@v3`
4. Health check: `GET /health` must return HTTP 200

Manual deploy:

```bash
# Build zip on Linux (WSL or a Linux machine)
cd app
zip -r /tmp/deploy.zip alembic ems_readykit alembic.ini app.py \
    Procfile pyproject.toml requirements.txt startup.sh

az webapp deploy \
    --resource-group rg-ems-readykit-dev \
    --name app-ems-readykit-dev \
    --src-path /tmp/deploy.zip \
    --type zip
```

> **Important:** Always build the zip on Linux. Windows `Compress-Archive` creates backslash paths that Oryx cannot extract as directories.

---

## Infrastructure

```bash
cd iac/Terraform
terraform init
terraform plan
terraform apply
```

Requires: Azure CLI authenticated, Terraform 1.6+, Azure AD permissions to create groups and app registrations.

See [docs/runbook.md](docs/runbook.md) for full deployment, validation, and teardown procedures.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/project_index.md](docs/project_index.md) | Master index — current state, all decisions, Phase 6 backlog |
| [docs/phase1_platform_foundation.md](docs/phase1_platform_foundation.md) | Azure infrastructure and Terraform |
| [docs/phase2_backend_api.md](docs/phase2_backend_api.md) | FastAPI application and domain model |
| [docs/phase3_auth_cicd.md](docs/phase3_auth_cicd.md) | Authentication, RBAC, CI/CD pipeline |
| [docs/phase4_compartments_line_items.md](docs/phase4_compartments_line_items.md) | Compartments, line items, expiration tracking |
| [docs/phase5_frontend_pwa.md](docs/phase5_frontend_pwa.md) | Frontend PWA plan (in progress) |
| [docs/phase6_backend_extensions.md](docs/phase6_backend_extensions.md) | Planned backend extensions |
| [docs/adr/](docs/adr/) | Architecture Decision Records (ADR-001 through ADR-005) |
| [docs/runbook.md](docs/runbook.md) | Deployment, validation, and teardown |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local setup, dev workflow, contribution guidelines |

---

## Technology stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Cloud | Microsoft Azure | — |
| IaC | Terraform | 1.6+ |
| Backend | FastAPI | 0.111.0 |
| ORM | SQLAlchemy | 2.0.30 |
| Migrations | Alembic | 1.13.1 |
| Validation | Pydantic | 2.7.1 |
| Database | PostgreSQL (Azure Flexible Server) | 16 |
| Runtime | Python | 3.11.15 |
| ASGI server | Gunicorn + UvicornWorker | 0.29.0 |
| Auth | Azure Active Directory | RS256 JWT |
| CI/CD | GitHub Actions | — |
| Frontend (planned) | React PWA + MSAL | — |
| Testing | pytest + pytest-asyncio | 8.2.0 |

---

## Known limitations (development deployment)

| Limitation | Detail | Production resolution |
|------------|--------|----------------------|
| F1 App Service tier | No VNet integration, no Always On | Upgrade to B1 — one Terraform variable change |
| Public DB connection | App reaches PostgreSQL over Azure services firewall | Enable VNet integration on B1+ |
| Short log retention | 7–14 days | Increase retention period in logging module |
| Single region | No geo-redundancy | Multi-region for production |

---

## License

MIT — see [LICENSE](LICENSE)
