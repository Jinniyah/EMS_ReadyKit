# Contributing to EMS ReadyKit

Thank you for working on EMS ReadyKit. This guide covers everything you need
to get a local development environment running, understand the codebase, and
contribute changes confidently.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Local setup](#2-local-setup)
3. [Environment variables](#3-environment-variables)
4. [Running the API](#4-running-the-api)
5. [Running tests](#5-running-tests)
6. [Database migrations](#6-database-migrations)
7. [Project structure](#7-project-structure)
8. [How to add a new endpoint](#8-how-to-add-a-new-endpoint)
9. [How to add a new model](#9-how-to-add-a-new-model)
10. [Authentication in development](#10-authentication-in-development)
11. [CI/CD pipeline](#11-cicd-pipeline)
12. [Deployment](#12-deployment)
13. [Code style and standards](#13-code-style-and-standards)
14. [Documentation standards](#14-documentation-standards)
15. [Branching and pull requests](#15-branching-and-pull-requests)

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | https://python.org |
| Git | Any recent | https://git-scm.com |
| Terraform | 1.6+ | https://developer.hashicorp.com/terraform/install |
| Azure CLI | Any recent | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |

You do NOT need a running PostgreSQL instance for local development or testing.
The test suite uses SQLite in-memory. The API defaults to SQLite when no
`DATABASE_URL` is configured.

---

## 2. Local setup

```bash
# Clone the repository
git clone https://github.com/Jinniyah/EMS_ReadyKit.git
cd EMS_ReadyKit

# Move into the application directory
cd app

# Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Apply database migrations (creates ems_readykit_dev.db for local SQLite)
alembic upgrade head

# Start the development server
uvicorn ems_readykit.main:app --reload
```

The API is now running at http://localhost:8000

Interactive API docs: http://localhost:8000/docs

---

## 3. Environment variables

Copy the example file and edit as needed:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `development` | Set to `production` to enable real JWT validation |
| `DATABASE_URL` | No | SQLite file | PostgreSQL connection string for production |
| `AZURE_AD_TENANT_ID` | No | — | Required for production JWT validation |
| `AZURE_AD_CLIENT_ID` | No | — | App Registration client ID |
| `SECRET_KEY` | No | Dev default | Used for any local signing operations |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed origins |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

**In development (`APP_ENV=development`):** real Azure AD tokens are not required.
Use the fake test tokens described in section 10.

**In production (`APP_ENV=production`):** `AZURE_AD_TENANT_ID` and
`AZURE_AD_CLIENT_ID` are required. The API will reject all requests without
a valid Azure AD JWT.

---

## 4. Running the API

```bash
cd app

# Development server with auto-reload
uvicorn ems_readykit.main:app --reload

# Production-style (same as App Service)
gunicorn ems_readykit.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 2
```

Endpoints:
- `GET /health` — health check
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc
- `GET /openapi.json` — OpenAPI schema
- `GET /api/v1/...` — all API routes

---

## 5. Running tests

```bash
cd app

# Run all 90 tests
pytest tests/ -v

# Run with short traceback (cleaner output)
pytest tests/ -v --tb=short

# Run a specific test file
pytest tests/test_routers.py -v

# Run a specific test class
pytest tests/test_routers.py::TestCheckLineItems -v

# Run tests matching a keyword
pytest tests/ -v -k "expired"

# Run tests matching a keyword
pytest tests/ -v -k "RBAC"
```

### How tests work

All tests use an in-memory SQLite database via a pytest fixture in
`tests/conftest.py`. Each test runs inside a SQLAlchemy savepoint transaction
that is rolled back after the test completes — no test data persists between
tests and no database cleanup is needed.

```
conftest.py
  engine       — SQLite in-memory, created once per session
  db_session   — savepoint per test, rolled back after each test
  client       — Starlette TestClient bound to the test session
  auth_admin   — {"Authorization": "Bearer test-administrator"}
  auth_supervisor — {"Authorization": "Bearer test-supervisor"}
  auth_responder  — {"Authorization": "Bearer test-responder"}
```

### Test categories

| File | What it covers |
|------|---------------|
| `test_models.py` | ORM model creation, relationships, constraints |
| `test_routers.py` | All API endpoints, business rules, schema validation, RBAC |

---

## 6. Database migrations

EMS ReadyKit uses Alembic for database schema migrations.

```bash
cd app

# Apply all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# Show migration history
alembic history

# Create a new migration (auto-generates from model changes)
alembic revision --autogenerate -m "describe_what_changed"

# Roll back one migration
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade 0001_initial_schema
```

### Migration conventions

- Migration files live in `alembic/versions/`
- File naming: `{revision_id}_{short_description}.py`
- Current migrations:
  - `0001_initial_schema.py` — all base tables
  - `0002_compartments_and_line_items.py` — Phase 4 additions
  - `0003_phase6_extensions.py` — Phase 6 additions (planned)
- Always write both `upgrade()` and `downgrade()` functions
- Always include indexes and constraints in the migration, not just columns
- Test the downgrade path before merging

### Important: startup migration

`startup.sh` runs `alembic upgrade head` before starting gunicorn. This means
migrations run automatically on every App Service container restart. Migrations
must be idempotent — running them twice must be safe.

---

## 7. Project structure

```
app/
├── ems_readykit/
│   ├── core/
│   │   ├── auth.py          # JWT validation, CurrentUser, fake test tokens
│   │   ├── config.py        # Settings (pydantic-settings, reads .env)
│   │   ├── database.py      # SQLAlchemy engine, session factory, get_db
│   │   └── logging.py       # Structured logging configuration
│   │
│   ├── models/              # SQLAlchemy ORM models (one file per entity)
│   │   ├── __init__.py      # Exports all models (required for Alembic)
│   │   ├── base.py          # TimestampMixin (created_at, updated_at)
│   │   ├── station.py
│   │   ├── vehicle.py
│   │   ├── inventory_location.py
│   │   ├── compartment.py
│   │   ├── item.py
│   │   ├── stock_lot.py
│   │   ├── par_level.py
│   │   ├── daily_inventory_check.py
│   │   ├── check_line_item.py
│   │   ├── controlled_substance_check.py
│   │   └── audit_event.py
│   │
│   ├── schemas/             # Pydantic v2 schemas (one file per entity)
│   │   ├── __init__.py
│   │   ├── station.py       # StationCreate, StationRead
│   │   ├── vehicle.py
│   │   ├── inventory_location.py
│   │   ├── compartment.py
│   │   ├── item.py
│   │   ├── stock_lot.py
│   │   ├── par_level.py
│   │   ├── daily_inventory_check.py
│   │   ├── check_line_item.py
│   │   ├── controlled_substance_check.py
│   │   └── audit_event.py
│   │
│   ├── routers/             # FastAPI route handlers (one file per domain)
│   │   ├── deps.py          # Shared dependencies: get_db, get_current_user, require_role
│   │   ├── stations.py
│   │   ├── vehicles.py
│   │   ├── items.py
│   │   ├── inventory.py
│   │   ├── checks.py
│   │   └── audit.py
│   │
│   └── main.py              # App factory, router registration, CORS, health check
│
├── alembic/
│   ├── env.py               # Alembic environment configuration
│   └── versions/            # Migration files
│
├── tests/
│   ├── conftest.py          # Fixtures: engine, session, client, auth headers
│   ├── test_models.py       # ORM model tests
│   └── test_routers.py      # Router, business rule, RBAC tests
│
├── .env.example             # Template for local environment variables
├── alembic.ini              # Alembic configuration
├── app.py                   # WSGI entry point (imports from main.py)
├── Procfile                 # Process definition for App Service
├── pyproject.toml           # Project metadata and tool configuration
├── requirements.txt         # Pinned dependencies
└── startup.sh               # Container startup: migrate then serve
```

---

## 8. How to add a new endpoint

Follow this pattern consistently. Example: adding
`GET /api/v1/vehicles/{id}/repair-requests`.

### Step 1 — Add the model (if new entity)

Create `app/ems_readykit/models/repair_request.py`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ems_readykit.core.database import Base
from ems_readykit.models.base import TimestampMixin

class RepairRequest(TimestampMixin, Base):
    __tablename__ = "repair_requests"

    request_id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.vehicle_id"))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="FILED")
```

Export from `models/__init__.py`:

```python
from ems_readykit.models.repair_request import RepairRequest
```

### Step 2 — Add the schema

Create `app/ems_readykit/schemas/repair_request.py`:

```python
from pydantic import BaseModel, ConfigDict, Field

class RepairRequestCreate(BaseModel):
    severity: str = Field(..., pattern="^(URGENT|NON_URGENT)$")
    description: str = Field(..., max_length=500)

class RepairRequestRead(RepairRequestCreate):
    model_config = ConfigDict(from_attributes=True)
    request_id: int
    vehicle_id: int
    status: str
```

### Step 3 — Add the route

In the appropriate router file (or create a new one):

```python
@router.post(
    "/{vehicle_id}/repair-requests",
    response_model=RepairRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="File a repair request for a vehicle",
)
def create_repair_request(
    vehicle_id: int,
    payload: RepairRequestCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*_ALL_ROLES)),
) -> RepairRequest:
    """
    Files a repair request for a vehicle.
    URGENT requests notify the supervisor immediately.
    Audit event logged: REPAIR_REQUEST_FILED
    """
    vehicle = _get_vehicle_or_404(vehicle_id, db)
    request = RepairRequest(
        vehicle_id=vehicle_id,
        severity=payload.severity,
        description=payload.description,
        status="FILED",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    # ... audit event
    return request
```

### Step 4 — Write the migration

```bash
alembic revision --autogenerate -m "add_repair_requests"
# Review and edit the generated file
alembic upgrade head
```

### Step 5 — Write the tests

Add a `TestRepairRequests` class to `test_routers.py` following the existing
pattern. Cover: happy path, validation errors, 404, RBAC (each role).

### Step 6 — Update documentation

- Add endpoint to the relevant phase document endpoint table
- Update `docs/project_index.md` Phase 6 backlog status
- Add an audit event type constant if introducing a new action

---

## 9. How to add a new model

1. Create `app/ems_readykit/models/{name}.py` using `TimestampMixin`
2. Add FK relationships to related models (both sides)
3. Export from `models/__init__.py`
4. Create `app/ems_readykit/schemas/{name}.py` with Create and Read schemas
5. Export from `schemas/__init__.py`
6. Generate migration: `alembic revision --autogenerate -m "add_{name}"`
7. Review migration — add any indexes, constraints, or defaults not auto-detected
8. Run migration: `alembic upgrade head`
9. Add model tests to `test_models.py`
10. Update `docs/phase{N}_{name}.md` with the new entity definition

---

## 10. Authentication in development

In `APP_ENV=development` (the default), the API accepts fake bearer tokens
instead of real Azure AD JWTs. This allows local development and pytest
without any Azure AD configuration.

| Token | Role | Use for |
|-------|------|---------|
| `test-responder` | Responder | Testing crew member endpoints |
| `test-supervisor` | Supervisor | Testing supervisor endpoints |
| `test-administrator` | Administrator | Testing admin endpoints |

```bash
# Example: create a station as administrator
curl -X POST http://localhost:8000/api/v1/stations \
  -H "Authorization: Bearer test-administrator" \
  -H "Content-Type: application/json" \
  -d '{"name": "Station 1", "address": "123 Main St"}'

# Example: submit a daily check as responder
curl -X POST http://localhost:8000/api/v1/checks/daily \
  -H "Authorization: Bearer test-responder" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id": 1, "station_id": 1, "check_date": "2026-05-15", ...}'
```

In pytest, use the auth fixtures from `conftest.py`:

```python
def test_create_station(client, auth_admin):
    response = client.post("/api/v1/stations", json={...}, headers=auth_admin)
    assert response.status_code == 201

def test_responder_cannot_create_station(client, auth_responder):
    response = client.post("/api/v1/stations", json={...}, headers=auth_responder)
    assert response.status_code == 403
```

### Testing with real Azure AD tokens (optional)

If `AZURE_AD_TENANT_ID` is set in development, real Azure AD tokens are also
accepted. Obtain one with:

```bash
az account get-access-token \
  --resource api://<AZURE_AD_CLIENT_ID> \
  --query accessToken -o tsv
```

---

## 11. CI/CD pipeline

The pipeline in `.github/workflows/deploy.yml` runs on every push to `main`
and every pull request.

```
Push to main or PR
    │
    ▼
Job 1: test
    ubuntu-latest
    pip install requirements.txt
    pytest tests/ -v --tb=short
    │
    ▼ (on pass, main branch only)
Job 2: deploy
    ubuntu-latest
    Build zip on Linux (forward-slash paths — critical for Oryx)
    az login via AZURE_CREDENTIALS secret
    azure/webapps-deploy@v3
    curl /health → must return 200
```

**Required GitHub secret:**

| Secret | How to create |
|--------|--------------|
| `AZURE_CREDENTIALS` | `az ad sp create-for-rbac --name "ems-readykit-github" --sdk-auth --role Contributor --scopes /subscriptions/{id}/resourceGroups/rg-ems-readykit-dev` |

**Critical: always build the zip on Linux.** Windows `Compress-Archive`
creates backslash paths that Oryx (Azure's build system) cannot extract as
directories. The pipeline builds on `ubuntu-latest` for this reason. If you
need to deploy manually, use WSL or a Linux machine.

---

## 12. Deployment

### Automated (recommended)

Push to `main`. The pipeline handles everything.

### Manual (emergency only)

```bash
# On Linux or WSL
cd app
mkdir -p /tmp/ems_stage
cp -r alembic ems_readykit alembic.ini app.py Procfile \
      pyproject.toml requirements.txt startup.sh /tmp/ems_stage/
cd /tmp/ems_stage
zip -r /tmp/deploy.zip .

az webapp deploy \
  --resource-group rg-ems-readykit-dev \
  --name app-ems-readykit-dev \
  --src-path /tmp/deploy.zip \
  --type zip

# Verify health
curl https://app-ems-readykit-dev.azurewebsites.net/health
```

### Terraform infrastructure

```bash
cd iac/Terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

See `docs/runbook.md` for full infrastructure deployment and teardown procedures.

---

## 13. Code style and standards

### Python

- Type hints on all function signatures
- Docstrings on all public functions and router endpoints
- Private helpers prefixed with `_` (e.g. `_compute_check_status`)
- No bare `except:` — always catch specific exceptions
- No magic numbers — use named constants or enums
- All business logic in router helper functions, not inline in route handlers
- Imports: stdlib → third-party → local, separated by blank lines

### FastAPI patterns

```python
# Always use require_role — never skip authentication
@router.get(
    "/path",
    response_model=SchemaRead,
    summary="One-line description shown in Swagger",
    dependencies=[Depends(require_role("Supervisor", "Administrator"))],
)
def handler(db: Session = Depends(get_db)) -> Model:
    """
    Longer description in the docstring.
    Shown in Swagger UI and API docs.
    Explains: what it returns, what roles can use it, any business rules.
    """
    ...

# When you need the current user in the handler body
@router.post("/path")
def handler(
    payload: SchemaCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("Responder", "Supervisor")),
) -> Model:
    performed_by = current_user.name  # always bind identity server-side
    ...
```

### SQLAlchemy patterns

```python
# Use mapped_column with type annotations (SQLAlchemy 2.0 style)
class MyModel(TimestampMixin, Base):
    __tablename__ = "my_models"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    optional_field: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

# Use relationship with TYPE_CHECKING for circular imports
if TYPE_CHECKING:
    from ems_readykit.models.other import Other

class MyModel(Base):
    other: Mapped["Other"] = relationship("Other", back_populates="mine")
```

### Pydantic patterns

```python
# Always use ConfigDict(from_attributes=True) on Read schemas
class MyModelRead(MyModelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
```

### Naming conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Models | PascalCase | `DailyInventoryCheck` |
| Tables | snake_case | `daily_inventory_checks` |
| Schema classes | PascalCase + suffix | `DailyInventoryCheckCreate`, `DailyInventoryCheckRead` |
| Route handlers | snake_case verb + noun | `create_daily_check`, `list_vehicle_cs_checks` |
| Helper functions | `_snake_case` (private) | `_compute_check_status` |
| Constants | `UPPER_SNAKE_CASE` | `ROLE_ADMINISTRATOR` |
| Test classes | `TestSubjectEndpoints` | `TestCheckLineItems` |
| Test functions | `test_specific_behavior` | `test_expired_lot_sets_status_fail` |

---

## 14. Documentation standards

Every new phase or significant feature should have a phase document in `docs/`
following the standard structure:

1. Executive Summary — one paragraph
2. Objectives — table
3. Scope — explicit in/out of scope
4. Technical Decisions — key choices with rationale
5. Deliverables — table with location and status
6. Testing — strategy and results
7. Known Issues and Tradeoffs
8. Phase Dependencies
9. Next Phase

For significant architectural decisions, write an ADR in `docs/adr/` following
the template in `ADR-001-Architecture.md`.

Update `docs/project_index.md` whenever:
- A phase changes status
- A new endpoint is added or removed from the backlog
- A new ADR is written
- A significant technical decision changes

---

## 15. Branching and pull requests

```
main          — always deployable; protected branch
feature/*     — new features (e.g. feature/repair-requests)
fix/*         — bug fixes (e.g. fix/expiry-date-hybrid-property)
docs/*        — documentation only (e.g. docs/contributing-guide)
```

### Pull request checklist

Before opening a PR, verify:

- [ ] All 90+ existing tests pass: `pytest tests/ -v`
- [ ] New functionality has tests covering: happy path, validation errors, 404s, and all RBAC combinations
- [ ] New models have a migration with both `upgrade()` and `downgrade()`
- [ ] New endpoints have docstrings explaining: what they return, required role, business rules
- [ ] `docs/project_index.md` updated if backlog status changed
- [ ] Phase document updated if scope or deliverables changed
- [ ] No secrets, tokens, or credentials in committed files
- [ ] No `print()` statements — use `logger.info()` / `logger.warning()`

### Commit message format

```
type: short description (50 chars max)

Optional longer explanation if needed.
Reference relevant phase or ADR if applicable.

Types: feat, fix, docs, test, refactor, chore, ci
```

Examples:
```
feat: add repair request endpoint with URGENT escalation
fix: hybrid property lot_number returns None on missing lot
docs: Phase 5 UX review — field-optimized design changes
test: add TestRepairRequests covering lifecycle and RBAC
chore: bump PyJWT to 2.9.0
ci: add health check retry on slow cold start
```
