# EMS ReadyKit — Active Backlog
# v1.47 | Updated: 2026-05-30
# Completed items → backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ SESSION COMPLETE 2026-05-24 — Phase 5H Infrastructure
# ✅ SESSION COMPLETE 2026-05-25 — Draft flow, UTC fix, Azure AD, station membership endpoints
# ✅ SESSION COMPLETE 2026-05-26 — Session A: Security Gate (OWASP A02/A04/A05/A06/A09, 0 CVEs)
# ✅ SESSION COMPLETE 2026-05-27 — Session B: Refactor Sprint (REF-1 through REF-7)
# ✅ SESSION COMPLETE 2026-05-29 — Session C: Access Control Enforcement (OWASP A01)
# ✅ SESSION COMPLETE 2026-05-29 — Session D: Features
# ✅ SESSION COMPLETE 2026-05-30 — Session E: Admin updates and bug fixes
# ✅ SESSION COMPLETE 2026-05-30 — Session F: Station Setup + Compliance Calendar + Par Levels
#    Block 1 ✅ Color System (B-M11, NEW-M1, S-F2, ADMIN-UX1-V)
#    Block 2 ✅ Add Station (ADMIN-B15, ADMIN-UX1-F9, call_sign migration)
#    Block 3 ✅ Compliance Calendar (F-5F2)
#    Block 4 ✅ Last-Check Banner (F-UX7)
#    Block 5 ✅ Par Level Assignment UI (ADMIN-F4a/b/c, B6, B7, B8)
#    Block 6 ✅ UAT Document (UAT-1) — docs/uat_test_cases.md
# ✅ SESSION COMPLETE 2026-06-01 — Session F UAT + Vehicle-Centric Par Level View
#    ✅ CODEBASE_INDEX updated (migrations 0010–0013, 217 tests)
#    ✅ GET /admin/compartments/{id}/assignments — new endpoint
#    ✅ CompartmentParLevels.jsx — add/edit/remove items per compartment from VehiclesScreen
#    ✅ Phone layout fix — 48px tap targets, stacked rows, compartment name+Edit top row
#    ✅ Block 5 UAT all pass. Next: Session G (Supply Room & Restocking)

---

## ──────────────────────────────────────────────────────────────────────────────
## UPCOMING SESSIONS
## ──────────────────────────────────────────────────────────────────────────────
##
## Session G — Supply Room & Restocking (3–4 hrs)
##   SUPPLY-M1     Migration: supply room location per station ~20 min
##   SUPPLY-B1–B3  Transfer, stock summary, supply room endpoints ~60 min
##   SUPPLY-F1     Supply room stock view                      ~45 min
##   SUPPLY-F2     Restock vehicle flow                        ~60 min
##   SUPPLY-F3     Receive stock into supply room              ~30 min
##
## Session H — Check Wizard UX Polish (2–3 hrs)
##   F-UX2         Left/right chevron nav between compartments ~30 min
##   F-UX3         Jump to unvalidated sticky button           ~30 min
##   F-UX6         Compartment location descriptor on cards    ~20 min
##   F-UX4         Expired item replacement prompt             ~45 min
##   F-UX8         Item count on compartment cards             ~20 min
##   B-E8          PUT /inventory/lots/{id} — correct expiry   ~30 min
##   CH-F7/F8      Deleted records screen + force hard-delete  ~45 min
##
## Session I — Retirement, Settings & Data Export (3–4 hrs)
##   RET-M1–M3     Migrations: retired_at/by/reason            ~30 min
##   RET-B1–B4     Retire vehicle/location/station endpoints   ~45 min
##   RET-F1–F5     Retire actions in UI                        ~60 min
##   F-5G3         Data export — CSV for history/audit/repairs  ~45 min
##   B-E18         GET /audit?from=&to= — date-range audit      ~30 min
##   S-F3          Allow check modification toggle (Admin)      ~20 min
##   S-F6          Station management in Settings               ~30 min
##
## Session J — UAT, Help System & Final Polish (2–3 hrs)
##   UAT-2–6       Execute all UAT test cases                   ~60 min
##   F-5C1         First-run tutorial — 8 steps                 ~45 min
##   F-5C2         Contextual ? help — bottom sheet per step     ~30 min
##   F-5G1         Feedback module — floating button + form      ~30 min
##   B-E10/B-E11   Feedback endpoints                           ~20 min
##   I-3           HTTPSRedirectMiddleware                      ~10 min
##   I-6           ADR-006 DDoS strategy decision record        ~20 min
##
## ──────────────────────────────────────────────────────────────────────────────

---

## 0. Security — Pre-User Gate

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX34 | Second crew picker — structured user lookup | Medium | ⛔ | Needs B-M15, B-E7 |
| I-3 | `HTTPSRedirectMiddleware` in `main.py` | Low | 📋 | |

---

## 2. Backend — Phase 6 Endpoints
| # | Endpoint | Description | Pri | Status |
|---|----------|-------------|-----|--------|
| B-E5 | `POST /inventory/transfer` | Move stock between supply room and vehicle | High | 📋 |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` | Stock vs par per item | High | 📋 |
| B-E7 | `GET /stations/{id}/users` | Active users at station via MS Graph | Medium | 📋 |
| B-E8 | `PUT /inventory/lots/{id}` | Supervisor corrects expiry date on lot | Medium | 📋 |
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 |
| B-E10 | `POST /feedback` | Submit bug/enhancement/general feedback | Medium | 📋 |
| B-E11 | `GET /feedback` | List feedback (Administrator only) | Medium | 📋 |
| B-E12 | `GET /notifications` | Unread notifications scoped by role | Medium | 📋 |
| B-E13 | `PATCH /notifications/{id}/read` | Mark notification read | Medium | 📋 |
| B-E14 | `POST /admin/user-requests` | Supervisor submits user onboarding request | Medium | 📋 |
| B-E15 | `GET /admin/user-requests` | List user requests (Administrator only) | Medium | 📋 |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 |

---

## 3. Backend — Data Models
| # | Item | Pri | Status |
|---|------|-----|--------|
| B-M2 | New table: `notifications` | Medium | 📋 |
| B-M3 | New table: `feedback_entries` | Medium | 📋 |
| B-M4 | New table: `user_requests` | Medium | 📋 |
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 |
| B-M8 | Alter `daily_inventory_checks`: add `started_by` | Medium | 📋 |
| B-M10 | Alter `stations`: add `allow_check_modification` | High | 📋 |
| B-M11 | Alter `stations`: add `primary_color` | High | ✅ Done |
| NEW-M1 | Alter `vehicles`: add `vehicle_color` | High | ✅ Done |
| NEW-M2 | Alter `stations`: add `call_sign` | High | ✅ Done |
| B-M12 | New table: `user_preferences` | Medium | 📋 |
| B-M13 | Alter `inventory_lots`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| B-M14 | New table: `loaned_items` | Medium | 📋 |
| B-M15 | Alter `daily_inventory_checks`: add `second_crew_id` | Medium | 📋 |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M4 | Scheduled nightly job: hard-delete retired objects > 5 yrs | High | 📋 |

---

## 4. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Force hard-delete | High | 📋 | Admin only |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks | Medium | 📋 | Admin only |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted check | Low | 📋 | Admin only |
| CH-B7 | `PATCH /stations/{id}/settings` | Update station settings | High | 📋 | Admin only |
| CH-B8 | `GET /stations/{id}/settings` | Read station settings | High | 📋 | Supervisor+ |
| CH-B9 | `GET /checks/daily/crew-history` | Checks where current user is second crew | Medium | ⛔ | B-M15 |

---

## 5. Backend — Retirement Endpoints
| # | Endpoint | Pri | Status |
|---|----------|-----|--------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | High | 📋 |
| RET-B2 | `PATCH /locations/{id}/retire` | High | 📋 |
| RET-B3 | `PATCH /stations/{id}/retire` | High | 📋 |
| RET-B4 | `GET /admin/retired?type=&station_id=` | Medium | 📋 |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | High | 📋 |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | Medium | 📋 |

---

## 6. Backend — Loaned Item Endpoints
| # | Endpoint | Pri | Status |
|---|----------|-----|--------|
| LOAN-B1 | `POST /equipment/loans` | Medium | 📋 |
| LOAN-B2 | `PATCH /equipment/loans/{id}/resolve` | Medium | 📋 |
| LOAN-B3 | `GET /equipment/loans?vehicle_id=&resolved=false` | Medium | 📋 |
| LOAN-B4 | `GET /equipment/loans/my?resolved=false` | Medium | 📋 |

---

## 7. Frontend — Phase 5C: Help System
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5C1 | First-run tutorial — 8 steps | High | 📋 |
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | High | 📋 |
| F-5C3 | Searchable FAQ — 15 questions | Medium | 📋 |
| F-5C4 | `src/modules/help/content.js` | Medium | 📋 |

---

## 8. Frontend — Phase 5D: Item Management
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5D1 | Item catalog search component | Medium | 📋 |
| F-5D2 | Add item form | Medium | 📋 |
| F-5D3 | Remove item with mandatory reason | Medium | 📋 |

---

## 9. Frontend — V&E Status
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| VE-F2 | Open loans panel | Medium | 📋 | LOAN-B3 |
| VE-F3 | Log a loan form | Medium | 📋 | LOAN-B1 |
| VE-F4 | Resolve loan modal | Medium | 📋 | LOAN-B2 |

---

## 10. Frontend — Phase 5F: Supervisor Dashboard
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5F2 | Compliance calendar | High | ✅ Done | Session F Block 3 |
| F-5F6 | Notification bell | Medium | ⛔ | B-E12 |
| F-5F7 | Supply room stock view | Medium | 📋 | B-E6 |

---

## 11. Frontend — Phase 5G: Supporting Modules
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5G1 | Feedback module | Medium | 📋 |
| F-5G2 | User management module | Medium | ⛔ |
| F-5G3 | Data export — CSV | Medium | 📋 |
| F-5G4 | Role switcher (crew mode) | Low | 📋 |

---

## 12. Frontend — Check Wizard UX
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX2 | Left/right chevron navigation | Medium | 📋 | |
| F-UX3 | "Jump to unvalidated" sticky button | Medium | 📋 | |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 |
| F-UX6 | Compartment location descriptor | Medium | 📋 | |
| F-UX7 | **Last check banner** | High | ✅ Done | Session F Block 4 |
| F-UX8 | Item count on compartment cards | Low | 📋 | |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | |
| F-UX10 | "Caller/spotter view" large-text mode | Low | 📋 | |
| F-UX32 | BORROWED badge on loaned items | Medium | 📋 | B-M14 |
| F-UX34 | Second crew picker | Medium | ⛔ | B-M15, B-E7 |

---

## 13. Frontend — Check History (remaining)
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note | High | ⛔ | B-M10, CH-B8 |
| CH-F7 | Deleted records screen | High | 📋 | |
| CH-F8 | Force hard-delete confirmation | High | 📋 | |
| CH-F9 | "Checks I helped with" tab | Medium | ⛔ | B-M15, CH-B9 |

---

## 14. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F1 | Settings nav entry | High | 📋 | |
| S-F2 | Shared `ColorPickerWidget` | High | ✅ Done | Block 1 |
| S-F3 | Allow check modification toggle | High | 📋 | B-M10 |
| S-F4 | Default station selector | Medium | 📋 | B-M12 |
| S-F5 | Display name override | Low | 📋 | B-M12 |
| S-F6 | Station management | High | 📋 | RET-B3/B4 |
| S-F7 | Vehicle management | High | 📋 | RET-B1/B2 |
| S-F8 | Par level management | Medium | 📋 | B-E9 |
| S-F9 | User onboarding management | Medium | 📋 | B-E14/15 |

---

## 15. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle | High | 📋 | RET-B1 |
| RET-F2 | Retire jump bag / portable location | High | 📋 | RET-B2 |
| RET-F3 | Retire inventory lot | High | 📋 | RET-B5, B-M13 |
| RET-F4 | Retire station | High | 📋 | RET-B3 |
| RET-F5 | Retired objects list | Medium | 📋 | RET-B4 |

---

## 16. Infrastructure / Security
| # | Item | Pri | Status |
|---|------|-----|--------|
| I-1 | Azure Firewall | Medium | 📋 |
| I-2 | Re-add route table | Medium | ⛔ |
| I-3 | `HTTPSRedirectMiddleware` | Low | 📋 |
| I-5 | Document Azure AD token lifetime | Low | 📋 |
| I-6 | ADR-006-DDoS-Strategy.md | Low | 📋 |

---

## 17. Equipment & Station Administration (B-ADMIN1)

### Phase 2 — Vehicle & Location Management
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B11 | `POST /admin/vehicles` | High | ✅ Done | Implemented via `POST /api/v1/vehicles` in VehiclesScreen |
| ADMIN-B12 | `PATCH /admin/vehicles/{id}` | High | ✅ Done | OOS/RTS toggle + vehicle number/type edit (Session F + Block 3 UAT fixes) |
| ADMIN-B13 | `POST /admin/locations` | High | ✅ Done | `POST /inventory/locations` already supports JUMP_BAG creation (Supervisor+) |
| ADMIN-B14 | `PATCH /admin/locations/{id}` | High | 📋 | Needs label rename endpoint for portable locations |
| ADMIN-F6 | Vehicle list view per station | High | ✅ Done | VehiclesScreen — color, name/type edit, OOS/RTS, compartments |
| ADMIN-F7 | Portable location list view (Jump Bags) | High | 📋 | "Portable Equipment" card in admin hub → PortableLocationsScreen; list/add/manage JUMP_BAG locations and their compartments. Backend: `POST /inventory/locations` already exists. Frontend: new screen parallel to VehiclesScreen. |
| ADMIN-F10 | Member list search | Low | 📋 | |

### Phase 3 — Station Onboarding
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B15 | `POST /admin/stations` | Medium | ✅ Done | Block 2 |
| ADMIN-B16 | `POST /admin/stations/{id}/clone-layout` | Medium | 📋 | |
| ADMIN-UX1-F9 | "+ Add Station" form | Medium | ✅ Done | Block 2 |
| ADMIN-F8 | New station wizard | Medium | 📋 | |
| ADMIN-F9 | Layout clone picker | Medium | 📋 | |

---

## 18. Station Membership & Access Control

### Frontend
| # | Item | Pri | Status |
|---|------|-----|--------|
| ACC-F1 | Station picker uses `GET /stations/my` | High | 📋 |
| ACC-F2 | Member list view | High | 📋 |
| ACC-F3 | Add member form | High | 📋 |
| ACC-F4 | Remove member confirmation | High | 📋 |
| ACC-F5 | "Pending assignment" screen | High | 📋 |

---

## 20. User Acceptance Testing (UAT)
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-1 | Test case document | High | ✅ Done | Session F Block 6; `docs/uat_test_cases.md` |
| UAT-2 | Execute Responder test cases | High | 📋 | |
| UAT-3 | Execute Supervisor test cases | High | 📋 | |
| UAT-4 | Execute Administrator test cases | High | 📋 | |
| UAT-5 | Execute cross-role test cases | Medium | 📋 | |
| UAT-6 | Execute edge case test cases | Medium | 📋 | |
| UAT-7 | Pending assignment test case | High | ⛔ | Needs ACC-F5 |
| UAT-8 | Multi-station test case | Medium | ⛔ | Needs ACC-F1–F5 |

---

## 23. Station Supply Room & Restocking (SUPPLY)
| # | Item | Pri | Status |
|---|------|-----|--------|
| SUPPLY-M1 | `STATION_SUPPLY_ROOM` auto-created per station | High | 📋 |
| SUPPLY-B1 | `POST /inventory/transfer` | High | 📋 |
| SUPPLY-B2 | `GET /inventory/locations/{id}/stock-summary` | High | 📋 |
| SUPPLY-B3 | `GET /stations/{id}/supply-room` | High | 📋 |
| SUPPLY-F1 | Supply room stock view | High | 📋 |
| SUPPLY-F2 | Restock vehicle flow | High | 📋 |
| SUPPLY-F3 | Receive stock into supply room | Medium | 📋 |
| SUPPLY-F4 | Transfer history | Medium | 📋 |

---

## 24. Par Level Assignment UI (ADMIN-F4)
*All items complete — Session F Block 5.*

| # | Item | Pri | Status |
|---|------|-----|--------|
| ADMIN-F4a | Par level list on item card | High | ✅ Done |
| ADMIN-F4b | "Assign to Vehicle" flow | High | ✅ Done |
| ADMIN-F4c | Edit/remove par level | High | ✅ Done |
| ADMIN-B6 | `POST /admin/items/{id}/assign` | High | ✅ Done |
| ADMIN-B7 | `PATCH /admin/par-levels/{id}` | High | ✅ Done |
| ADMIN-B8 | `PATCH /admin/par-levels/{id}/deactivate` | High | ✅ Done |

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
| Q-7 | Check modification setting default: False or True? | Project owner |
| Q-8 | Restored soft-deleted checks: responder history or admin screen only? | Project owner |
| Q-9 | 5-year hard-delete job: share with Q-6 or separate? | Engineering |
| Q-10 | Second crew lookup: MS Graph or local user list? | Engineering |
| Q-11 | Should a FAIL check auto-suggest a restock? | Project owner |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Security — remaining | 1 | 1 | 2 |
| Backend — Phase 6 Endpoints | 12 | 0 | 12 |
| Backend — Data Models | 14 | 0 | 14 |
| Backend — Check History | 5 | 1 | 6 |
| Backend — Retirement | 6 | 0 | 6 |
| Backend — Loaned Items | 4 | 0 | 4 |
| Frontend — Phase 5C Help | 4 | 0 | 4 |
| Frontend — Phase 5D Item Mgmt | 3 | 0 | 3 |
| Frontend — V&E Status | 3 | 0 | 3 |
| Frontend — Phase 5F Supervisor | 1 | 1 | 2 |
| Frontend — Phase 5G Supporting | 3 | 1 | 4 |
| Frontend — Check Wizard UX | 8 | 3 | 11 |
| Frontend — Check History remaining | 3 | 1 | 4 |
| Frontend — Settings | 8 | 0 | 8 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Infrastructure / Security | 4 | 1 | 5 |
| Equipment & Station Admin | 9 | 0 | 9 |
| Station Membership Frontend | 5 | 0 | 5 |
| User Acceptance Testing | 6 | 2 | 8 |
| Station Supply Room & Restocking | 8 | 0 | 8 |
| **Total open** | **111** | **11** | **122** |

*Session F complete — Blocks 1–6 all done.*
*Completed items — Sessions A–F — are in backlog_completed.md.*
