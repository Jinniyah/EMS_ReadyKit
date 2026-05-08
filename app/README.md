# EMS ReadyKit — Application

FastAPI (Python 3.11) web/API application for vehicle readiness and inventory management.

---

## Project Structure

```
app/
├── ems_readykit/
│   ├── core/
│   │   ├── config.py       — Settings (env vars, Key Vault resolution)
│   │   ├── database.py     — SQLAlchemy engine, session factory, get_db dependency
│   │   └── logging.py      — Structured JSON logging (production) / console (dev)
│   ├── models/             — SQLAlchemy ORM models (full domain)
│   ├── schemas/            — Pydantic request/response models (Phase 2)
│   ├── routers/            — FastAPI route handlers (Phase 2)
│   └── main.py             — Application factory and startup
├── alembic/                — Database migrations
│   └── versions/
│       └── 0001_initial_schema.py
├── tests/
│   ├── conftest.py         — In-memory SQLite fixtures
│   └── test_models.py      — Phase 1 model and health check tests
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Local Development Setup

```bash
cd app

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env — defaults use SQLite, no Azure dependencies needed locally

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn ems_readykit.main:app --reload

# API docs available at:
#   http://localhost:8000/docs     (Swagger UI)
#   http://localhost:8000/redoc    (ReDoc)
#   http://localhost:8000/health   (health check)
```

---

## Running Tests

```bash
cd app
pytest -v
```

All Phase 1 tests use an in-memory SQLite database — no network or Azure connection required.

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Generate a new migration after changing models
alembic revision --autogenerate -m "describe your change"
```

---

## Domain Model

| Entity | Description |
|---|---|
| `Station` | Physical EMS station — top-level scope |
| `Vehicle` | Ambulance or response unit (ALS/BLS/QRV) assigned to a station |
| `InventoryLocation` | VEHICLE or STATION_SUPPLY_ROOM container for stock |
| `Item` | What is tracked (Medication, Consumable, Equipment) |
| `StockLot` | Quantity of an item at a location with lot number and expiration |
| `ParLevel` | Min/max stock levels per item per location |
| `DailyInventoryCheck` | Required once per active vehicle per calendar day |
| `ControlledSubstanceCheck` | Double-signature workflow for ALS vehicles only |
| `AuditEvent` | Immutable log of all material system actions |

---

## Phase Roadmap

- **Phase 1 ✅** — Project scaffold, ORM models, migrations, database config
- **Phase 2** — Inventory CRUD API (stations, vehicles, items, stock lots, par levels, daily checks)
- **Phase 3** — Controlled substance workflow, audit trail, expiration alerts
