# EMS ReadyKit — Phase 4: Compartments, Line Items, and Expiration Tracking
# Document version: 1.0
# Status: Complete
# Last updated: 2026-05-15

---

## 1. Executive Summary

Phase 4 extended the inventory data model to reflect how EMS crews actually
perform daily checks — compartment by compartment, item by item, with explicit
verification of lot numbers and expiration dates. New Compartment and
CheckLineItem models enable the application to capture exactly what the paper
Jan-Care inventory form captures: the physical compartment, the required quantity
(Need), the actual quantity found (Have), and whether the item's lot is expired.
Status computation is fully automated and tamper-resistant. Sixteen new
automated tests validate all new behavior.

---

## 2. Background and Motivation

### The gap identified from the paper form
Review of the Jan-Care inventory sheets revealed that the existing data model
captured the daily check at vehicle level only — a single PASS/FAIL/NEEDS_RESTOCK
for the whole truck. The paper form actually captures:

- Which specific compartment each item lives in (Compartment #1, Drug Bag, First Out Bag, etc.)
- The required quantity per item per compartment (Need column)
- The actual quantity found during the check (Have column)
- The lot number and expiration date for medications and tracked consumables

Without this granularity, the system could not:
- Tell a medic which compartment needs attention
- Record which lot of Epi was checked and whether it was expired
- Provide a supervisor with legally defensible line-item detail

Phase 4 closes this gap.

---

## 3. Objectives

| Objective | Description |
|-----------|-------------|
| Compartment model | Physical storage areas per vehicle, matching the paper form layout |
| Line item tracking | Per-item Need/Have counts per compartment per daily check |
| Expiration verification | Lot-level expiration checked at check time, not just in reporting |
| Automatic status | OK / SHORT / MISSING / EXPIRED computed server-side — never client-supplied |
| Lot integrity | Lot must belong to the correct item — validated before write |
| Test coverage | 16 new tests covering compartments, line items, expiration, and lot validation |

---

## 4. Scope

### In scope
- `Compartment` model and migration
- `CheckLineItem` model and migration with `lot_id` FK
- `EXPIRED` status added to `LineItemStatus` enum
- `lot_number` and `expiration_date` hybrid properties on `CheckLineItem`
- `lot` relationship on `CheckLineItem` with `lazy="selectin"`
- `compartments` relationship on `InventoryLocation`
- `check_line_items` relationship on `DailyInventoryCheck` with `lazy="selectin"`
- `compartment_id` FK on `ParLevel` (compartment-scoped par levels)
- 3 new compartment endpoints on inventory router
- Updated daily check router: accepts line_items, validates lots, computes status
- Updated schemas: `CheckLineItemCreate`, `CheckLineItemRead`, `DailyInventoryCheckCreate`, `DailyInventoryCheckRead`
- Alembic migration 0002
- 16 new automated tests (TestCompartmentEndpoints + TestCheckLineItems)

### Out of scope
- Frontend rendering (Phase 5)
- Supervisor acknowledgement workflow (Phase 6)
- PUT /inventory/lots/{id} expiry correction (Phase 6)

---

## 5. New Data Models

### Compartment
Represents a named physical storage area within a vehicle.

| Field | Type | Description |
|-------|------|-------------|
| compartment_id | Integer PK | System identifier |
| location_id | FK → InventoryLocation | Parent vehicle location |
| name | String(100) | Physical label (e.g. "Compartment #1", "Drug Bag") |
| sort_order | Integer | Display order matching physical truck layout |
| als_only | Boolean | Hidden on BLS trucks (Drug Bag, Narcotic Lock Bag) |
| active | Boolean | Soft delete support |

**Unique constraint:** `(location_id, name)` — one compartment with a given name per location.

**Design decision:** Compartment is a separate model rather than a field on
InventoryLocation, because:
1. The same item can appear in multiple compartments with different par levels
2. Par levels and check line items can be scoped to a specific compartment
3. Compartment templates can be defined once and applied to multiple vehicles

### CheckLineItem
One row on the paper inventory form — one item in one compartment during one check.

| Field | Type | Description |
|-------|------|-------------|
| line_item_id | Integer PK | System identifier |
| check_id | FK → DailyInventoryCheck | Parent check |
| compartment_id | FK → Compartment | Compartment being checked |
| item_id | FK → Item | Item being counted |
| lot_id | FK → StockLot (nullable) | Specific lot inspected (optional) |
| quantity_needed | Integer | Par/Need — expected quantity |
| quantity_found | Integer | Have — actual count found |
| status | Enum | OK / SHORT / MISSING / EXPIRED — computed at write |
| notes | String(300) | Optional free-text note |

**Hybrid properties** on `CheckLineItem`:
- `lot_number` — reads `self.lot.lot_number` (via selectin-loaded relationship)
- `expiration_date` — reads `self.lot.expiration_date`

These are surfaced in `CheckLineItemRead` responses without requiring a second API call.

---

## 6. Status Computation Logic

### Per line item (computed at write time, immutable after)

```
IF lot_id provided AND lot.expiration_date IS NOT NULL AND lot.expiration_date <= today:
    status = EXPIRED       ← expiration takes priority over quantity

ELSE IF quantity_found == 0 AND quantity_needed > 0:
    status = MISSING

ELSE IF quantity_found < quantity_needed:
    status = SHORT

ELSE:
    status = OK
```

### Overall check status (derived from line items)

```
IF any line item is EXPIRED or MISSING → FAIL
ELSE IF any line item is SHORT → NEEDS_RESTOCK
ELSE → PASS (also PASS if no line items submitted — header-only check)
```

### Why EXPIRED takes priority
An expired item is not usable in the field regardless of quantity. A truck
with 10 expired Epi vials is in the same compliance state as a truck with
zero. Setting EXPIRED above MISSING prevents false-positive PASS statuses.

---

## 7. Lot Validation Rules

When a `lot_id` is provided on a line item, the following are validated before
the check is written:

1. The lot exists in the database (404 if not found)
2. The lot's `item_id` matches the line item's `item_id` (422 if mismatch)

If any lot ID in the submission fails validation, the entire check write is
aborted. No partial writes.

---

## 8. Expiry Date Override (UX Note — Phase 5 Implementation)

When the expiration date on a physical package differs from the system record,
a medic can record the discrepancy at check time. This is captured in
`line_item.notes`:

```
"Medic reported lot expiry as 2026-08-01 (system: 2026-06-01)"
```

The system evaluates EXPIRED status against the system date (conservative —
uses earlier date). The supervisor corrects the lot record separately via
a supervisor workflow (Phase 6: PUT /inventory/lots/{id}).

---

## 9. New API Endpoints

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/inventory/locations/{id}/compartments` | Supervisor, Administrator | Create compartment |
| GET | `/inventory/locations/{id}/compartments` | All roles | List compartments (sorted by sort_order) |
| GET | `/inventory/compartments/{id}` | All roles | Get compartment detail |

### Updated endpoints

| Method | Endpoint | Change |
|--------|----------|--------|
| POST | `/checks/daily` | Now accepts `line_items` array; validates lots; computes status |
| GET | `/checks/daily/{id}` | Now returns `line_items` with lot_number and expiration_date |

---

## 10. Database Migration

### Migration 0002 — `compartments_and_line_items`

**New tables:**
- `compartments` — with `(location_id, name)` unique constraint and `ix_compartments_location_id` index
- `check_line_items` — with indexes on `check_id`, `compartment_id`, `status`, `lot_id`

**Modified tables:**
- `par_levels` — added nullable `compartment_id` FK column and `uq_par_item_compartment` unique constraint

**Backward compatibility:** All new columns are nullable. Existing par levels
(without compartment_id) remain valid. The `uq_par_item_location` constraint
on existing (item_id, location_id) pairs is preserved alongside the new
`uq_par_item_compartment` constraint.

---

## 11. Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| Compartment model | `app/ems_readykit/models/compartment.py` | ✅ Complete |
| CheckLineItem model | `app/ems_readykit/models/check_line_item.py` | ✅ Complete |
| Updated StockLot model | `app/ems_readykit/models/stock_lot.py` | ✅ Complete |
| Updated ParLevel model | `app/ems_readykit/models/par_level.py` | ✅ Complete |
| Updated DailyInventoryCheck model | `app/ems_readykit/models/daily_inventory_check.py` | ✅ Complete |
| Updated Item model | `app/ems_readykit/models/item.py` | ✅ Complete |
| Compartment schema | `app/ems_readykit/schemas/compartment.py` | ✅ Complete |
| CheckLineItem schema | `app/ems_readykit/schemas/check_line_item.py` | ✅ Complete |
| Updated check schemas | `app/ems_readykit/schemas/daily_inventory_check.py` | ✅ Complete |
| Updated par level schema | `app/ems_readykit/schemas/par_level.py` | ✅ Complete |
| Updated inventory router | `app/ems_readykit/routers/inventory.py` | ✅ Complete |
| Updated checks router | `app/ems_readykit/routers/checks.py` | ✅ Complete |
| Alembic migration 0002 | `app/alembic/versions/0002_compartments_and_line_items.py` | ✅ Complete |
| New/updated model __init__ | `app/ems_readykit/models/__init__.py` | ✅ Complete |
| New/updated schema __init__ | `app/ems_readykit/schemas/__init__.py` | ✅ Complete |
| 16 new tests | `app/tests/test_routers.py` | ✅ Complete |

---

## 12. Testing

### New test classes

#### TestCompartmentEndpoints (7 tests)
| Test | Validates |
|------|-----------|
| Create compartment returns 201 | Basic creation |
| Duplicate compartment returns 409 | Unique constraint |
| List sorted by sort_order | Physical layout ordering |
| Get compartment by ID | Read endpoint |
| Get compartment not found returns 404 | Error handling |
| Responder can list compartments | RBAC read access |
| Responder cannot create compartment returns 403 | RBAC write restriction |

#### TestCheckLineItems (9 tests)
| Test | Validates |
|------|-----------|
| Daily check with line items returns 201 + PASS | Basic line item submission |
| Short item sets NEEDS_RESTOCK | Status computation |
| Missing item sets FAIL | Status computation |
| No line items defaults to PASS | Backward compatibility |
| Invalid compartment ID returns 404 | Validation |
| Expired lot sets EXPIRED + FAIL | Expiration logic |
| Valid lot passes expiration check + lot fields in response | Lot field denormalization |
| Wrong lot/item combination returns 422 | Lot integrity |
| Mixed statuses: worst case wins | Priority ordering |

Total test suite: 90/90 passing.

---

## 13. Known Issues and Tradeoffs

| Item | Detail | Resolution |
|------|--------|------------|
| Lot not required for non-medication items | Gloves, tape, dressings do not need lot tracking | lot_id is optional — medics only provide it for items with tracked lots |
| Line items optional at submission | A check can be submitted without line items | Intentional backward compatibility — header-only checks are valid |
| Expiry override does not update lot record | Medic observation stored in notes, not in database | Supervisor corrects via Phase 6 endpoint |

---

## 14. Phase Dependencies

| Dependency | Direction |
|------------|-----------|
| Phase 2 | Requires: All base models and API infrastructure |
| Phase 3 | Requires: Authentication and RBAC on all new endpoints |
| Phase 5 | Provides: Compartment and line item endpoints for the check wizard |
| Phase 6 | Provides: PUT /inventory/lots/{id} for supervisor expiry correction |

---

## 15. Next Phase

Phase 5 — Frontend PWA: Progressive Web App implementing the daily check
wizard, supervisor dashboard, item management, vehicle status reporting,
and help center.
