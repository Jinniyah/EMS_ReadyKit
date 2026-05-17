# EMS ReadyKit — Session Handoff Document
# Date: 2026-05-15
# Status: Active development — pick up here next session

---

## Where we left off — CRITICAL: finish this first

The seed script failed because Alembic migrations 0002 and 0003 used
`op.create_unique_constraint` and `op.add_column` with FKs directly on
existing tables — SQLite does not support this syntax. Both migrations
have been rewritten to use Alembic batch mode (copy-and-move strategy).

### Immediate next steps (do these first, in order)

```powershell
cd C:\Users\jinni\source\repos\EMS_ReadyKit\app
.venv\Scripts\Activate.ps1

# 1. Delete the old dev database (data will be reseeded)
Remove-Item ems_readykit_dev.db

# 2. Rebuild from scratch — runs all 3 migrations
alembic upgrade head

# 3. Verify — must show exactly:
#    0003_item_check_types_and_equipment (head)
alembic current

# 4. Run the seed
python seed.py

# 5. Run the tests — should still be 90/90
pytest tests/ -v --tb=short

# 6. Commit and push
cd C:\Users\jinni\source\repos\EMS_ReadyKit
git add .
git commit -m "fix: migrations 0002 and 0003 use batch mode for SQLite ALTER TABLE compatibility; seed data for Ambulance 712"
git push origin main
```

05/15/2026 1:25 PM.  I ran the above commands successfully.

Here's selective output from the above commands:
```2026-05-15 13:23:36,783 INFO sqlalchemy.engine.Engine [generated in 0.00021s] (2, 3)

  ✓ Seed complete.
    Items in catalog:      238
    Compartments seeded:   42 (712 truck + jump bag)
    Par levels created:    238

  Vehicle 712 location ID:  2
  Jump Bag location ID:      3

  -------
  ================================================== warnings summary ===================================================
.venv\Lib\site-packages\starlette\formparsers.py:12
  C:\Users\jinni\source\repos\EMS_ReadyKit\app\.venv\Lib\site-packages\starlette\formparsers.py:12: PendingDeprecationWarning: Please use `import python_multipart` instead.
    import multipart

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================================ 90 passed, 1 warning in 1.68s ============================================

git push origin main
Enumerating objects: 20, done.
Counting objects: 100% (20/20), done.
Delta compression using up to 20 threads
Compressing objects: 100% (11/11), done.
Writing objects: 100% (11/11), 16.76 KiB | 5.59 MiB/s, done.
Total 11 (delta 8), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (8/8), completed with 8 local objects.
To https://github.com/Jinniyah/EMS_ReadyKit.git
   1044067..2eaf5ae  main -> main

 ```
 The github CI/CD pipeline provided the following failure:
 ```
    1m 8s
    Run echo "Waiting 30s for app to start..."
    Waiting 30s for app to start...
    Health check status: 503
    Health check failed with status 503
    Error: Process completed with exit code 1.
```



---

## What was built today (2026-05-15)

### 1. Migration 0003 — new item check types
File: `app/alembic/versions/0003_item_check_types_and_equipment.py`

Added to items table:
- `check_type` VARCHAR(20) default SUPPLY
- `measurement_minimum` FLOAT nullable
- `measurement_maximum` FLOAT nullable
- `recurrence_days` INTEGER nullable

Added to check_line_items table:
- `measurement_value` FLOAT nullable  (O2 PSI readings)
- `functional_pass` BOOLEAN nullable  (battery OK, runs & starts)
- `date_value` DATE nullable          (AED last charge date)

Added to compartments table:
- `location_descriptor` VARCHAR(150) nullable
- `parent_compartment_id` INTEGER nullable FK → compartments
- `restriction_note` VARCHAR(100) nullable

### 2. Updated models
- `models/item.py` — added ItemCheckType enum (SUPPLY/MEASUREMENT/FUNCTIONAL/DATE_RECORD/DOCUMENT)
  and new fields
- `models/check_line_item.py` — added measurement_value, functional_pass, date_value fields
  and new LineItemStatus values (LOW, FAIL, OVERDUE)
- `models/compartment.py` — added location_descriptor, parent_compartment_id, restriction_note
- `models/inventory_location.py` — added JUMP_BAG and EQUIPMENT to LocationType enum
- `models/__init__.py` — exports ItemCheckType

### 3. Updated schemas
- `schemas/item.py` — added check_type, measurement_minimum, measurement_maximum, recurrence_days
- `schemas/check_line_item.py` — added measurement_value, functional_pass, date_value
- `schemas/compartment.py` — added location_descriptor, parent_compartment_id, restriction_note
- `schemas/inventory_location.py` — added InventoryLocationCreate schema for Jump Bag creation

### 4. Updated routers
- `routers/items.py` — passes all new fields to ORM
- `routers/inventory.py` — passes new compartment fields to ORM; added POST /inventory/locations
  endpoint for creating JUMP_BAG and EQUIPMENT locations
- `routers/checks.py` — now queries Item to get check_type before computing status;
  passes measurement_value, functional_pass, date_value to CheckLineItem;
  _compute_line_item_status now routes by check_type;
  _compute_check_status handles LOW (NEEDS_RESTOCK) and FAIL/OVERDUE (FAIL)

### 5. Status computation logic (checks.py)
MEASUREMENT: LOW if value < measurement_minimum, else OK
FUNCTIONAL:  FAIL if functional_pass=False, OK if True, MISSING if None
DATE_RECORD: OVERDUE if (today - date_value).days > recurrence_days, else OK
SUPPLY:      EXPIRED > MISSING > SHORT > OK (unchanged)
DOCUMENT:    MISSING if found=0, OK if found>=1

Overall check status:
  FAIL         = any EXPIRED, MISSING, FAIL, OVERDUE
  NEEDS_RESTOCK = any SHORT, LOW
  PASS         = all OK

### 6. Seed script
File: `app/seed.py`

Creates from real Ambulance 712 inventory forms:
- Station: Newberg Township Station 1
- Vehicle: Unit 712 (ALS)
- Supply room location
- Jump Bag location (shared 710/712)
- ~38 compartments including exterior ECs, Truck Operations, Under Hood
- ~140 items including:
  - AED (4 items: battery FUNCTIONAL, charge date DATE_RECORD, adult pads SUPPLY, peds pads SUPPLY)
  - O2 tanks (MEASUREMENT, minimum 500 PSI, maximum 2200 PSI)
  - LUCAS device (presence SUPPLY + charge date DATE_RECORD, recurrence 30 days)
  - Truck Operations (all FUNCTIONAL — runs & starts, lights, sirens, etc.)
  - Under Hood (FUNCTIONAL, restriction_note="Approved personnel only")
  - All medications with controlled_substance flags
  - Jump Bag sub-compartments with parent_compartment_id links
- ~150 par levels

### 7. Documentation completed today
- `README.md` — fully rewritten, professional, portfolio-quality
- `CONTRIBUTING.md` — full local setup, test commands, migration guide, how to add endpoints
- `docs/adr/ADR-005-Frontend-Architecture.md` — 8 major frontend decisions with rationale
- `docs/adr/ADR-003-Logging-and-Audit.md` — updated with correlation ID and request logging notes
- `core/logging.py` — rewritten with _EmsJsonFormatter, correlation ID, request_id ContextVar
- `main.py` — added request logging middleware (method, path, status, duration, request_id)
- `docs/session_handoff_2026-05-15.md` — this file

---

## Complete current state of the project

### What is live (deployed to Azure)
- Azure infrastructure (Phase 1) — North Central US, F1 tier
- FastAPI backend (Phase 2-4) — https://app-ems-readykit-dev.azurewebsites.net
- Azure AD authentication (Phase 3) — RS256 JWT, 3 app roles
- GitHub Actions CI/CD (Phase 3)
- Compartments + line items + expiration (Phase 4)

### What is coded but not yet deployed
- Migration 0003 (new item check types)
- Updated models, schemas, routers
- Seed script
- New logging middleware

### Test suite
- 90/90 tests passing
- All existing tests still pass after all model/schema/router changes
- New tests needed: see "Tests to write" section below

---

## Key architectural decisions made from real inventory forms

### Four item check types discovered from Ambulance 712 forms
The paper forms revealed that not everything is a counted item:

| Check type   | Example items                    | Fields used                |
|--------------|----------------------------------|----------------------------|
| SUPPLY       | Kerlix, Gauze, Medications       | quantity_needed/found, lot |
| MEASUREMENT  | O2 PSI (all 4 tanks on truck)    | measurement_value          |
| FUNCTIONAL   | Battery OK, Runs & Starts        | functional_pass            |
| DATE_RECORD  | AED last charge, LUCAS charge    | date_value                 |
| DOCUMENT     | PCR forms, Protocol book         | quantity 0/1               |

### AED modeled as 4 separate items in PC 8
- "AED Battery"              check_type=FUNCTIONAL   → Battery OK yes/no
- "AED Date of Last Charge"  check_type=DATE_RECORD  → recurrence_days=90
- "AED Pads Adult"           check_type=SUPPLY       → quantity + expiry date
- "AED Pads Pediatric"       check_type=SUPPLY       → quantity + expiry date

### O2 tanks modeled as 2 items per location
- "On-Board O2 Tank w/ Regulator 15LPM"  SUPPLY → presence check
- "On-Board O2 PSI"                       MEASUREMENT → measurement_minimum=500.0

Same pattern for: Stretcher O2, Jump Bag O2

### Jump Bag is a JUMP_BAG location type (not VEHICLE)
Shared between trucks 710 and 712. Has its own compartment structure.
Sub-compartments use parent_compartment_id linking.

### Truck Operations section = all FUNCTIONAL items
"Runs and Starts", "Lights & Sirens", "Climate Control", etc.

### Under Hood = restricted compartment
restriction_note="Approved personnel only — mechanical authorization required"

---

## What needs to happen next (in order)

### Immediate (next session start)
1. Run the migration fix commands above
2. Run seed.py successfully
3. Verify 90/90 tests still pass
4. Commit and push

### Tests to write (TestCheckTypes class)
Add to app/tests/test_routers.py:

```python
class TestCheckTypes:
    # MEASUREMENT items
    def test_o2_psi_above_minimum_returns_ok
    def test_o2_psi_below_minimum_returns_low
    def test_o2_psi_below_minimum_sets_check_needs_restock
    def test_measurement_missing_value_returns_missing

    # FUNCTIONAL items
    def test_battery_ok_true_returns_ok
    def test_battery_ok_false_returns_fail
    def test_functional_fail_sets_check_fail
    def test_functional_missing_value_returns_missing

    # DATE_RECORD items
    def test_recent_charge_date_returns_ok
    def test_overdue_charge_date_returns_overdue
    def test_overdue_sets_check_fail
    def test_date_record_missing_value_returns_missing

    # DOCUMENT items
    def test_document_present_returns_ok
    def test_document_missing_returns_missing

    # Jump Bag location
    def test_create_jump_bag_location_returns_201
    def test_cannot_create_vehicle_location_via_api_returns_422
```

### Phase 5 Frontend (after seed is verified)
See docs/phase5_frontend_pwa.md for complete plan.

Build order:
5A — Foundation: useAuth, ErrorBoundary, statusCalc, useDraft, UserPill
5B — Check wizard: Steps 1-4, submitted screen, draft save/resume
5C — Help system: tutorial, FAQ, contextual help
5D — Item management module
5E — Vehicle status + repair requests
5F — Supervisor dashboard (needs Phase 6 endpoints)
5G — Feedback, user management, data export, supply room
5H — Infrastructure: Azure Static Web Apps Terraform module, CI/CD

### Phase 6 Backend (run in parallel with Phase 5 as needed)
Priority endpoints:
1. PATCH /api/v1/vehicles/{id}                    — active/inactive
2. PATCH /api/v1/checks/daily/{id}/acknowledge    — FAIL check corrective action
3. GET /api/v1/checks/daily/station/{id}?from=&to= — compliance calendar
4. POST /api/v1/vehicles/{id}/repair-requests      — repair request
5. POST /api/v1/inventory/transfer                 — supply room restock
6. GET /api/v1/inventory/locations/{id}/stock-summary — supply room view
7. GET /api/v1/stations/{id}/users                 — second crew picker
8. PUT /api/v1/inventory/lots/{id}                 — correct expiry date
9. PATCH /api/v1/inventory/par-levels/{id}         — deactivate par level
10. POST /api/v1/feedback
11. GET/PATCH /api/v1/notifications
12. POST /api/v1/admin/user-requests
13. GET /api/v1/audit?from=&to= (date filter)
14. GET /api/v1/vehicles/{id}/repair-requests

New models needed for Phase 6:
- RepairRequest
- Notification
- FeedbackEntry
- UserRequest
- Vehicle.active, inactive_reason, inactive_since
- ParLevel.active, deactivated_at, deactivation_reason
- DailyInventoryCheck.reviewed_by, reviewed_at, corrective_action
- DailyInventoryCheck.started_by (for handoff flow)

Migration 0004 covers all of the above.

### ADR still needed
ADR-005-Frontend-Architecture.md — WRITTEN today, already committed

### CONTRIBUTING.md — WRITTEN today, already committed

---

## File locations — everything important

```
C:\Users\jinni\source\repos\EMS_ReadyKit\
├── app/
│   ├── ems_readykit/
│   │   ├── core/
│   │   │   ├── auth.py          ✅ JWT validation, fake tokens, CurrentUser
│   │   │   ├── config.py        ✅ Settings, DB URL, Azure AD config
│   │   │   ├── database.py      ✅ SQLAlchemy engine, SessionLocal
│   │   │   └── logging.py       ✅ JSON formatter, correlation ID, request_id
│   │   ├── models/
│   │   │   ├── __init__.py      ✅ exports all models including ItemCheckType
│   │   │   ├── item.py          ✅ ItemCheckType enum + new fields
│   │   │   ├── check_line_item.py ✅ measurement/functional/date fields
│   │   │   ├── compartment.py   ✅ location_descriptor, parent, restriction_note
│   │   │   └── inventory_location.py ✅ JUMP_BAG, EQUIPMENT location types
│   │   ├── schemas/
│   │   │   ├── item.py          ✅ check_type and measurement fields
│   │   │   ├── check_line_item.py ✅ all 3 new field types
│   │   │   ├── compartment.py   ✅ all new fields
│   │   │   └── inventory_location.py ✅ InventoryLocationCreate added
│   │   ├── routers/
│   │   │   ├── checks.py        ✅ routes by check_type, new status values
│   │   │   ├── items.py         ✅ passes new fields to ORM
│   │   │   └── inventory.py     ✅ new compartment fields + POST /locations
│   │   └── main.py              ✅ request logging middleware + correlation ID
│   ├── alembic/versions/
│   │   ├── 0001_initial_schema.py          ✅
│   │   ├── 0002_compartments_and_line_items.py ✅ FIXED batch mode
│   │   └── 0003_item_check_types_and_equipment.py ✅ FIXED batch mode
│   ├── tests/
│   │   ├── conftest.py          ✅ fixtures, auth headers
│   │   ├── test_models.py       ✅ 11 model tests
│   │   └── test_routers.py      ✅ 79 router tests (90 total)
│   └── seed.py                  ✅ Ambulance 712 full seed
├── docs/
│   ├── project_index.md         ✅ master index, current state, backlog
│   ├── phase1_platform_foundation.md ✅
│   ├── phase2_backend_api.md    ✅
│   ├── phase3_auth_cicd.md      ✅
│   ├── phase4_compartments_line_items.md ✅
│   ├── phase5_frontend_pwa.md   ✅ complete with all UX decisions
│   ├── phase6_backend_extensions.md ✅
│   ├── help_content.md          ✅ tutorial, FAQ, contextual help content
│   ├── adr/
│   │   ├── ADR-001-Architecture.md          ✅
│   │   ├── ADR-002-RBAC.md                  ✅
│   │   ├── ADR-003-Logging-and-Audit.md     ✅ updated today
│   │   ├── ADR-004-Terraform-Module-Structure.md ✅
│   │   └── ADR-005-Frontend-Architecture.md ✅ WRITTEN TODAY
│   └── models/
│       ├── Ambulance 712 Page 1 Inventory.jpg
│       ├── Ambulance 712 Page 2 Inventory.jpg
│       └── Ambulance Jump Bag.jpg
├── iac/Terraform/               ✅ all 8 modules complete
├── .github/workflows/deploy.yml ✅ CI/CD pipeline
├── README.md                    ✅ REWRITTEN TODAY — professional
└── CONTRIBUTING.md              ✅ WRITTEN TODAY
```

---

## Things discovered from the real Ambulance 712 inventory forms

1. Form has "Inspectors:" (plural) — dual crew is the norm, make it required
2. * = item has expiration date — maps exactly to our lot_id model
3. BLS Drug Bag is separate from ALS drugs — als_only flag is validated
4. PC 1-18 are interior, EC 1-3 are exterior bays (driver and passenger side)
5. Jump Bag shared between 710 and 712 — JUMP_BAG location type needed
6. AED has 4 check types on one piece of equipment
7. O2 tanks need PSI readings (MEASUREMENT), not just presence
8. LUCAS device needs last charge date (DATE_RECORD, recurrence 30 days)
9. AED needs last charge date (DATE_RECORD, recurrence 90 days)
10. "Truck Operations" section is all FUNCTIONAL checks
11. "Under Hood" is restricted to approved personnel only
12. Glucometer Kit appears on 3 separate forms — normalize item names
13. Some items embed quantities in names (x3, x4) — extract to par levels
14. Colorimetric CO2 detector expires (reagent-based) — needs * flag
15. Paperwork items (PCR, billing forms) = DOCUMENT check type
16. Battery Charged? on stretcher = FUNCTIONAL check type

---

## Prompt for next Claude session

Copy and paste this exactly to start the next conversation:

---

I am continuing development of EMS ReadyKit, a cloud-native inventory and 
vehicle readiness platform for EMS operations. The codebase is at:
C:\Users\jinni\source\repos\EMS_ReadyKit

We had a very productive session yesterday. There is a handoff document at:
C:\Users\jinni\source\repos\EMS_ReadyKit\docs\session_handoff_2026-05-15.md

Please read that document first. Then read the project index at:
C:\Users\jinni\source\repos\EMS_ReadyKit\docs\project_index.md

The most urgent task is fixing a migration issue and getting the seed script 
to run successfully. The handoff document has the exact commands to run first.

Key context:
- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL (SQLite for dev)
- Auth: Azure AD JWT RS256, three roles (Administrator/Supervisor/Responder)  
- CI/CD: GitHub Actions → Azure App Service
- 90/90 tests passing before the migration fix
- Seed data is based on REAL Ambulance 712 inventory forms
- We discovered 4 item check types from the real forms:
  SUPPLY (counted), MEASUREMENT (O2 PSI), FUNCTIONAL (battery OK), 
  DATE_RECORD (AED last charge date), DOCUMENT (paperwork)
- Migrations 0002 and 0003 were fixed to use Alembic batch mode for SQLite

After fixing the migrations and seed, the next priority is:
1. Write TestCheckTypes tests for the new check types
2. Start Phase 5 frontend (React PWA) — Phase 5A foundation first
3. Run Phase 6 backend extensions in parallel as the frontend needs them

The live API is at: https://app-ems-readykit-dev.azurewebsites.net
GitHub: https://github.com/Jinniyah/EMS_ReadyKit

Please start by reading the handoff document and project index, then confirm
what you see as the current state before we begin.
