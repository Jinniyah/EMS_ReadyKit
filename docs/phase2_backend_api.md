# EMS ReadyKit — Phase 2: Backend API
# Document version: 1.0
# Status: Complete
# Last updated: 2026-05-15

---

## 1. Executive Summary

Phase 2 delivered a production-quality REST API implementing the full EMS
ReadyKit domain model. Built with FastAPI and SQLAlchemy on PostgreSQL, the
API covers station and vehicle management, compartment-level inventory tracking,
daily readiness checks with per-item validation, expiration management via
stock lot tracking, controlled substance dual-signature workflows, and a
comprehensive audit trail. Seventy-four automated tests validate all endpoints,
business rules, and data integrity constraints.

---

## 2. Objectives

| Objective | Description |
|-----------|-------------|
| Domain model | Accurate representation of EMS operational hierarchy (Station → Vehicle → Compartment → Item) |
| REST API | Complete CRUD endpoints for all domain entities |
| Business rules | Enforcement of EMS operational rules in application logic |
| Data integrity | Database-level constraints and application-level validation |
| Expiration tracking | Per-lot expiration with check-time verification |
| Controlled substances | Dual-signature workflow with discrepancy audit events |
| Audit trail | First-class audit events for all material actions |
| Test coverage | Automated test suite covering models, routers, schema validation, and RBAC |

---

## 3. Scope

### In scope
- FastAPI application with six routers
- SQLAlchemy 2.0 ORM models (11 entities)
- Alembic database migrations (0001 initial schema, 0002 Phase 4 additions)
- Pydantic v2 request/response schemas
- Business rule enforcement (CS dual-sign, one check per vehicle per day, etc.)
- Health check endpoint
- Audit event generation for all material actions
- 74-test automated test suite

### Out of scope
- Authentication and authorization (Phase 3)
- CI/CD pipeline (Phase 3)
- Frontend (Phase 5)
- Notification delivery (Phase 6)

---

## 4. Domain Model

The domain model mirrors real EMS operational hierarchy:

```
Station
 └── Vehicle (assigned to exactly one Station)
      ├── InventoryLocation (vehicle-level)
      │    └── Compartment (physical storage area — Phase 4)
      │         └── ParLevel (per-item required quantity)
      └── DailyInventoryCheck
           └── CheckLineItem (per-item count per compartment — Phase 4)
                └── StockLot (lot number + expiration date)

Station
 └── InventoryLocation (station supply room)
      └── StockLot

Vehicle (ALS only)
 └── ControlledSubstanceCheck (dual-signature)

AuditEvent (all material actions)
```

### Entity summary

| Entity | Purpose |
|--------|---------|
| Station | Physical EMS station; RBAC and reporting scope |
| Vehicle | Ambulance or response unit; check and CS workflow owner |
| InventoryLocation | Abstract location (vehicle or supply room) |
| Compartment | Named physical storage area on vehicle (Phase 4) |
| Item | Catalog entry — what is tracked |
| StockLot | Quantity + lot number + expiration date per location |
| ParLevel | Minimum/maximum required quantity per item per compartment |
| DailyInventoryCheck | Header record — one per vehicle per calendar day |
| CheckLineItem | Per-item Need/Have count per compartment per check (Phase 4) |
| ControlledSubstanceCheck | Dual-signature narcotics accountability record |
| AuditEvent | Immutable record of all material actions |

---

## 5. API Endpoints

### Stations (`/api/v1/stations`)
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/stations` | Administrator | Create station |
| GET | `/stations` | Supervisor, Administrator | List active stations |
| GET | `/stations/{id}` | Supervisor, Administrator | Get station detail |
| GET | `/stations/{id}/vehicles` | All roles | List vehicles at station |

### Vehicles (`/api/v1/vehicles`)
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/vehicles` | Administrator | Create vehicle; auto-creates InventoryLocation |
| GET | `/vehicles/{id}` | All roles | Get vehicle detail |

### Items (`/api/v1/items`)
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/items` | Administrator | Create item in catalog |
| GET | `/items` | All roles | List items with optional filters |
| GET | `/items/{id}` | All roles | Get item detail |

### Inventory (`/api/v1/inventory`)
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/inventory/locations` | All roles | List all inventory locations |
| GET | `/inventory/locations/{id}` | All roles | Get location detail |
| GET | `/inventory/locations/{id}/stock` | All roles | List stock lots at location |
| GET | `/inventory/locations/{id}/par-levels` | All roles | List par levels at location |
| GET | `/inventory/locations/{id}/compartments` | All roles | List compartments at location |
| POST | `/inventory/locations/{id}/compartments` | Supervisor, Administrator | Create compartment |
| GET | `/inventory/compartments/{id}` | All roles | Get compartment detail |
| POST | `/inventory/lots` | Supervisor, Administrator | Create stock lot |
| GET | `/inventory/lots/{id}` | All roles | Get stock lot |
| GET | `/inventory/expiring` | All roles | List expiring lots (configurable window) |
| POST | `/inventory/par-levels` | Supervisor, Administrator | Create par level |
| GET | `/inventory/par-levels/{id}` | All roles | Get par level |

### Checks (`/api/v1/checks`)
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/checks/daily` | All roles | Submit daily check with line items |
| GET | `/checks/daily/{id}` | Supervisor, Administrator | Get check detail with line items |
| GET | `/checks/daily/vehicle/{id}` | All roles | List checks for vehicle |
| GET | `/checks/daily/station/{id}/today` | Supervisor, Administrator | Today's compliance status |
| POST | `/checks/controlled-substance` | All roles | Submit CS dual-signature check |
| GET | `/checks/controlled-substance/{id}` | Supervisor, Administrator | Get CS check detail |
| GET | `/checks/controlled-substance/vehicle/{id}` | Supervisor, Administrator | List CS checks for vehicle |

### Audit (`/api/v1/audit`)
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/audit` | Supervisor, Administrator | Query audit events with filters |

---

## 6. Business Rules Enforced

| Rule | Enforcement Layer |
|------|------------------|
| One daily check per vehicle per calendar day | Database unique constraint + 409 response |
| CS checks require ALS vehicle only | Application logic + 422 response |
| CS check requires two different signers | Application logic + 422 response |
| performed_by bound to authenticated identity | Router (JWT claim) — cannot be overridden by request body |
| Line item status computed from Need/Have/Expiry | Application logic — cannot be submitted |
| Overall check status derived from worst line item | Application logic — cannot be submitted |
| EXPIRED status takes priority over MISSING/SHORT | Application logic — explicit precedence |
| Lot must belong to the correct item | Validated before write + 422 response |
| Compartment must belong to correct location | Validated before write + 404 response |
| Station must exist before vehicle creation | FK constraint + 404 response |

---

## 7. Line Item Status Logic

The following status computation is applied per line item at write time:

```
IF lot.expiration_date <= today → EXPIRED
ELSE IF quantity_found == 0 AND quantity_needed > 0 → MISSING
ELSE IF quantity_found < quantity_needed → SHORT
ELSE → OK
```

Overall check status derived from worst line item status:

```
IF any EXPIRED or MISSING → FAIL
ELSE IF any SHORT → NEEDS_RESTOCK
ELSE → PASS
```

---

## 8. Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Web framework | FastAPI | 0.111.0 |
| ORM | SQLAlchemy | 2.0.30 |
| Migrations | Alembic | 1.13.1 |
| Schema validation | Pydantic | 2.7.1 |
| Database | PostgreSQL (Azure Flexible Server) | 16 |
| Python | CPython | 3.11.15 |
| ASGI server | Gunicorn + UvicornWorker | 0.29.0 |
| Test framework | pytest + pytest-asyncio | 8.2.0 |
| Test client | Starlette TestClient | — |

---

## 9. Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| FastAPI application | `app/ems_readykit/` | ✅ Complete |
| 11 SQLAlchemy models | `app/ems_readykit/models/` | ✅ Complete |
| Alembic migrations (0001, 0002) | `app/alembic/versions/` | ✅ Complete |
| Pydantic schemas | `app/ems_readykit/schemas/` | ✅ Complete |
| 6 API routers | `app/ems_readykit/routers/` | ✅ Complete |
| Health check endpoint | `GET /health` | ✅ Complete |
| 74 automated tests | `app/tests/` | ✅ Complete |
| Requirements file | `app/requirements.txt` | ✅ Complete |

---

## 10. Testing

### Test categories

| Category | Count | Description |
|----------|-------|-------------|
| Model tests | 11 | ORM model creation, relationships, constraints |
| Station endpoints | 6 | CRUD + validation |
| Vehicle endpoints | 8 | CRUD + auto-location creation |
| Item endpoints | 6 | CRUD + filters |
| Inventory endpoints | 11 | Locations, lots, par levels |
| Compartment endpoints | 7 | CRUD + sort order + RBAC |
| Check line items | 9 | Status logic, expiration, lot validation |
| Check endpoints | 12 | Daily + CS workflows + audit events |
| Audit endpoints | 5 | Filters, limits |
| Schema validation | 3 | Edge cases |
| RBAC enforcement | 12 | All role combinations |
| **Total** | **74** | 74/74 passing, 1.66s runtime |

### Test isolation
All tests run against an in-memory SQLite database using SQLAlchemy savepoint
transactions. Each test rolls back to a clean state without dropping tables.
No test data persists between tests.

---

## 11. Known Issues and Tradeoffs

| Item | Detail | Resolution |
|------|--------|------------|
| gunicorn resolves from system Python | Oryx compresses build; gunicorn found via antenv activation | Fixed in startup.sh — activate antenv from APP_PATH |
| Windows zip backslash paths | Compress-Archive uses backslashes; Oryx cannot reconstruct directories | Fixed — zip always built on Linux (GitHub Actions or manual Linux rebuild) |
| alembic.ini not in wwwroot | Oryx extracts to APP_PATH (/tmp/...), not wwwroot | Fixed in startup.sh — alembic run from APP_PATH |

---

## 12. Phase Dependencies

| Dependency | Direction |
|------------|-----------|
| Phase 1 | Requires: App Service, PostgreSQL, Key Vault from Phase 1 |
| Phase 3 | Provides: API endpoints for auth integration; requires RBAC from Phase 1 |
| Phase 4 | Phase 4 additions integrated into Phase 2 codebase (compartments, line items) |
| Phase 5 | Provides: all API endpoints consumed by the frontend |

---

## 13. Next Phase

Phase 3 — Authentication and CI/CD: Azure AD JWT authentication, RBAC
enforcement on all endpoints, GitHub Actions CI/CD pipeline.
