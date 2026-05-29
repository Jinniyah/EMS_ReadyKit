# EMS ReadyKit — Active Backlog
# v1.35 | Updated: 2026-05-29
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
# NEXT SESSION — Session D (features):
#   B-E3    Date-range compliance query endpoint  → unblocks F-5F2, F-UX7, VE-F5
#   CH-UX1  Unified check resolution workflow (frontend only)
#   VE-F5   Open issue badge on V&E Status card
#   D-R1    Documentation audit

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
| ADMIN-B1 | `GET /admin/items` | List global item catalog | High | 📋 | |
| ADMIN-B2 | `POST /admin/items` | Add item to global catalog | High | 📋 | Admin + Supervisor |
| ADMIN-B3 | `PATCH /admin/items/{id}` | Edit item | High | 📋 | Admin + Supervisor |
| ADMIN-B4 | `PATCH /admin/items/{id}/deactivate` | Soft-deactivate item | High | 📋 | Admin only |
| ADMIN-B5 | `GET /admin/locations/{id}/par-levels` | List par levels for a location | High | 📋 | |
| ADMIN-B6 | `POST /admin/par-levels` | Add item to compartment | High | 📋 | Admin + Supervisor |
| ADMIN-B7 | `PATCH /admin/par-levels/{id}` | Edit min/max qty | High | 📋 | Admin + Supervisor |
| ADMIN-B8 | `PATCH /admin/par-levels/{id}/deactivate` | Remove item from compartment (soft) | High | 📋 | Admin only |
| ADMIN-B9 | `POST /admin/compartments` | Add compartment to a location | High | 📋 | Admin + Supervisor |
| ADMIN-B10 | `PATCH /admin/compartments/{id}` | Edit compartment | High | 📋 | Admin + Supervisor |
| ADMIN-F1 | Admin home card | High | 📋 | |
| ADMIN-F2 | Item catalog list view | High | 📋 | |
| ADMIN-F3 | Add/edit item form | High | 📋 | |
| ADMIN-F4 | Par level editor | High | 📋 | |
| ADMIN-F5 | Compartment editor | High | 📋 | |
| ADMIN-F10 | Member list search | Low | 📋 | Needed once stations have 20+ members |

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
| B-R1 | Wrong modal on "Mark In Progress" — opens Resolve dialog instead of In Progress flow | High | 📋 | Frontend only; split handlers |
| B-R2 | "Mark Resolved" button non-functional inside incorrectly-triggered Resolve modal | High | 📋 | Investigate after B-R1; may share root cause |
| F-R1 | New "Mark In Progress" lightweight modal — optional comment, no resolution required, all roles | High | 📋 | Depends on B-R1 fix |

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
| Equipment & Station Admin (B-ADMIN1) | 19 | 0 | 19 |
| Station Membership Frontend (B-ACCESS1) | 5 | 0 | 5 |
| Documentation | 1 | 0 | 1 |
| User Acceptance Testing (UAT) | 6 | 2 | 8 |
| Check Resolution Workflow (CH-UX1) | 5 | 0 | 5 |
| Repair Request Workflow Bugs (B-R) | 0 | 0 | 3 |
| **Total** | **127** | **12** | **139** |
