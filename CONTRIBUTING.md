# Contributing to EMS ReadyKit

This guide covers everything you need to get a local development environment
running, understand the codebase, and contribute changes confidently.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Local setup](#2-local-setup)
3. [Environment variables](#3-environment-variables)
4. [Running the API](#4-running-the-api)
5. [Running tests](#5-running-tests)
6. [Seeding the database](#6-seeding-the-database)
7. [Database migrations](#7-database-migrations)
8. [Project structure](#8-project-structure)
9. [How to add a new endpoint](#9-how-to-add-a-new-endpoint)
10. [How to add a new model](#10-how-to-add-a-new-model)
11. [Authentication in development](#11-authentication-in-development)
12. [CI/CD pipeline](#12-cicd-pipeline)
13. [Deployment](#13-deployment)
14. [Code style and standards](#14-code-style-and-standards)
15. [Branching and pull requests](#15-branching-and-pull-requests)

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| Git | Any recent | https://git-scm.com |
| Terraform | 1.6+ | https://developer.hashicorp.com/terraform/install |
| Azure CLI | Any recent | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |

You do NOT need a running PostgreSQL instance for local development or testing.
The test suite uses SQLite in-memory. The API defaults to SQLite when no
`DATABASE_URL` is set.

---

## 2. Local setup

**Windows PowerShell:**

```powershell
# Clone the repository
git clone https://github.com/Jinniyah/EMS_ReadyKit.git
cd EMS_ReadyKit

# Backend setup
cd app
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Apply migrations and seed
alembic upgrade head
python seed.py

# Start the API
uvicorn ems_readykit.main:app --reload --port 8000
```

**Frontend (separate terminal):**

```powershell
cd frontend
npm install
npm run dev       # proxies API calls to port 8000
```

API explorer: http://localhost:8000/docs
Frontend: http://localhost:5173

---

## 3. Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `development` | Set to `production` to enable real JWT validation |
| `DATABASE_URL` | No | SQLite file | PostgreSQL connection string for production |
| `AZURE_AD_TENANT_ID` | No | — | Required for production JWT validation |
| `AZURE_AD_CLIENT_ID` | No | — | App Registration client ID |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed origins |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Frontend API base URL |

In `APP_ENV=development` (the default), real Azure AD tokens are not required.
Use the fake test tokens described in section 11.

In `APP_ENV=production`, `AZURE_AD_TENANT_ID` and `AZURE_AD_CLIENT_ID` are
required. The API rejects all requests without a valid Azure AD JWT.

---

## 4. Running the API

```powershell
cd app

# Development server with auto-reload
uvicorn ems_readykit.main:app --reload --port 8000

# Production-style (same as App Service)
gunicorn ems_readykit.main:app `
    --worker-class uvicorn.workers.UvicornWorker `
    --bind 0.0.0.0:8000 `
    --workers 2
```

Key endpoints:
- `GET /health` — health check
- `GET /docs` — Swagger UI (non-prod only)
- `GET /api/v1/...` — all API routes

---

## 5. Running tests

```powershell
cd app

# Full suite (349 tests, ~6 seconds)
pytest tests/ -q

# Verbose with short tracebacks
pytest tests/ -v --tb=short

# Save output to file (useful for sharing failures)
pytest tests/ -v --tb=long 2>&1 | Out-File -FilePath test_results.txt -Encoding utf8

# Specific file
pytest tests/test_priority_items.py -v
pytest tests/test_safety_checks.py -v
pytest tests/test_seed_integrity.py -v   # requires seeded dev DB

# Keyword filter
pytest tests/ -v -k "AED"
pytest tests/ -v -k "RBAC"
pytest tests/ -v -k "supervisor"
```

### How tests work

**Two database fixtures — do not mix them:**

`db` — in-memory SQLite, used by almost all tests:
- Created fresh for each test session
- Each test runs inside a SQLAlchemy savepoint that rolls back after the test
- No external services required
- Use this for all API/business logic tests

`seeded_db` — read-only connection to `ems_readykit_dev.db`, used only by `test_seed_integrity.py`:
- Connects to the actual seeded development database
- Read-only by convention — tests must never write to it
- Skips automatically with a clear message if `ems_readykit_dev.db` does not exist
- Use this only to verify that `seed.py` produced correct operational data

```python
# conftest.py provides these fixtures and auth headers:
# db           — in-memory SQLite session (rolls back after each test)
# seeded_db    — read-only session on ems_readykit_dev.db
# client       — Starlette TestClient bound to the in-memory db
# auth_admin       — {"Authorization": "Bearer test-administrator"}
# auth_supervisor  — {"Authorization": "Bearer test-supervisor"}
# auth_responder   — {"Authorization": "Bearer test-responder"}
```

### Test file overview

| File | What it covers | Fixture |
|------|---------------|---------|
| `test_routers.py` | Main router integration tests | `db` |
| `test_supply_room.py` | Supply room SR-B1/B2/B3/B4 | `db` |
| `test_repair_requests.py` | Repair request lifecycle | `db` |
| `test_station_membership.py` | RBAC + station membership enforcement | `db` |
| `test_check_history.py` | Check history, soft-delete, acknowledgement | `db` |
| `test_admin_items.py` | Admin item management, par levels, CSV | `db` |
| `test_models.py` | Model-level unit tests | `db` |
| `test_priority_items.py` | AED + LUCAS all check types; legal immutability | `db` |
| `test_persona_responder.py` | Jamie (Responder): all 5 check types; FAIL+comment flow | `db` |
| `test_persona_supervisor.py` | Earl (Supervisor): damaged item regression; repair requests | `db` |
| `test_persona_admin.py` | Jennifer (Admin): supply room decrement; role alias regression | `db` |
| `test_safety_checks.py` | O₂ PSI below minimum; date recurrence overdue; requires_full_check | `db` |
| `test_seed_integrity.py` | Verifies Unit 712, PC 8, AED/LUCAS, Truck Operations in dev DB | `seeded_db` |

### Known xfail

`test_safety_checks.py::TestRequiresFullCheck::test_requires_full_check_true_blocks_no_change`
documents that the router does not yet enforce `requires_full_check=True` on the
Truck Operations compartment. This must be implemented before launch (backlog SEED-GAP2).
When it is fixed, the test will flip to pass automatically.

### Test isolation note

Route handlers that call `db.commit()` release the active SQLAlchemy savepoint.
Any fixture creating a row with a UNIQUE constraint must use get-or-create
semantics. See `test_item` and `vehicle_location` fixtures in `test_supply_room.py`
for the established pattern.

### TestClient.delete() body

Starlette's TestClient does not support `json=` or `content=` kwargs on DELETE.
Use `client.request()` instead:

```python
r = client.request(
    "DELETE",
    f"/api/v1/checks/daily/{check_id}",
    content=json.dumps({"deletion_reason": "reason"}),
    headers={**auth_admin, "Content-Type": "application/json"},
)
```

---

## 6. Seeding the database

The dev seed creates realistic operational data for Newberg Township EMS:

```powershell
cd app
python seed.py
```

What gets created:
- **Newberg Township Station 1** — Unit 712 BLS ambulance (26+ compartments, 200+ par levels) + Unit 712 Jump Bag
- **Marcellus Township Station 1** — Unit 540 ALS ambulance
- **⚠ TEST STATION** — Unit TEST QRV with 2 compartments covering all 5 check types

Key seeded items:
- `AED Battery` — FUNCTIONAL, `priority_check=True`, `priority_question="AED shows READY?"`
- `AED Date of Last Charge` — DATE_RECORD, `recurrence_days=90`
- `LUCAS Device Ready Check` — FUNCTIONAL, `priority_check=True`
- `LUCAS Date of Last Charge` — DATE_RECORD, `recurrence_days=30`
- `On-Board O2 PSI` — MEASUREMENT, `measurement_minimum=500.0` PSI
- `Truck Operations` compartment — `requires_full_check=True`

To reseed from scratch:

```powershell
cd app
Remove-Item ems_readykit_dev.db
alembic upgrade head
python seed.py
```

---

## 7. Database migrations

EMS ReadyKit uses Alembic for schema migrations. 18 migrations are currently applied.

```powershell
cd app

# Apply all pending migrations
alembic upgrade head

# Check current version
alembic current

# Show history
alembic history

# Create a new migration (auto-generates from model changes)
alembic revision --autogenerate -m "describe_what_changed"

# Roll back one migration
alembic downgrade -1
```

### Migration conventions

- Always use **batch mode** for ALTER TABLE — required for SQLite compatibility in tests:

```python
with op.batch_alter_table("my_table") as batch_op:
    batch_op.add_column(sa.Column("new_field", sa.Boolean(), nullable=False, server_default=sa.false()))
```

- Always write both `upgrade()` and `downgrade()` functions
- Use Python `True`/`False` for boolean literals in raw SQL — never `0`/`1` (PostgreSQL rejects integers for boolean columns)
- After adding a migration, update the migration table in `CODEBASE_INDEX.md`
- `startup.sh` runs `alembic upgrade head` before gunicorn starts — migrations must be idempotent

---

## 8. Project structure

```
app/
├── ems_readykit/
│   ├── core/
│   │   ├── auth.py          # JWT validation, CurrentUser, test token handling
│   │   ├── audit.py         # write_audit_event() — always use this, never inline
│   │   ├── config.py        # Settings (pydantic-settings, reads .env)
│   │   ├── database.py      # SQLAlchemy engine, session factory, get_db
│   │   └── logging.py       # Structured logging configuration
│   │
│   ├── models/              # SQLAlchemy ORM models (one file per entity)
│   │   ├── __init__.py      # Exports all models (required for Alembic)
│   │   ├── base.py          # TimestampMixin (created_at, updated_at)
│   │   ├── station.py
│   │   ├── vehicle.py
│   │   ├── inventory_location.py   # LocationType: VEHICLE, JUMP_BAG, STATION_SUPPLY_ROOM
│   │   ├── compartment.py          # requires_full_check on Truck Operations
│   │   ├── item.py                 # ItemCheckType enum; station_supply; measurement_minimum
│   │   ├── stock_lot.py
│   │   ├── par_level.py            # priority_check, priority_question, is_damaged
│   │   ├── daily_inventory_check.py  # CheckStatus: PASS/NEEDS_RESTOCK/FAIL
│   │   ├── check_line_item.py        # LineItemStatus: OK/SHORT/LOW/MISSING/EXPIRED/OVERDUE/FAIL
│   │   ├── controlled_substance_check.py
│   │   ├── repair_request.py
│   │   ├── station_member.py       # user_id = email (JWT preferred_username)
│   │   ├── stock_transfer.py
│   │   └── audit_event.py          # Immutable; always write via core/audit.py
│   │
│   ├── schemas/             # Pydantic v2 schemas (one file per entity)
│   │
│   ├── routers/             # FastAPI route handlers (one file per domain)
│   │   ├── deps.py          # ALL_ROLES, SUPERVISOR_PLUS, ADMIN_ONLY, require_role,
│   │   │                    # get_vehicle_or_404, require_station_membership
│   │   ├── stations.py
│   │   ├── station_members.py
│   │   ├── vehicles.py
│   │   ├── items.py         # POST /items is SUPERVISOR_PLUS (not admin-only)
│   │   ├── inventory.py     # Supply catalog, par levels, lots, PATCH /items/{id}/status
│   │   ├── checks.py        # _compute_line_item_status, _auto_decrement_supply_room
│   │   ├── check_history.py
│   │   ├── repair_requests.py
│   │   ├── admin.py         # Item deactivation (ADMIN_ONLY); par level PATCH
│   │   └── audit.py
│   │
│   └── main.py              # App factory, middleware, router registration order
│
├── alembic/
│   ├── env.py
│   └── versions/            # 18 migration files (0001–0018 + 0003a)
│
├── tests/
│   ├── conftest.py          # db, seeded_db, client, auth_admin/supervisor/responder
│   ├── test_routers.py      # 67 KB — main integration tests
│   ├── test_supply_room.py
│   ├── test_repair_requests.py
│   ├── test_station_membership.py
│   ├── test_check_history.py
│   ├── test_admin_items.py
│   ├── test_models.py
│   ├── test_priority_items.py
│   ├── test_persona_responder.py
│   ├── test_persona_supervisor.py
│   ├── test_persona_admin.py
│   ├── test_safety_checks.py
│   └── test_seed_integrity.py
│
├── seed.py                  # Idempotent dev seed (Unit 712 + Marcellus 540 + TEST)
├── initial_stock.csv        # 10 seed stock items for supply room
├── alembic.ini
├── app.py                   # WSGI entry point
├── Procfile
├── pyproject.toml
├── requirements.txt
└── startup.sh               # Container startup: alembic upgrade head → gunicorn

frontend/
├── src/
│   ├── modules/             # Feature modules (self-contained: index.jsx, api/, components/)
│   │   ├── check-wizard/    # 5-step check flow
│   │   ├── supervisor/      # Compliance dashboard
│   │   ├── admin/           # Station administration
│   │   ├── supply-room/     # Station supplies
│   │   ├── vehicles/        # V&E Status
│   │   └── check-history/   # Check history
│   ├── pages/               # Top-level pages (HomePage, NotFoundPage)
│   ├── shared/
│   │   ├── api/             # client.js (Axios), authConfig.js, stationsApi.js
│   │   ├── hooks/           # useAuth, useDraft, useRoleMode, useApi
│   │   ├── components/      # UserPill, Modal, StatusBadge, DevBanner, etc.
│   │   └── utils/           # roleGuard.js (canAccess), statusCalc.js
│   └── App.jsx              # Router, auth guard, top-level layout
└── index.css                # Design tokens (:root CSS variables) — use these everywhere
```

---

## 9. How to add a new endpoint

Follow this pattern. Example: a new `GET /vehicles/{id}/status` endpoint.

### Step 1 — Read first

Read the relevant router, model, and schema files before writing anything.
Use `filesystem:read_multiple_files` for related files simultaneously.

### Step 2 — Add or update the schema

```python
# schemas/vehicle.py
class VehicleStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    vehicle_id: int
    active: bool
    inactive_reason: Optional[str]
```

### Step 3 — Add the route

```python
# routers/vehicles.py
from ems_readykit.routers.deps import ALL_ROLES, require_role, get_vehicle_or_404

@router.get(
    "/{vehicle_id}/status",
    response_model=VehicleStatusRead,
    summary="Get vehicle active/inactive status",
)
def get_vehicle_status(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> Vehicle:
    vehicle = get_vehicle_or_404(vehicle_id, db)
    require_station_membership(vehicle.station_id, current_user, db)
    return vehicle
```

### Step 4 — Write the tests

Add to the appropriate persona or domain test file. Cover:
- Happy path (correct response)
- 404 (entity not found)
- 403 (role too low)
- Station membership denial (if applicable)

### Step 5 — Write the audit event (if mutating)

```python
from ems_readykit.core.audit import write_audit_event

write_audit_event(
    db,
    actor=current_user.name,      # always actor=, never performed_by=
    action="VEHICLE_STATUS_CHANGED",
    entity_type="vehicle",
    entity_id=str(vehicle_id),
    station_id=vehicle.station_id,
    vehicle_id=vehicle_id,
    metadata={"active": payload.active},  # always metadata=, never detail=
    severity="INFO",
)
```

### Step 6 — Add migration if schema changed

```powershell
cd app
alembic revision --autogenerate -m "add_vehicle_status_fields"
# Review the generated file — add indexes if needed
alembic upgrade head
```

Update the migration table in `CODEBASE_INDEX.md`.

---

## 10. How to add a new model

1. Create `app/ems_readykit/models/{name}.py` using `TimestampMixin`
2. Add FK relationships to related models (both sides of the relationship)
3. Export from `models/__init__.py`
4. Create `app/ems_readykit/schemas/{name}.py` with `{Name}Create` and `{Name}Read`
5. Generate migration: `alembic revision --autogenerate -m "add_{name}"`
6. Review migration — use batch mode for any ALTER TABLE
7. Run: `alembic upgrade head`
8. Add model tests to `test_models.py`
9. Update `CODEBASE_INDEX.md` migration table

---

## 11. Authentication in development

In `APP_ENV=development` (the default), the API accepts fake bearer tokens
instead of real Azure AD JWTs. The test tokens map to station memberships
created by `seed.py`.

| Token | Role | Email |
|-------|------|-------|
| `Bearer test-responder` | Responder | test-responder@ems.local |
| `Bearer test-supervisor` | Supervisor | test-supervisor@ems.local |
| `Bearer test-administrator` | Administrator | test-administrator@ems.local |
| `Bearer test-admin` | Administrator | test-administrator@ems.local (alias) |

```powershell
# Submit a daily check as responder
curl -X POST http://localhost:8000/api/v1/checks/daily `
  -H "Authorization: Bearer test-responder" `
  -H "Content-Type: application/json" `
  -d '{"vehicle_id": 1, "station_id": 1, "check_date": "2026-06-08", "timestamp": "2026-06-08T10:00:00Z", "line_items": []}'

# Create a station as administrator
curl -X POST http://localhost:8000/api/v1/stations `
  -H "Authorization: Bearer test-administrator" `
  -H "Content-Type: application/json" `
  -d '{"name": "Test Station", "address": "1 Main St", "region": "Test"}'
```

In pytest, use the auth fixtures from `conftest.py`:

```python
def test_responder_cannot_create_item(client, auth_responder):
    r = client.post("/api/v1/items", json={
        "name": "Test Item",
        "category": "Equipment",
        "unit_of_measure": "each",
    }, headers=auth_responder)
    assert r.status_code == 403   # Responder denied — must be Supervisor+
```

**Role boundary to know:** `POST /api/v1/items` is `SUPERVISOR_PLUS` — both
Supervisor and Administrator can create items. Only `PATCH /admin/items/{id}/deactivate`
is `ADMIN_ONLY`.

---

## 12. CI/CD pipeline

The pipeline in `.github/workflows/deploy.yml` runs on every push to `main`
and every pull request.

```
Push to main or PR
    │
    ▼
Job 1: test
    ubuntu-latest
    pip install -r requirements.txt
    pytest tests/ -v --tb=short   (349 tests must pass)
    │
    ▼ (on pass, main branch only)
Job 2: deploy
    ubuntu-latest
    Build zip on Linux (critical — forward-slash paths for Azure Oryx)
    az login via AZURE_CREDENTIALS secret
    azure/webapps-deploy@v3
    curl /health → must return 200
```

**Required GitHub secret:**

| Secret | How to create |
|--------|--------------|
| `AZURE_CREDENTIALS` | `az ad sp create-for-rbac --name "ems-readykit-github" --sdk-auth --role Contributor --scopes /subscriptions/{id}/resourceGroups/rg-ems-readykit-dev` |

---

## 13. Deployment

### Automated (recommended)

Push to `main`. The pipeline handles everything.

### Manual (emergency only — must use Linux or WSL)

```bash
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

curl https://app-ems-readykit-dev.azurewebsites.net/health
```

> **Never build the zip on Windows.** `Compress-Archive` creates backslash paths
> that Oryx cannot extract as directories.

### Terraform infrastructure

```bash
cd iac/Terraform
# Delete the delete-lock before apply
az lock delete --name delete-lock --resource-group rg-ems-readykit-dev
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

See `docs/runbook.md` for full infrastructure procedures.

---

## 14. Code style and standards

### Python

- Type hints on all function signatures
- Docstrings on all public functions and router endpoints
- Private helpers prefixed with `_` (e.g. `_compute_check_status`)
- No bare `except:` — always catch specific exceptions
- No magic numbers — use named constants or enums
- Always import role constants from `deps.py` — never re-declare locally

### FastAPI patterns

```python
# Access control only (no user object needed):
@router.get(
    "/path",
    response_model=SchemaRead,
    summary="One-line description",
    dependencies=[Depends(require_role(*ADMIN_ONLY))],
)
def handler(db: Session = Depends(get_db)) -> Model:
    """Longer description. What it returns. Business rules."""
    ...

# Access control + identity in handler:
@router.post("/path")
def handler(
    payload: SchemaCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*ALL_ROLES)),
) -> Model:
    performed_by = current_user.name   # always bind identity server-side
    ...
```

### Audit events

```python
# Always use write_audit_event — never inline AuditEvent()
write_audit_event(
    db,
    actor=current_user.name,     # actor= not performed_by=
    action="ACTION_NAME",
    entity_type="entity",
    entity_id=str(entity.id),
    station_id=station_id,
    metadata={"key": "value"},   # metadata= not detail=
    severity="INFO",
)
```

### SQLAlchemy

```python
# SQLAlchemy 2.0 mapped_column style
class MyModel(TimestampMixin, Base):
    __tablename__ = "my_models"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                       server_default=sa.false())
    optional: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

### Naming conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Models | PascalCase | `DailyInventoryCheck` |
| Tables | snake_case | `daily_inventory_checks` |
| Schema classes | PascalCase + suffix | `DailyInventoryCheckCreate` |
| Route handlers | snake_case verb + noun | `create_daily_check` |
| Private helpers | `_snake_case` | `_compute_check_status` |
| Constants | `UPPER_SNAKE_CASE` | `ROLE_ADMINISTRATOR` |
| Test classes | `TestSubjectBehavior` | `TestAEDChecks` |
| Test functions | `test_specific_behavior` | `test_aed_date_one_day_past_recurrence_is_overdue` |

---

## 15. Branching and pull requests

```
main          — always deployable; protected branch
feature/*     — new features
fix/*         — bug fixes
docs/*        — documentation only
```

### Pull request checklist

Before opening a PR:

- [ ] All 349 tests pass: `pytest tests/ -q`
- [ ] New functionality has tests: happy path, validation errors, 404s, RBAC
- [ ] New models have a migration with `upgrade()` and `downgrade()`
- [ ] Audit events use `actor=` and `metadata=` kwargs (not `performed_by=`/`detail=`)
- [ ] `CODEBASE_INDEX.md` updated if files were added or migrations added
- [ ] `docs/project_index.md` updated if backlog status changed
- [ ] No secrets, tokens, or credentials in committed files
- [ ] No `print()` statements — use `logger.info()` / `logger.warning()`

### Commit message format

```
type: short description (50 chars max)

Optional explanation. Reference backlog item if applicable.

Types: feat, fix, docs, test, refactor, chore, ci
```

Examples:
```
feat: add requires_full_check enforcement on Truck Operations compartment
fix: write_audit_event kwargs — actor/metadata not performed_by/detail
test: add seed integrity tests for Unit 712 PC 8 and AED/LUCAS items
docs: update CODEBASE_INDEX and project_index for Session L post-close
chore: remove orphan Unit 710 Jump Bag from Newberg Township seed
```
