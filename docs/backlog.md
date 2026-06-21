# EMS ReadyKit — Active Backlog
# v3.03 | Updated: 2026-06-20 | Session AI closed: ITM-4 done (seed.py rewritten with
# BASE_ITEM_SEED, station_id on all items, Newberg full par levels, Marcellus/Training/Test
# catalog only; 32 seed_integrity failures resolved — 484/484 expected after reseed).
# Version-history footer (v1.95-v2.07) moved to backlog_completed.md
# to keep this file small — see that file's "Changelog Archive" section for history.
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AH complete — see backlog_completed.md

---

## LAUNCH GATE
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## All prior gate criteria met as of Session AF (full list in backlog_completed.md's
## Changelog Archive). Gate reopened 2026-06-20 — launch is blocked on ITM-1..8 below.
##
## 📋 Item catalog must be station-scoped (no cross-station bleed-through), items must
##   be assignable to jump bags and the station supply room (not just vehicles), and
##   the Newberg seed must be rebuilt from the real 712/jump bag inventory forms with
##   one canonical item per real-world thing. Jennifer decided to delay launch rather
##   than ship the current global, bleed-through catalog.

---

## PRE-LAUNCH — ITM-1..8 (station-scoped items + deduplicated seed)

### Why
Items are global today (`Item.name` is globally unique, no `station_id` on the
model) — every station's supervisors see and can rename/retire every other
station's items. The Item Catalog also can't assign items to jump bags or the
station supply room, only vehicles, even though the backend already supports any
`location_id` (confirmed by reading `admin_items.py::assign_item_to_compartment` —
no backend blocker there). Separately, today's seed works around the old global-
uniqueness constraint by suffixing item names per location (`Gauze 3x3 PC18`,
`Gauze 3x3 JB`, `Stethoscope PC18`, `Stethoscope JB`...) — the same real-world item
becomes multiple unrelated catalog rows, fragmenting par levels and usage tracking.

No production data exists (confirmed by Jennifer 2026-06-20) — the dev DB will be
wiped and reseeded rather than migrated, which removes the original plan's highest-
risk step (a live data split-and-repoint migration).

### ITM-1 — Migration: `station_id` on `items`, per-station uniqueness
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | ✅ Complete — Session AG (2026-06-20) |
| Notes | Migration 0028 applied. `items.station_id` FK (NOT NULL → stations); `UniqueConstraint("station_id", "name", name="uq_items_station_name")` replaces global `uq_items_name`. Supply catalog endpoint scoped to station. Test suite updated throughout (30+ call sites + 2 supply room test fixes). 452 tests passing; 32 test_seed_integrity failures are expected until ITM-4 rewrites seed.py. |

### ITM-2 — Base item seed: deduplicated across locations, 6 cabinets — FINAL, locked 2026-06-20
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | ✅ Merge table finalized and signed off by Jennifer — ready for ITM-4 to consume |
| Source | `docs/models/Ambulance 712 Page 1/2 Inventory.jpg`, `docs/models/Ambulance Jump Bag.jpg` — not the current `seed.py` names. |
| Rule | Merge across **locations** (ambulance vs. jump bag vs. supply room), never across **sizes** (3x3 vs 4x4 vs 5x9 stay distinct; Glove/Kerlix sizes stay distinct). |

**Cabinets (`category_group`):** Airway & Respiratory · Wound Care & Trauma Supplies ·
PPE & Cleaning · Diagnostic & Monitoring Equipment · Medications & Controlled
Substances · Documents, Linens & Patient Comfort — plus an uncategorized **Vehicle
Operations** bucket for FUNCTIONAL/DOCUMENT vehicle checks (Truck Operations, Under
Hood) that aren't physical stock and don't belong in a cabinet.

**O2 PSI thresholds (corrected from today's blanket 500/2200 for all three):**
| Item | min | max |
|---|---|---|
| On-Board O2 PSI | 500 | 2200 — unchanged, large tank |
| Stretcher O2 PSI | 200 | 500 — changed, small tank |
| Jump Bag O2 PSI | 200 | 500 — changed, small tank |

`priority_question` text for Stretcher/Jump Bag O2 updates to match ("...above 200
PSI?" instead of "...above 500 PSI?").

**Merged items (old name(s) → canonical name), by cabinet:**

*Airway & Respiratory:* Adult BVM (+ BVM Adult JB) · Combi-Tube 37F & 41F (+ Combi-Tube
JB) · Thomas Tube Holders (+ JB) · Adult NAS (+ NAS Adult JB) · Adult NRB (+ NRB Adult
JB) · OPAs/NPAs (+ JB) · SPo2 Monitor (Bench + JB).

*Wound Care & Trauma Supplies:* Gauze, 3x3 (Gauze 3x3 PC18 + Gauze 3x3 JB + Gauze Pads
3x3 JB — all three, confirmed same item) · CAT Tourniquet (+ Tourniquet JB, canonical
name confirmed) · ABD Pad 5x9 (+ JB) · Tape Various Sizes (+ JB) · Triangle Bandage (+
JB) · ACE Wrap Various Sizes (+ JB) · Occlusive Dressing (+ JB) · Bite Stick (+ JB) ·
**Traction Splint** (Traction Splint PS + Passenger Side EC2 listing — merged, stays
distinct from Adult/Pediatric Traction Splint) · **C-Collar, Adult** (C-Collars PC7 +
C-Collar Adult JB + C-Collars Adult PS — the collar itself) · **C-Collar Bag** (kept
separate — confirmed different item, the carrying bag) · Mega-Movers (PC14 + DS3) ·
Emesis Container (+ JB).

*PPE & Cleaning:* **Gloves, Small/Medium/Large** (merges Glove Boxes Small/Medium/Large
+ Cab Gloves Small/Medium/Large — same glove, now stocked in 3 locations: PC5, Truck
Ops cab, Glove Compartment) · Gloves, X-Large (unchanged, no cab equivalent on form) ·
Antimicrobial Hand Wipes (+ PC5) · Infection Control Kit (+ PC5 + PC14) · BioHazard
Bags (+ JB).

*Diagnostic & Monitoring Equipment:* **Stethoscope** (Stethoscope + PC18 + JB + Flap
JB — all four, confirmed same item) · **Thermometer** (PC18 Unit + JB + EP — confirmed
same item) · Glucometer Lancets (+ JB + Restock Lancets) · Glucometer Test Strips (+
JB) · **Alcohol Prep Pads** (PC18 + JB + Alcohol Preps BLS + Restock — confirmed same
item, used everywhere) · Bandaids (PC18 + JB + Restock) · Oral Glucose Tablets (+ Oral
Glucose) · **Trauma Shears** (plain + PC18 + JB — confirmed same item) · **LUCAS
Device** (merges LUCAS Device + LUCAS Device Ready Check into one FUNCTIONAL priority
item) · **LUCAS Date of Last Charge** (unchanged, DATE_RECORD, stays separate from
LUCAS Device) · **Stretcher Battery Date of Last Charge** (NEW item, DATE_RECORD —
companion to existing Stretcher Battery Charged FUNCTIONAL item, mirrors the AED/LUCAS
ready-check + compliance-date pattern).

*Medications & Controlled Substances:* Syringes (Syringes BLS + Extra Syringes) ·
**Overdose Rescue Kit (NARCAN) and Intranasal Naloxone confirmed as two separate
items** (kit vs. the medication itself — not merged).

*Documents, Linens & Patient Comfort:* Clipboard w/ Paperwork (ambulance Admin Counter
+ JB) · Blankets (+ Extra Blankets) · **Towels** (PC11 + PC14 — confirmed same item) ·
Empty Sharps Container (Bench + JB) · Writing Utensils (+ JB) · Water Bottle (+ Water
Bottles) · **Fire Extinguisher** (merges the Passenger Side EC2 physical item + the
Truck Operations "Fire Extinguisher UL Listed" FUNCTIONAL check into one item;
check_type set to **SUPPLY** — confirmed by Jennifer; Truck Operations compartment
loses this as a separate FUNCTIONAL line item as a result).

**Output:** `BASE_ITEM_SEED` — station-agnostic list:
`(name, category, category_group, check_type, unit_of_measure, measurement_minimum,
measurement_maximum, recurrence_days, controlled_substance)`. No location or quantity
baked in — that's ITM-4.

### ITM-3 — `category_group` field on Item (the 6 cabinets)
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | ✅ Complete — Session AH (2026-06-20) |
| Notes | Migration 0029 applied. `Item.category_group` VARCHAR(100) nullable added. Schema updated (`ItemBase.category_group Optional[str]`). Values populated by seed.py in ITM-4. |

### ITM-4 — Rewrite `seed.py`
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | ✅ Complete — Session AI (2026-06-20) |
| Notes | `seed.py` fully rewritten: `BASE_ITEM_SEED` list (~100+ canonical items across 7 category_groups), `get_or_create_item(db, *, station_id, ...)` now required, `seed_station_catalog(db, station_id)` bootstraps any station's catalog, `build_supply_room(db, loc, station_id)` updated, `build_ambulance_inventory`/`build_jump_bag` use canonical names + corrected O2 PSI thresholds (Stretcher/JB 200–500, On-Board 500–2200), LUCAS Device Ready Check merged into LUCAS Device, Fire Extinguisher → SUPPLY, Stretcher Battery Date of Last Charge NEW item. Newberg gets full par levels; Marcellus, Training, Test get catalog only. `test_seed_integrity.py` updated: 6 test changes (LUCAS merge, O2 PSI thresholds, functional item count). Module docstring updated — "SHARED" line removed. |

### ITM-5 — Backend: scope item endpoints to station
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | 📋 Not started — depends on ITM-1, ITM-4 |
| Notes | `GET/POST /admin/items`, search, CSV import/template (`admin_items.py`) need `station_id` (same pattern as `require_station_membership` elsewhere). `_conflict_on_name` becomes per-station. Barcode stays globally unique (a physical barcode is still one product) — confirmed assumption. |

### ITM-6 — Frontend: station-scoped Item Catalog + assign to jump bag/supply room
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | 📋 Not started — depends on ITM-5 |
| Notes | `ItemCatalog.jsx` / `adminApi.listItems` pass `station_id` — no cross-station bleed-through. `ItemAssignments.jsx`'s `AddAssignmentForm`/`EditRow` currently hardcode a vehicle-only `<select>` — replace with a "Where" picker spanning vehicles + jump bags + station supply room (backend already accepts `location_id` for any location type — no backend change needed for this part). Catalog UI groups/filters by `category_group` cabinets (ITM-3), alongside or replacing today's Medication/Consumable/Equipment/Document chips — decide exact UI in-session. |

### ITM-7 — Fast-follow: multi-location assign-from-item
| Field | Value |
|---|---|
| Priority | Medium (not launch-blocking) |
| Status | 📋 Not started |
| Notes | Once ITM-6's "Where" picker ships, consider letting one item be assigned to several locations in one pass instead of repeating the 3-step flow per location. Confirm the ideal flow after first real use of ITM-6 rather than guessing now. |

### ITM-8 — Tests + docs
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | 📋 Not started — depends on ITM-1..6 |
| Notes | New `test_item_station_scoping.py`: per-station name uniqueness, cross-station invisibility, base-seed bootstrap for a brand-new station (catalog + cabinets, no par levels), Newberg's full real par levels still correct after rewrite. Update `CODEBASE_INDEX.md` (Item model section, migration table, new architectural decision row), `seed.py` module docstring, and this file's launch-gate checklist on close. |

### Sequencing
ITM-1 (✅ done) → ITM-2 (✅ done) → ITM-3 (✅ done) → ITM-4 (✅ done) → ITM-5 → ITM-6 → ITM-8. ITM-7 is a fast-follow
after ITM-6 ships, not launch-blocking.

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter physical stock count for Unit 712 | ⛔ Blocked on ITM-4 reseed — counts must be entered against the rebuilt, deduplicated catalog. |
| LAUNCH-OPS3 | Enter stock count for Unit 712 Jump Bag | ⛔ Same block as LAUNCH-OPS2. |
| LAUNCH-OPS4 | Add all EMS team members | Use Station Administration → Members → Import CSV. |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | 🔄 In progress — surfaced ITM-1..8 among other findings. |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | |

### Post-launch engineering
| # | Item | Pri | Notes |
|---|------|-----|-------|
| F-5G3 | CSV data export | Medium | One download button each in: Check History (supervisor view), Audit Log, Repair Requests. Same streaming CSV pattern as the receive-stock template. |
| ADMIN-F10 | Member list search/filter | Low | Search box in `MemberManagementSection` (`modules/admin/`) filtering by name or email. Client-side, no new backend endpoint. |
| TEST-AE1 | Test coverage for MembersScreen / MemberManagementSection | Medium | Multi-role grouping/display, CSV import happy path + errors, name edit, member_id-based role removal, Supervisor-vs-Admin role-gating. |
| TEST-AF1 | Test coverage for the rewritten ComplianceCalendar.jsx | Medium | Jump bags in month view, Station Supplies Count reminder strip, EntityPicker, getLocationCheckHistory data source. Pair with TEST-AE1. |
| AI-F2 | Barcode search in After-Call Reset | Medium | Deferred by decision. |
| AI-F3 | Barcode search in supply room receive | Medium | Deferred by decision. |
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | Medium | Build based on questions team actually asks after first month. |
| F-UX10 | Scroll-to-card on return from compartment item list | Low | |
| F-UX5 | Check handoff support | Medium | ⛔ Requires B-M8 (started_by field). |
| F-UX9 | Two-state submit with offline queue | Low | IndexedDB queue retries on reconnect. |
| I-1 | Azure Firewall | Medium | Before scaling to second service. |
| I-2 | Re-add route table | Medium | ⛔ |
| TECH-2 | React Query for frontend data management | Low | Post-launch refactor. |
| TECH-3 | Offline submission queue | Low | |

---

## Summary
| Area | Count |
|------|-------|
| Pre-launch ITM-1..8 | 8 (4 ✅ done — ITM-1, ITM-2, ITM-3, ITM-4; 1 fast-follow, not blocking) |
| Post-launch operational | 6 (1 🔄 in progress, 2 ⛔ blocked on ITM-4) |
| Post-launch engineering | 14 (2 ⛔) |
| **Total remaining** | **28** |
