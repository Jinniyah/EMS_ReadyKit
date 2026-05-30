# EMS ReadyKit — Active Backlog
# v1.39 | Updated: 2026-05-30
# Completed items → backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ SESSION COMPLETE 2026-05-24 — Phase 5H Infrastructure
# ✅ SESSION COMPLETE 2026-05-25 — Draft flow, UTC fix, Azure AD, station membership endpoints
# ✅ SESSION COMPLETE 2026-05-26 — Session A: Security Gate (OWASP A02/A04/A05/A06/A09, 0 CVEs)
# ✅ SESSION COMPLETE 2026-05-27 — Session B: Refactor Sprint (REF-1 through REF-7)
# ✅ SESSION COMPLETE 2026-05-29 — Session C: Access Control Enforcement (OWASP A01)
#   - ACC-B7: Station membership enforced on all /checks endpoints
#   - ACC-B8: Station membership enforced on all /vehicles and /inventory endpoints
#   - ACC-B9: Supervisor dashboard covered via ACC-B7/B8 (no separate router)
#   - Human-readable 403 error messages throughout backend and frontend
#   - 26 new membership enforcement tests; 179 total passing, 0 warnings
#   - 4 pre-existing tests fixed with _add_member() fixture helper
#
# ✅ SESSION COMPLETE 2026-05-29 — Session D (in progress):
#   B-R1/B-R2/F-R1: Repair request workflow bugs fixed; In Progress modal split from Resolve
#   B-E3: Date-range compliance endpoint; frontend wired; today-only stub removed
#   VE-F5: Open issue badge on V&E Status card; vehicle card badge on mount
#   F-UX35: Already implemented in previous session (confirmed in code review)
#   CH-UX1: Unified check resolution — ResolutionTag shared component, CheckDetail
#           parity with CheckDetailPanel (I Fixed This, resolution states), CheckList
#           rows upgraded from plain ✓ to ResolutionTag
#   Session D COMPLETE
#
# ✅ SESSION COMPLETE 2026-05-30 — Session E:
#   ADMIN-UX1: Admin screen redesigned — Option B (station header + 3 nav cards)
#   ADMIN-UX1-B1: PATCH /inventory/compartments/{id} — edit compartment
#   ADMIN-UX1-F1–F8: AdminScreen, MembersScreen, VehiclesScreen all complete
#   ADMIN-B17/B18 + ADMIN-F11: CSV import — template download + bulk upload
#   B-R1/B-R2/F-R1: Already marked done (Session D)
#   Bug fixes: check wizard 403 for Supervisors; sort_order number input;
#              station selection preserved on Back; OOS/RTS reason forms;
#              vehicle card red border for out-of-service
#
# NEXT SESSION — Session F or continued Session E:
#   F-5F2  Monthly compliance calendar (unblocked by B-E3)
#   F-UX7  Last check banner per vehicle
#   SUPPLY Station supply room and restocking workflow
#   UAT    Begin user acceptance testing with real crew members

---

## ──────────────────────────────────────────────────────────────────────────────
## SESSION PLAN
## ──────────────────────────────────────────────────────────────────────────────
##
## Session A — Security Gate          ✅ COMPLETE 2026-05-26
## Session B — Refactor Sprint        ✅ COMPLETE 2026-05-27
## Session C — Access Control         ✅ COMPLETE 2026-05-29
##
## Session D — Features (3–4 hrs)
##   B-E3    Date-range compliance query endpoint              ~60 min
##   CH-UX1  Unified check resolution workflow (frontend)      ~90 min
##   VE-F5   Open issue badge on V&E Status card               ~45 min
##   D-R1    Documentation audit                               ~60 min
##
## Session E — Core Features (3–4 hrs per session, multiple sessions)
##   B-E5, B-E6, ADMIN-B1–B10, ADMIN-F1–F5, RET-* items
##
## Session F — UAT (1–2 hrs)
##   UAT-1 through UAT-8
##
## ──────────────────────────────────────────────────────────────────────────────

---

## 0. Security — Pre-User Gate ✅ COMPLETE

### OWASP A01 — Broken Access Control ✅ COMPLETE 2026-05-29
| # | Item | Status | Notes |
|---|------|--------|-------|
| ACC-B7 | Enforce station membership on `/checks` | ✅ Done | Session C |
| ACC-B8 | Enforce station membership on `/vehicles` + `/inventory` | ✅ Done | Session C |
| ACC-B9 | Enforce station membership on supervisor dashboard | ✅ Done | Via ACC-B7/B8 |
| ACC-B10 | `deps.py`: `require_station_membership()` | ✅ Done | Session B (REF-4) |

### Remaining low-priority security items
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX34 | Second crew picker — structured user lookup (OWASP A04 long-term fix) | Medium | ⛔ | Needs B-M15, B-E7 |
| I-3 | `HTTPSRedirectMiddleware` in `main.py` (production-gated) | Low | 📋 | OWASP A05 defense-in-depth |

---

## 1. Code — Refactoring Sprint ✅ COMPLETE 2026-05-27
See backlog_completed.md.

---

## 2. Backend — Phase 6 Endpoints
| # | Endpoint | Description | Pri | Status | Needs |
|---|----------|-------------|-----|--------|-------|
| B-E3 | `GET /checks/daily/station/{id}?from=&to=` | Date-range compliance query | High | ✅ Done | Unblocks F-5F2, F-UX7, VE-F5 |
| B-E5 | `POST /inventory/transfer` | Move stock between supply room and vehicle | High | 📋 | |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` | Stock vs par per item | High | 📋 | |
| B-E7 | `GET /stations/{id}/users` | Active users at station via MS Graph | Medium | 📋 | |
| B-E8 | `PUT /inventory/lots/{id}` | Supervisor corrects expiry date on lot | Medium | 📋 | |
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 | |
| B-E10 | `POST /feedback` | Submit bug/enhancement/general feedback | Medium | 📋 | |
| B-E11 | `GET /feedback` | List feedback (Administrator only) | Medium | 📋 | |
| B-E12 | `GET /notifications` | Unread notifications scoped by role | Medium | 📋 | |
| B-E13 | `PATCH /notifications/{id}/read` | Mark notification read | Medium | 📋 | |
| B-E14 | `POST /admin/user-requests` | Supervisor submits user onboarding request | Medium | 📋 | |
| B-E15 | `GET /admin/user-requests` | List user requests (Administrator only) | Medium | 📋 | |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 | |

*All paths prefixed `/api/v1/`*

---

## 3. Backend — Data Models
| # | Item | Pri | Status |
|---|------|-----|--------|
| B-M2 | New table: `notifications` | Medium | 📋 |
| B-M3 | New table: `feedback_entries` | Medium | 📋 |
| B-M4 | New table: `user_requests` | Medium | 📋 |
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 |
| B-M8 | Alter `daily_inventory_checks`: add `started_by` (check handoff) | Medium | 📋 |
| B-M10 | Alter `stations`: add `allow_check_modification` (Boolean, default False) | High | 📋 |
| B-M11 | Alter `stations`: add `primary_color` (String, nullable) | Medium | 📋 |
| B-M12 | New table: `user_preferences` | Medium | 📋 |
| B-M13 | Alter `inventory_lots`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| B-M14 | New table: `loaned_items` | Medium | 📋 |
| B-M15 | Alter `daily_inventory_checks`: add `second_crew_id` (String, nullable) | Medium | 📋 |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M4 | Scheduled nightly job: hard-delete retired objects where `retired_at` > 5 yrs | High | 📋 |

---

## 4. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Administrator force hard-delete (PII spill) | High | 📋 | Admin only |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks within 90-day window | Medium | 📋 | Admin only |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted check within 90-day window | Low | 📋 | Admin only |
| CH-B7 | `PATCH /stations/{id}/settings` | Update station settings incl. `allow_check_modification` | High | 📋 | Admin only |
| CH-B8 | `GET /stations/{id}/settings` | Read station settings | High | 📋 | Supervisor+ |
| CH-B9 | `GET /checks/daily/crew-history` | Checks where current user is second crew | Medium | ⛔ | B-M15 |

---

## 5. Backend — Retirement Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | Retire vehicle | High | 📋 | Supervisor+ |
| RET-B2 | `PATCH /locations/{id}/retire` | Retire jump bag / portable location | High | 📋 | Supervisor+ |
| RET-B3 | `PATCH /stations/{id}/retire` | Retire station | High | 📋 | Admin only |
| RET-B4 | `GET /admin/retired?type=&station_id=` | List retired objects | Medium | 📋 | Admin only |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | Retire a specific lot | High | 📋 | Supervisor+; needs B-M13 |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | List retired lots | Medium | 📋 | Supervisor+ |

---

## 6. Backend — Loaned Item Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| LOAN-B1 | `POST /equipment/loans` | Record a loan | Medium | 📋 | All roles; needs B-M14 |
| LOAN-B2 | `PATCH /equipment/loans/{id}/resolve` | Mark loan resolved | Medium | 📋 | All roles |
| LOAN-B3 | `GET /equipment/loans?vehicle_id=&resolved=false` | Open loans for a vehicle | Medium | 📋 | Supervisor+ |
| LOAN-B4 | `GET /equipment/loans/my?resolved=false` | Current user's open loans | Medium | 📋 | All roles |

---

## 7. Frontend — Phase 5C: Help System
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5C1 | First-run tutorial — 8 steps, auto-shown on first login, replayable, skip button | High | 📋 |
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | High | 📋 |
| F-5C3 | Searchable FAQ — client-side filter, crew + supervisor sections, 15 questions | Medium | 📋 |
| F-5C4 | `src/modules/help/content.js` — single source of truth for all help text | Medium | 📋 |

---

## 8. Frontend — Phase 5D: Item Management
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5D1 | Item catalog search component | Medium | 📋 |
| F-5D2 | Add item form — Responder requests; Supervisor/Admin adds directly | Medium | 📋 |
| F-5D3 | Remove item with mandatory documented reason | Medium | 📋 |

---

## 9. Frontend — V&E Status
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| VE-F2 | Open loans panel — unresolved loans per vehicle; Resolve button per row | Medium | 📋 | LOAN-B3 |
| VE-F3 | Log a loan form — lot picker + destination note field | Medium | 📋 | LOAN-B1 |
| VE-F4 | Resolve loan modal — optional note, calls LOAN-B2 | Medium | 📋 | LOAN-B2 |
| VE-F5 | **Open issue badge on V&E Status card (home screen)** | High | ✅ Done | Uses today endpoint (exists); upgraded by B-E3 |

### VE-F5 — Open Issue Badge: Full Specification

**User story:** As any crew member, when I open the app and select a station, I need to
immediately know if there is an unresolved vehicle or equipment issue so I can act before
going on shift — without having to open V&E Status to find out.

**Location:** The "Vehicle & Equipment Status" module card on `HomePage.jsx`.
Visible to **all roles** (Responder, Supervisor, Administrator).
Station-scoped: always reflects the **currently selected station** only.

**Two badge states:**

| State | Colour | Label | Trigger |
|-------|--------|-------|---------|
| New | 🔴 Red | `New Issue` | Unacknowledged FAIL daily check (`reviewed_at IS NULL`) OR open URGENT repair request |
| In Progress | 🟡 Yellow | `In Progress` | FAIL acknowledged but URGENT repair not resolved |
| None | — | *(no badge)* | All FAILs acknowledged and all URGENT repairs resolved |

**Priority:** New beats In Progress when both exist simultaneously.

**Data sources (no new endpoints needed):**
- `GET /checks/daily/station/{id}/today` — filter client-side for `status === 'FAIL'`
- `GET /vehicles/{id}/repair-requests?status=OPEN` — filter for `severity === 'URGENT'`

**Future upgrade:** Once B-E3 is built, replace today-only with rolling 24-hour window.

**Badge CSS:**
```css
.module-card__issue-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 700; padding: 2px 8px;
  border-radius: 999px; margin-top: 4px; width: fit-content;
}
.module-card__issue-badge--new         { background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; }
.module-card__issue-badge--in-progress { background: #fefce8; color: #ca8a04; border: 1px solid #fde68a; }
```

**Acceptance criteria:**
- [ ] Red "New Issue" for unacknowledged FAIL or open URGENT repair
- [ ] Yellow "In Progress" for acknowledged FAIL with unresolved URGENT repair
- [ ] No badge when no open issues
- [ ] Refreshes on window focus; fails silently
- [ ] All three roles see the badge

---

## 10. Frontend — Phase 5F: Supervisor Dashboard
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-5F2 | Monthly compliance calendar — color-coded per vehicle per day | High | ⛔ | B-E3 |
| F-5F6 | Notification bell with unread badge | Medium | ⛔ | B-E12 |
| F-5F7 | Supply room stock view (stock vs par, color coded, reorder form) | Medium | 📋 | B-E6 |

---

## 11. Frontend — Phase 5G: Supporting Modules
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-5G1 | Feedback module — floating button, bug/enhancement/general form | Medium | 📋 | |
| F-5G2 | User management module | Medium | ⛔ | B-E14 |
| F-5G3 | Data export — CSV for check history, audit events, repair requests | Medium | 📋 | |
| F-5G4 | Role switcher (crew mode for supervisors) — amber CREW MODE badge | Low | 📋 | |

---

## 12. Frontend — Check Wizard UX
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-UX2 | Left/right chevron navigation between compartments | Medium | 📋 | |
| F-UX3 | "Jump to unvalidated" sticky button | Medium | 📋 | |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | |
| F-UX7 | **Last check banner** — per vehicle, color-coded green/amber/red | High | ⛔ | B-E3 |
| F-UX8 | Item count on compartment cards | Low | 📋 | |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | |
| F-UX10 | "Caller/spotter view" large-text mode | Low | 📋 | |
| F-UX32 | BORROWED badge on loaned items during check; shortcut to V&E Status | Medium | 📋 | B-M14 |
| F-UX34 | Second crew picker — structured user lookup (OWASP A04 long-term fix) | Medium | ⛔ | B-M15, B-E7 |
| F-UX35 | Draft banner visible while station API loading | High | ✅ Done | Implemented via `ems_last_station_id` fallback in `useDraftIndex` |

---

## 13. Frontend — Check History (remaining)
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note on submitted check | High | ⛔ | B-M10, CH-B8 |
| CH-F7 | Deleted records screen (Admin) — restore or force hard-delete | High | 📋 | |
| CH-F8 | Force hard-delete confirmation — type "PERMANENTLY DELETE" to confirm | High | 📋 | |
| CH-F9 | "Checks I helped with" tab in Check History | Medium | ⛔ | B-M15, CH-B9 |

---

## 14. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F1 | Settings nav entry — role-scoped visibility | High | 📋 | |
| S-F2 | Station color picker (Supervisor+) — live preview | Medium | 📋 | B-M11 |
| S-F3 | Allow check modification toggle (Admin only) | High | 📋 | B-M10 |
| S-F4 | Default station selector (all roles) | Medium | 📋 | B-M12 |
| S-F5 | Display name / preferred name override (all roles) | Low | 📋 | B-M12 |
| S-F6 | Station management — create, edit, retire | High | 📋 | RET-B3/B4 |
| S-F7 | Vehicle / portable equipment management — add, edit, retire | High | 📋 | RET-B1/B2 |
| S-F8 | Par level management — view and edit per vehicle/compartment | Medium | 📋 | B-E9 |
| S-F9 | User onboarding management — approve/reject, assign role + station | Medium | 📋 | B-E14/15 |

---

## 15. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle (Supervisor+) | High | 📋 | RET-B1 |
| RET-F2 | Retire jump bag / portable location (Supervisor+) | High | 📋 | RET-B2 |
| RET-F3 | Retire inventory lot (Supervisor+) | High | 📋 | RET-B5, B-M13 |
| RET-F4 | Retire station (Admin only) | High | 📋 | RET-B3 |
| RET-F5 | Retired objects list (Admin) — filterable by type, read-only | Medium | 📋 | RET-B4 |

---

## 16. Infrastructure / Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall in `modules/network` with UDR + FQDN allow-list | Medium | 📋 | |
| I-2 | Re-add route table to subnets | Medium | ⛔ | I-1 |
| I-3 | `HTTPSRedirectMiddleware` in `main.py` (production-gated) | Low | 📋 | OWASP A05 defense-in-depth |
| I-5 | Document Azure AD token lifetime; confirm CAE enabled | Low | 📋 | |
| I-6 | Write `docs/adr/ADR-006-DDoS-Strategy.md` | Low | 📋 | |

---

## 17. Equipment & Station Administration (B-ADMIN1)

### Phase 1 — Item & Par Management
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B1 | `GET /admin/items` | List global item catalog | High | ✅ Done | |
| ADMIN-B2 | `POST /admin/items` | Add item to global catalog | High | ✅ Done | Admin + Supervisor |
| ADMIN-B3 | `PATCH /admin/items/{id}` | Edit item | High | ✅ Done | Admin + Supervisor |
| ADMIN-B4 | `PATCH /admin/items/{id}/deactivate` | Soft-deactivate item | High | ✅ Done | Admin only |
| ADMIN-B5 | `GET /admin/items/search` | Typeahead search across name, alternate_names, ai_tags | High | ✅ Done | |
| ADMIN-B6 | `POST /admin/items/{id}/assign` | Assign item to vehicle compartment | High | ✅ Done | Derives location_id server-side |
| ADMIN-B7 | `PATCH /admin/par-levels/{id}` | Edit par level min/max | High | ✅ Done | |
| ADMIN-B8 | `DELETE /admin/par-levels/{id}` | Remove item from compartment (soft) | High | ✅ Done | Supervisor+ |
| ADMIN-B9 | `GET /admin/items/{id}/assignments` | List enriched assignments for an item | High | ✅ Done | |
| ADMIN-B10 | `GET /admin/vehicles/{id}/compartments` | Compartments for vehicle cascade picker | High | ✅ Done | |
| ADMIN-B17 | `POST /admin/items/import` | Bulk import items from CSV upload | High | ✅ Done | Supervisor+; BOM-safe; 2MB/1000 row limit |
| ADMIN-B18 | `GET /admin/items/import/template` | Download CSV template with headers + example rows | High | ✅ Done | |
| ADMIN-F1 | Admin home card | High | ✅ Done | Option B nav cards |
| ADMIN-F2 | Item catalog list view | High | ✅ Done | |
| ADMIN-F3 | Add/edit item form | High | ✅ Done | |
| ADMIN-F4 | Par level editor | High | ✅ Done | ItemAssignments panel |
| ADMIN-F5 | Compartment editor | High | ✅ Done | Inline in VehiclesScreen |
| ADMIN-F10 | Member list search | Low | 📋 | Needed once stations have 20+ members |
| ADMIN-F11 | CSV import UI — file picker, upload, results summary, template download | High | ✅ Done | |

### ADMIN-B17/B18 + ADMIN-F11 — CSV Item Import: Full Specification

**Why this matters:** Manually entering 200+ items one at a time through the UI is
unreasonable. A CSV import lets an administrator prepare the full inventory list
in a spreadsheet, validate it offline, and load it in one upload.

**Backend — `POST /admin/items/import`**
- Accepts `multipart/form-data` with a single CSV file field
- Admin only (not Supervisor — bulk import is a high-trust action)
- Processes rows sequentially; does not fail the entire import on a single bad row
- Per-row behavior:
  - Row is valid and item name is new → created
  - Row is valid and item name already exists → skipped (not updated — use Edit for that)
  - Row has a validation error → recorded in errors list, import continues
- Returns a structured result:
  ```json
  {
    "created": 147,
    "skipped": 12,
    "errors": [
      { "row": 4, "name": "O2 PSI", "error": "measurement_minimum required for MEASUREMENT items" },
      { "row": 9, "name": "",       "error": "name is required" }
    ]
  }
  ```
- Max file size: 2MB. Max rows: 1000. Rows beyond limit are ignored with a warning.
- UTF-8 encoding required. BOM-safe (Excel exports BOM by default).

**CSV columns (order-independent, matched by header name):**

| Column | Required | Notes |
|--------|----------|-------|
| `name` | Yes | Max 150 chars, must be unique |
| `category` | Yes | Medication / Consumable / Equipment / Document |
| `check_type` | No | SUPPLY (default) / MEASUREMENT / FUNCTIONAL / DATE_RECORD / DOCUMENT |
| `unit_of_measure` | Yes | e.g. each, PSI, N/A |
| `controlled_substance` | No | TRUE / FALSE (default FALSE) |
| `measurement_minimum` | Conditional | Required when check_type = MEASUREMENT |
| `measurement_maximum` | No | Optional upper bound for MEASUREMENT items |
| `recurrence_days` | Conditional | Required when check_type = DATE_RECORD |
| `alternate_names` | No | Comma-separated crew shorthand |
| `ai_tags` | No | Comma-separated AI classifier keywords |
| `barcode` | No | UPC/GS1; must be unique if provided |

**Backend — `GET /admin/items/import/template`**
- Returns a downloadable CSV file with:
  - Correct headers in the expected order
  - 3 example rows (one SUPPLY, one MEASUREMENT, one DATE_RECORD)
  - Filename: `ems_readykit_items_template.csv`
- Admin only

**Frontend — `ADMIN-F11` — CSV Import UI**
- Lives in the Item Catalog screen, below the "+ Add item" button
- A secondary button: "↑ Import from CSV"
- Tapping it reveals:
  1. "Download template" link (calls ADMIN-B18)
  2. File picker (accepts .csv only)
  3. "Upload" button (disabled until file selected)
- After upload, shows a clean results panel:
  - Green: "{n} items added to the catalog"
  - Yellow: "{n} items skipped (already exist)"
  - Red: "{n} rows had errors" with a collapsible list showing row number + error
- On success, catalog list refreshes automatically
- Error rows can be downloaded as a CSV for easy fixing

**Acceptance criteria:**
- [ ] Admin can upload a valid CSV and see items appear in catalog immediately
- [ ] Duplicate names are skipped gracefully — not rejected as errors
- [ ] Invalid rows show row number and plain-English error message
- [ ] Template downloads with correct headers and example rows
- [ ] Non-admin roles get 403 on both endpoints
- [ ] File over 2MB or over 1000 rows returns a clear error before processing
- [ ] BOM-prefixed files from Excel are handled correctly

### Phase 2 — Vehicle & Location Management
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B11 | `POST /admin/vehicles` | Add vehicle to a station | High | 📋 | Admin + Supervisor |
| ADMIN-B12 | `PATCH /admin/vehicles/{id}` | Edit vehicle | High | 📋 | Admin + Supervisor |
| ADMIN-B13 | `POST /admin/locations` | Add portable location | High | 📋 | Admin + Supervisor |
| ADMIN-B14 | `PATCH /admin/locations/{id}` | Edit location label/type | High | 📋 | Admin + Supervisor |
| ADMIN-F6 | Vehicle list view per station — add, edit, retire | High | 📋 | |
| ADMIN-F7 | Portable location list view per station — add, edit, retire | High | 📋 | |

### Phase 3 — Station Onboarding
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B15 | `POST /admin/stations` | Create new station | Medium | 📋 | Admin only |
| ADMIN-B16 | `POST /admin/stations/{id}/clone-layout` | Copy layout from existing station | Medium | 📋 | Admin only |
| ADMIN-F8 | New station wizard | Medium | 📋 | |
| ADMIN-F9 | Layout clone picker | Medium | 📋 | |

---

## 18. Station Membership & Access Control (B-ACCESS1)

### Backend [ALL COMPLETE]
| # | Item | Status | Notes |
|---|------|--------|-------|
| ACC-M1 | New table: `station_members` | ✅ Done | 2026-05-25 |
| ACC-M2 | Migration: add `station_members` table | ✅ Done | 2026-05-25 |
| ACC-B1–B6 | Membership CRUD endpoints | ✅ Done | 2026-05-25 |
| ACC-B7 | Membership enforced on `/checks` | ✅ Done | 2026-05-29 |
| ACC-B8 | Membership enforced on `/vehicles` + `/inventory` | ✅ Done | 2026-05-29 |
| ACC-B9 | Membership enforced on supervisor dashboard | ✅ Done | 2026-05-29 |
| ACC-B10 | `deps.py`: `require_station_membership()` | ✅ Done | 2026-05-27 |

### Frontend
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-F1 | Station picker uses `GET /stations/my` | High | 📋 | |
| ACC-F2 | Member list view | High | 📋 | Supervisor+ |
| ACC-F3 | Add member form | High | 📋 | |
| ACC-F4 | Remove member confirmation | High | 📋 | |
| ACC-F5 | "Pending assignment" screen | High | 📋 | |

### Open Questions
| # | Question | Owner |
|---|----------|-------|
| Q-11 | User lookup when adding a member: MS Graph search or free-text? | Engineering |
| Q-13 | Seed: auto-assign admin to all stations? Dowagiac station pending. | Engineering |

---

## 19. Documentation
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| D-R1 | **Documentation audit** — full review of all docs | High | ✅ Done | README rewritten with feature list; project_index updated; 14 stale files archived; 10 docs → 7 |

---

## 20. User Acceptance Testing (UAT)
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-1 | Write test case document — one sheet per role | High | 📋 | |
| UAT-2 | Responder test cases | High | 📋 | |
| UAT-3 | Supervisor test cases | High | 📋 | |
| UAT-4 | Administrator test cases | High | 📋 | |
| UAT-5 | Cross-role test cases | Medium | 📋 | |
| UAT-6 | Edge case test cases | Medium | 📋 | |
| UAT-7 | Pending assignment test case | High | ⛔ | Needs ACC-F5 |
| UAT-8 | Multi-station test case | Medium | ⛔ | Needs ACC-F1–F5 |

---

## 21. Check Resolution Workflow (CH-UX1)

**Problem:** FAIL resolution is split across Check History and Compliance Dashboard.
**Solution:** Unified panel — one button captures corrective action + resolved/pending.
No new endpoints — uses existing `PATCH /checks/daily/{id}/acknowledge`.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| CH-UX1-F1 | Bring `IFixedThisForm` into `CheckDetail.jsx` | High | ✅ Done | `IFixedThisPanel` added; calls `supervisorApi.resolveFailedItems` |
| CH-UX1-F2 | Unified resolution panel | High | ✅ Done | Shared `ResolutionTag` + `getResolutionState` in `shared/components/` |
| CH-UX1-F3 | Resolved/Pending visual state on check detail | High | ✅ Done | `ResolutionTag` shown in summary header |
| CH-UX1-F4 | Compliance Dashboard "I Fixed This" uses same panel | Medium | ✅ Done | `CheckDetailPanel` already correct; `supervisorApi` shared |
| CH-UX1-F5 | Check card in history list shows "Resolved" indicator | Medium | ✅ Done | `CheckList` rows now use `ResolutionTag` |

---

## 22. Repair Request Workflow Bugs (B-R)

**Context:** Discovered during testing on 2026-05-29 via Vehicle & Equipment Status → vehicle expanded panel.
See screenshots: `Vehicle_Expanded_Screen_1.png`, `Vehicle_Expanded_Screen_2.png`.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| B-R1 | Wrong modal on "Mark In Progress" — opens Resolve dialog instead of In Progress flow | High | ✅ Done | |
| B-R2 | "Mark Resolved" button non-functional inside incorrectly-triggered Resolve modal | High | ✅ Done | |
| F-R1 | New "Mark In Progress" lightweight modal — optional comment, no resolution required, all roles | High | ✅ Done | |

### F-R1 — Mark In Progress Modal: Full Specification

**Trigger:** "Mark In Progress" action link on repair request card in V&E Status expanded panel.

**Behavior:**
- Opens a small modal (does NOT close/resolve the ticket)
- Shows repair request title as read-only context
- Optional comment/note field: `Add a note... (optional)`
- Two buttons: **Confirm** (transitions status to In Progress) and **Cancel**
- No resolution notes required
- Available to **all roles** — no supervisor restriction
- On confirm: status → `IN_PROGRESS`; comment stored if provided

**Acceptance criteria:**
- [ ] Clicking "Mark In Progress" opens the new lightweight modal, not the Resolve modal
- [ ] Comment field is optional — confirm works with or without text
- [ ] Status transitions to IN_PROGRESS on confirm
- [ ] Cancel dismisses with no change
- [ ] All roles (Responder, Supervisor, Administrator) can perform the action
- [ ] Card reflects updated status after confirm

---

## 23. Station Supply Room & Restocking (SUPPLY)

**Context:** Ambulances are restocked from the station supply room.
Currently no way to track station-level inventory or record transfers.
The `STATION_SUPPLY_ROOM` LocationType already exists in the data model —
this is the correct implementation path (not a "fake vehicle").

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SUPPLY-M1 | Ensure `STATION_SUPPLY_ROOM` location auto-created per station (migration) | High | 📋 | LocationType already defined in model |
| SUPPLY-B1 | `POST /inventory/transfer` — move stock from supply room to vehicle | High | 📋 | Supervisor+; atomic debit/credit |
| SUPPLY-B2 | `GET /inventory/locations/{id}/stock-summary` — stock vs par per item | High | 📋 | All roles + membership |
| SUPPLY-B3 | `GET /stations/{id}/supply-room` — get or create supply room location | High | 📋 | Auto-creates if missing |
| SUPPLY-F1 | Supply room stock view — items, quantities, par comparison | High | 📋 | Supervisor+ |
| SUPPLY-F2 | Restock vehicle flow — pick vehicle, pick items, confirm transfer | High | 📋 | Supervisor+ |
| SUPPLY-F3 | Receive stock into supply room — add lot, quantity, expiry | Medium | 📋 | Supervisor+ |
| SUPPLY-F4 | Transfer history per vehicle / per supply room | Medium | 📋 | Audit trail |

**Key design decisions to make before building:**
- Transfer is atomic: supply room quantity decreases, vehicle par is not changed (par = target, not current stock)
- Stock on hand is derived from transfer history, not a stored counter — avoids sync bugs
- Open question: does a FAIL check auto-suggest a restock? (Q-11 below)

---

## 24. Par Level Assignment UI (ADMIN-F4 — Phase 2)

**Context:** Item catalog (ADMIN-F1–F3) is built. Missing piece:
assigning an item to a vehicle compartment with a required quantity.

**UX flow (decided 2026-05-29):** Item-first, not vehicle-first.
From the item card in the catalog → "Assign to Vehicle" →
pick vehicle → pick compartment → set min qty ("Needs at least") +
max qty ("Restock to") → Save.

Item card shows current assignments: "Assigned to: TEST / PC 3, TEST / Drug Bag".

**On max quantity:** Keep both min and max in the UI.
Min = flag threshold. Max = "restock to" target — used by the restocking
workflow (SUPPLY-F2) to know how much to transfer.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-F4a | Par level list on item card — shows vehicle/compartment/min/max | High | 📋 | Item-first view |
| ADMIN-F4b | "Assign to Vehicle" flow — vehicle picker → compartment picker → qty form | High | 📋 | Uses `ItemSearchCombobox` pattern |
| ADMIN-F4c | Edit/remove par level from item card | High | 📋 | Supervisor+; soft-deactivate |
| ADMIN-B6 | `POST /inventory/par-levels` (expose from admin router) | High | 📋 | Already exists in inventory router |
| ADMIN-B7 | `PATCH /inventory/par-levels/{id}` — edit min/max | High | 📋 | |
| ADMIN-B8 | `PATCH /inventory/par-levels/{id}/deactivate` — remove assignment | High | 📋 | Admin only |

---

## 25. Admin Screen Redesign — Option B (ADMIN-UX1)

**Context:** Decided 2026-05-29. The current tab bar (Members | Item Catalog) is
getting crowded as Vehicles management is added. The primary real-world user is
68 years old, iPhone, not tech-savvy — needs maximum clarity and zero learning curve.

**Decision:** Option B — Station header + large navigation cards, each leading to
a dedicated full-screen view. Mirrors the home screen module card pattern the user
already knows. One task at a time, full screen per section, Back button to return.

**UX principles driving this design:**
- 60px minimum tap targets throughout
- One task at a time — never two sections competing for attention
- Reuse the existing module card navigation pattern (zero learning curve)
- Clear text labels on everything — no icon-only buttons
- Forgiveness — destructive actions require confirmation
- Station selector: 1 station = plain header; 2-3 = stacked cards; 4+ = search added
- "+ Add Station" is a low-prominence text button at bottom, Admin only

**Admin home screen layout:**
```
Station Administration

Managing: Marcellus Township Station 1  [Change]

┌─────────────────────────────────────┐
│  👥  Members                3 active │  →
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  📦  Item Catalog          12 items  │  →
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  🚑  Vehicles               2 units  │  →
└─────────────────────────────────────┘

                        [+ Add Station]  (Admin only)
```

Each card navigates to a dedicated full-screen sub-screen with ← Back at top.

**Work items:**

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-UX1-F1 | Redesign `AdminScreen` — station header + 3 nav cards | High | ✅ Done | |
| ADMIN-UX1-F2 | `MembersScreen` — full-screen members management | High | ✅ Done | |
| ADMIN-UX1-F3 | `ItemCatalogScreen` — full-screen item catalog | High | ✅ Done | |
| ADMIN-UX1-F4 | `VehiclesScreen` — full-screen vehicle + compartment management | High | ✅ Done | |
| ADMIN-UX1-B1 | `PATCH /admin/compartments/{id}` — edit compartment | High | ✅ Done | |
| ADMIN-UX1-F5 | Add vehicle form — vehicle number, type (ALS/BLS/QRV) | High | ✅ Done | |
| ADMIN-UX1-F6 | Vehicle card — shows compartments, add/edit compartment inline | High | ✅ Done | |
| ADMIN-UX1-F7 | Add compartment form — name, descriptor, sort order, restriction note | High | ✅ Done | |
| ADMIN-UX1-F8 | Station selector — plain header (1 station), stacked cards (2-3), search (4+) | High | ✅ Done | |
| ADMIN-UX1-F9 | "+ Add Station" — Admin only, low-prominence, bottom of admin home | Medium | 📋 | Calls existing POST /stations |

**Session E start point:**
Begin with ADMIN-UX1-F1 (redesign AdminScreen shell) then work inward.
All backend for Members and Item Catalog already exists.
One new backend endpoint needed: ADMIN-UX1-B1 (edit compartment).

---

## 26. Open Questions
| # | Question | Owner |
|---|----------|-------|
| Q-1 | Notification delivery: email (Azure Comms) or in-app only? | Project owner |
| Q-2 | MS Graph user lookup: cache in DB? | Engineering |
| Q-3 | 90-day max range sufficient for compliance calendar? | Project owner |
| Q-4 | BLOCKING feedback bugs auto-create GitHub issue? | Project owner |
| Q-5 | Supply room reorder tracking: Phase 6 or defer to Phase 7? | Project owner |
| Q-6 | Auto-hard-delete scheduler: Azure Function or startup cleanup job? | Engineering |
| Q-7 | Check modification setting default: False (conservative) or True (permissive)? | Project owner |
| Q-8 | Restored soft-deleted checks: responder history or admin screen only? | Project owner |
| Q-9 | 5-year hard-delete job: share with Q-6 or separate process? | Engineering |
| Q-10 | Second crew lookup: MS Graph or local user list? Affects B-E7 and F-UX34. | Engineering |
| Q-11 | Should a FAIL check auto-suggest a restock from the supply room? | Project owner |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Security — remaining low-priority (Section 0) | 2 | 1 | 3 |
| Backend — Phase 6 Endpoints | 13 | 0 | 13 |
| Backend — Data Models | 15 | 0 | 15 |
| Backend — Check History | 5 | 1 | 6 |
| Backend — Retirement | 6 | 0 | 6 |
| Backend — Loaned Items | 4 | 0 | 4 |
| Frontend — Phase 5C Help | 4 | 0 | 4 |
| Frontend — Phase 5D Item Mgmt | 3 | 0 | 3 |
| Frontend — V&E Status | 4 | 0 | 4 |
| Frontend — Phase 5F Supervisor | 1 | 2 | 3 |
| Frontend — Phase 5G Supporting | 3 | 1 | 4 |
| Frontend — Check Wizard UX | 10 | 3 | 13 |
| Frontend — Check History (remaining) | 3 | 1 | 4 |
| Frontend — Settings | 9 | 0 | 9 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Infrastructure / Security | 4 | 1 | 5 |
| Equipment & Station Admin (B-ADMIN1) | 2 | 0 | 19 |
| Station Membership Frontend (B-ACCESS1) | 5 | 0 | 5 |
| Documentation | 0 | 0 | 1 |
| User Acceptance Testing (UAT) | 6 | 2 | 8 |
| Check Resolution Workflow (CH-UX1) | 0 | 0 | 5 |
| Admin Screen Redesign (ADMIN-UX1) | 1 | 0 | 10 |
| Station Supply Room & Restocking (SUPPLY) | 8 | 0 | 8 |
| Par Level Assignment UI (ADMIN-F4) | 6 | 0 | 6 |
| Repair Request Workflow Bugs (B-R) | 0 | 0 | 3 |
| **Total** | **118** | **12** | **168** |
