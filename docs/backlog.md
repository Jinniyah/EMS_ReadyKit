# EMS ReadyKit — Active Backlog
# v1.70 | Updated: 2026-06-09 | Current: Post-session L complete + frontend test suite
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–L complete — see backlog_completed.md

---

## LAUNCH PHILOSOPHY (established 2026-06-04)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## Launch gate criteria — ALL must be met before any user sees the app:
##   ✓ Check wizard redesign complete (No Change / Modify / Priority Items)
##   ✓ After-call reset flow complete
##   ✓ Damaged item marking complete
##   ✓ First-run tutorial complete (3-screen minimum)
##   ✓ All responder-facing language plain English (no jargon, no technical errors)
##   ✓ Open repair count visible on compliance dashboard
##   ✓ Vehicle + location retirement actions complete
##   ✓ Priority items configured in admin for Unit 712 (AED, LUCAS, O2, Truck Ops)
##   ✓ UAT executed against live Azure deployment with real Unit 712 inventory
##   ✓ Physical stock count entered for Unit 712 (not seed quantities — actual counts)
##   ✓ All tests passing (349 tests green — Session L post-close)
##   ✓ Code cleanup complete (dead files deleted, CSS consolidated)

---

## UPCOMING SESSIONS
##
## Session M — UX Redesign + Pre-launch Fixes (~5 hrs)
##   SEED-GAP2    requires_full_check enforcement in router (clears xfail)  ~30 min
##   RX-B2        PATCH /admin/par-levels/{id} priority_check/question      ~20 min
##   RX-F12       Priority toggle + question in par level edit form (Admin)  ~45 min
##   RX-F3        Collapse Step 1 for single-station users                   ~30 min
##   RX-F4        Simplify Step 5 for clean PASS checks                      ~30 min
##   RX-F5        Restock list persists on SubmittedScreen                   ~20 min
##   RX-F9b       Priority "last confirmed" display                          ~30 min
##   RX-F10       Responder-facing language + error message replacement      ~60 min
##   SUP-F1        Open repair count on compliance dashboard                 ~20 min
##   SUP-F2        Repair count drill-down to V&E Status                     ~15 min
##   DMG-F3        Damaged item badge in supply room View Supplies           ~20 min
##
## Session N — After-Call Reset + Tutorial (~4 hrs)
##   RX-B1        POST /checks/usage                                  ~45 min
##   RX-F6        After-Call Reset flow — recents + search            ~90 min
##   RX-F11       First-run tutorial — 3 screens on first login       ~60 min
##
## Session O — Dashboard + Station Admin (~4 hrs)
##   SUP-F3       Expiring items alert on compliance dashboard        ~45 min
##   B-M10        Migration: allow_check_modification on stations     ~20 min
##   CH-B7/B8     Station settings GET/PATCH endpoints                ~30 min
##   ADMIN-B14    PATCH /admin/locations/{id} (label rename)          ~20 min
##   ADMIN-F7     Portable location list view (Jump Bags) in Admin    ~45 min
##   ACC-F1-F5    Station membership frontend                         ~60 min
##
## Session P — Retirement + Settings (~4 hrs)
##   RET-M1-M3    Migrations: retired_at/by/reason                    ~30 min
##   RET-B1-B6    Retire vehicle/location/station endpoints           ~60 min
##   RET-F1-F5    Retire actions in UI                                ~60 min
##   S-F1/F3/F6/F7/F8  Settings module                                ~90 min
##   I-3          HTTPSRedirectMiddleware (3 lines)                   ~10 min
##   SEC-OPS1     Monthly dependency audit workflow                   ~20 min
##
## Session Q — UAT Dress Rehearsal + Launch
##   LAUNCH-OPS1–9  Operational checklist
##   UAT-2–11       Execute all test cases

---

## 0. Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-3 | `HTTPSRedirectMiddleware` in `main.py` | Low | 📋 | Azure App Service enforces HTTPS at platform level. Application-layer enforcement is defence-in-depth. Three lines in main.py. Session P. |
| SEC-OPS1 | Scheduled monthly dependency audit workflow | Low | 📋 | `.github/workflows/dependency-audit.yml` — runs pip-audit + npm audit on first of each month, opens GitHub issue on findings above moderate. Session P. |

---

## 1. Workflow Acceleration — Check Wizard

### Interaction redesign
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F3 | Collapse Step 1 for single-station users | High | 📋 | Session M. Single-station: vehicle picker + "Continue" only. Date and second crew collapse into a disclosure — "Change date or add crew member". Open by default only if date != today or draft has second crew. |
| RX-F4 | Simplify Step 5 for clean PASS checks | High | 📋 | Session M. PASS: status badge + single "Submit — Unit 712" button. No compartment re-review, no repair toggle, no notes field, no confirmation modal. Repair toggle and notes appear only on NEEDS_RESTOCK or FAIL. |
| RX-F5 | Restock list persists on SubmittedScreen | High | 📋 | Session M. On NEEDS_RESTOCK: "View restock list" button on SubmittedScreen opens read-only reconcile summary. Currently the list disappears after submission. |

### Priority items
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F9b | Priority item "last confirmed" display | Medium | 📋 | Session M. "Last confirmed ready: [date] · [N] days ago" below each priority item. Pulls from most recent PASS line item for that item on that vehicle. Amber if > threshold days (7 amber / 14 red — Q-15 resolved). |
| RX-B2 | `PATCH /admin/par-levels/{id}` — accept priority_check + priority_question | High | 📋 | Session M. Verify or extend: endpoint must accept `priority_check` (bool) and `priority_question` (VARCHAR 150). Migration 0015 added these columns. Admin+ only. Uses `write_audit_event()`. ~20 min |
| RX-F12 | Priority toggle + question in par level edit form (Admin) | High | 📋 | Session M. In `CompartmentParLevels.jsx`: add **"Show as priority at start of check"** toggle and conditional **"Custom check question"** text field (max 150 chars, appears when toggle is on). Save via RX-B2. Gap from SEED-GAP3 — DB columns exist since migration 0015, UI was never built. ~45 min |

### After-Call Reset
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F6 | After-Call Reset flow — recents + search | Critical | 📋 | Session N. Home screen "Log Items Used." Auto-selects truck if only one. Shows last 8-10 items by frequency + search. +/− controls per item. "Done" commits. Target: ≤3 taps for 2-3 item case. |
| RX-B1 | `POST /checks/usage` — lightweight usage record | Critical | 📋 | Session N. Uses DailyInventoryCheck (Q-11 resolved — reuse existing model). Auto-decrements stock lots FIFO (Q-12 resolved). Accepts: vehicle_id, station_id, timestamp, [{item_id, compartment_id, quantity_used}]. |

### Responder language + error messages
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F10 | Responder-facing language + error message replacement | Critical | 📋 | Session M. Display strings only. Jargon replacements: "Par level" → "Stock: N / N", "Reconcile" → "Restock list", "Functional check" → custom question text, "Date record" → "Expiration date", "NEEDS_RESTOCK" → "Restock needed", "FAIL" → "Problem found", "Measurement" → "Reading", "Repair request" → "Report a problem". Error replacements: 401 → "Your session expired. Sign out and sign back in.", 403 → "You don't have permission to do that. Ask your supervisor if something seems wrong." No HTTP codes or server terminology visible to responders ever. |

### First-run tutorial
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F11 | First-run tutorial — 3 screens on first login | Critical | 📋 | Session N. Shown exactly once. localStorage flag `ems_tutorial_complete`. Three screens: (1) Home — Check the Truck vs Log Items Used. (2) Check flow — No Change vs Modify vs priority items. (3) After-call — Log Items Used. Each: large text, one illustration, "Got it" button. Skip on screen 1 only. 60px tap targets throughout. |

---

## 2. Damaged Item Status
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| DMG-F3 | Damaged item visibility in supply room | Medium | 📋 | Session M. View Supplies shows damaged items with ⚠ badge. Damaged items excluded from restock suggestions — repair first. |

---

## 3. Supervisor Dashboard Enhancements
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SUP-F1 | Open repair count on compliance dashboard | Critical | 📋 | Session M. "N open repair requests" count line. Tap navigates to V&E Status. Hidden if zero. No new API call. |
| SUP-F2 | Repair count drill-down to V&E Status | High | 📋 | Session M. Tap navigates to V&E Status filtered to open/in-progress. Uses existing onNavigateToVehicles prop. |
| SUP-F3 | Expiring items alert on compliance dashboard | High | 📋 | Session O. Query stock_lots expiring within 30 days. Show count in dashboard header. Tap opens list grouped by vehicle: item name, lot number, expiry date, compartment. Amber at 30 days, red at 7 days. No new migration — expiration_date already on StockLot. |

---

## 4. AI Item Identification — Groundwork
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| AI-B1 | `PATCH /admin/items/{id}/ai-fields` | High | 📋 | Admin-only. Sets ai_tags, alternate_names, reference_image_url, barcode. Fields exist in DB since migration 0009. |
| AI-F1 | AI fields editor in Item admin screen | High | 📋 | Collapsible "AI Identification" section in ItemForm.jsx (collapsed by default, admin only). Barcode, alternate names, reference image URL, AI tags. Save via AI-B1. |
| AI-F2 | Barcode search in After-Call Reset | Medium | 📋 | Post-launch. Camera barcode scan → item lookup in RX-F6. Graceful text search fallback. |
| AI-F3 | Barcode search in supply room receive | Medium | 📋 | Post-launch. Scan barcode to identify item being received. |

---

## 5. Seed Data Gaps — Unit 712
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEED-GAP2 | Truck Operations — requires_full_check=True enforcement | High | 📋 | Session M. Implement enforcement in router (clears xfail in test_safety_checks.py). Also set `requires_full_check=True` on Truck Operations compartment in seed.py. Q-16 resolved: compartment-level flag. |
| SEED-GAP4 | O2 PSI items — priority consideration | Medium | 📋 | "On-Board O2 PSI" (DS EC 1) and "Stretcher O2 PSI" — both min 500 PSI. Chief decides whether to mark priority. Stretcher O2 likely priority. |
| SEED-GAP5 | Jump bag O2 PSI priority consideration | Low | 📋 | "Jump Bag O2 PSI" MEASUREMENT item. Same priority decision as SEED-GAP4. |

---

## 6. Launch Readiness — Operational Checklist
| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 in production admin | EMS chief | 📋 | After RX-F12 ships: Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device Ready Check, O2 PSI items as priority. Set custom question text. |
| LAUNCH-OPS2 | Enter actual physical stock count for Unit 712 | EMS chief | 📋 | Seed has par levels (targets) not actual counts. Do physical count before UAT. |
| LAUNCH-OPS3 | Enter actual stock count for Unit 712 Jump Bag | EMS chief | 📋 | Unit 710 Jump Bag removed from seed until Unit 710 ambulance is configured. |
| LAUNCH-OPS4 | Add all EMS team members in admin | EMS chief | 📋 | ~10 team members need Azure AD login + station member assignment with correct role. |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | EMS chief | 📋 | Complete check in production. Every compartment. Priority items. Truck Operations. Submit. Verify compliance dashboard reflects it. |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | Volunteer | 📋 | One less tech-comfortable volunteer runs a complete check cold. Observe without helping. Questions = UX issues. |
| LAUNCH-OPS7 | Marcellus Township — NOT in initial launch | — | N/A | Q-19 resolved: Newberg Township only at launch. |
| LAUNCH-OPS8 | Remove TEST STATION from production | Engineering | 📋 | `SEED_TEST_DATA=false` env var check in seed.py. Q-18 resolved: env var approach. |
| LAUNCH-OPS9 | Verify Azure AD user emails match station member emails | Engineering | 📋 | StationMember.user_id keyed on email. Mismatch = "not listed" error on first login. Verify before launch day. |

---

## 7. Backend — Endpoints
| # | Endpoint | Description | Pri | Status |
|---|----------|-------------|-----|--------|
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 |

---

## 8. Backend — Data Models
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 | |
| B-M10 | Alter `stations`: add `allow_check_modification` (default True — Q-7 resolved) | High | 📋 | Session O. |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | Session P. |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | Session P. |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | Session P. |

---

## 9. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Force hard-delete | High | 📋 | Admin only. Post-launch. |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks | Medium | 📋 | Supervisor+. Post-launch. |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted (Q-8: all roles) | Low | 📋 | Post-launch. |
| CH-B7 | `PATCH /stations/{id}/settings` | Update station settings | High | 📋 | Admin only. Session O. |
| CH-B8 | `GET /stations/{id}/settings` | Read station settings | High | 📋 | Supervisor+. Session O. |

---

## 10. Backend — Retirement Endpoints
| # | Endpoint | Pri | Status |
|---|----------|-----|--------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | High | 📋 | Session P. |
| RET-B2 | `PATCH /locations/{id}/retire` | High | 📋 | Session P. |
| RET-B3 | `PATCH /stations/{id}/retire` | High | 📋 | Session P. |
| RET-B4 | `GET /admin/retired?type=&station_id=` | Medium | 📋 | Session P. |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | High | 📋 | Session P. |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | Medium | 📋 | Session P. |

---

## 11. Frontend — Help System
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | Medium | 📋 | Post-launch. Based on what questions the team actually asks after first month. |

---

## 12. Frontend — Supervisor Dashboard
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5F7 | Supply room stock view on dashboard | Medium | 📋 | Post-launch enhancement |

---

## 13. Frontend — Supporting Modules
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5G3 | Data export — CSV for history, audit, repairs | Medium | 📋 | Q-3 answered: yes, download history. When first compliance report is due. |

---

## 14. Frontend — Check Wizard UX
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX10 | Scroll-to-card on return from compartment item list | Low | 📋 | Sticky button handles the common case. Revisit post-launch if team finds it insufficient. ~30 min |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 (started_by field) — post-launch |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | Already in seed data, just needs display |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | Post-launch |

---

## 15. Frontend — Check History
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note | High | ⛔ | B-M10, CH-B8 |

---

## 16. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F1 | Settings nav entry | High | 📋 | Session P. |
| S-F3 | Allow check modification toggle (default True) | High | 📋 | Session P. Needs B-M10. |
| S-F6 | Station management | High | 📋 | Session P. Needs RET-B3/B4. |
| S-F7 | Vehicle management | High | 📋 | Session P. Needs RET-B1/B2. |
| S-F8 | Par level management | Medium | 📋 | Session P. Needs B-E9. |

---

## 17. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle | High | 📋 | Session P. Needs RET-B1. |
| RET-F2 | Retire jump bag / portable location | High | 📋 | Session P. Needs RET-B2. |
| RET-F3 | Retire inventory lot | High | 📋 | Session P. Needs RET-B5. |
| RET-F4 | Retire station | High | 📋 | Session P. Needs RET-B3. |
| RET-F5 | Retired objects list | Medium | 📋 | Session P. Needs RET-B4. |

---

## 18. Infrastructure / Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall | Medium | 📋 | Before scaling to second service |
| I-2 | Re-add route table | Medium | ⛔ | |
| I-5 | Document Azure AD token lifetime | Low | 📋 | |
| PERF-1 | Batch N+1 in `_auto_decrement_supply_room` | Low | 📋 | One query for all items instead of one per item. Not urgent at 5 calls/week. |
| TECH-1 | `pytest-cov` coverage reporting | Low | 📋 | One-line addition to pyproject.toml. Enables accurate coverage badge. |
| TECH-2 | React Query for frontend data management | Low | 📋 | Post-launch refactor. Eliminates manual useEffect+useState pattern; adds background refetch, request deduplication, cache invalidation. |
| TECH-3 | Offline submission queue (F-UX9) | Low | 📋 | IndexedDB queue retries on reconnect. Critical for basement/low-signal scenarios. |

---

## 19. Equipment & Station Administration
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B14 | `PATCH /admin/locations/{id}` | High | 📋 | Session O. Label rename for portable locations. |
| ADMIN-F7 | Portable location list view (Jump Bags) | High | 📋 | Session O. |
| ADMIN-F10 | Member list search | Low | 📋 | Post-launch. |

---

## 20. Station Membership & Access Control
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-F1 | Station picker uses `GET /stations/my` | High | 📋 | Session O. |
| ACC-F2 | Member list view | High | 📋 | Session O. |
| ACC-F3 | Add member form | High | 📋 | Session O. |
| ACC-F4 | Remove member confirmation | High | 📋 | Session O. |
| ACC-F5 | "Pending assignment" screen | High | 📋 | Session O. |

---


## 22. User Acceptance Testing
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-2 | Execute Responder test cases | High | 📋 | Against live Azure, real Unit 712 data |
| UAT-3 | Execute Supervisor test cases | High | 📋 | Chief logged in as Supervisor |
| UAT-4 | Execute Administrator test cases | High | 📋 | |
| UAT-5 | Execute cross-role test cases | Medium | 📋 | |
| UAT-6 | Execute edge case test cases | Medium | 📋 | |
| UAT-7 | Pending assignment test case | High | ⛔ | Needs ACC-F5 |
| UAT-8 | Multi-station test case | Medium | ⛔ | Needs ACC-F1-F5 |
| UAT-9 | Unit 712 full shift-start check — cold run | Critical | 📋 | Chief + one volunteer, no coaching, production. Pass: zero calls for help, check submitted, dashboard reflects it. |
| UAT-10 | After-call usage log — cold run | Critical | 📋 | Log 2-3 items used. Verify restock list updates. Pass: completed in under 60 seconds without explanation. |
| UAT-11 | Damaged item scenario — cold run | High | 📋 | Simulate discovering a damaged item during UAT-9. Verify in-context path, repair request created, chief sees it on dashboard. |

---

## 23. Open Questions
| # | Question | Notes |
|---|----------|-------|
| Q-3 | Download check history CSV? | Yes — add to F-5G3 scope when first compliance report is due |
| Q-6 | Auto-hard-delete: Azure Function | Resolved: Azure Function (Q-6 answered) |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Security | 2 | 0 | 2 |
| Workflow — Check Wizard | 3 | 0 | 3 |
| Workflow — Priority Items | 3 | 0 | 3 |
| Workflow — After-Call Reset | 2 | 0 | 2 |
| Workflow — Language + Errors | 1 | 0 | 1 |
| Workflow — Tutorial | 1 | 0 | 1 |
| Damaged Item Status | 1 | 0 | 1 |
| Supervisor Dashboard | 3 | 0 | 3 |
| AI Identification — Groundwork | 4 | 0 | 4 |
| Seed Data Gaps — Unit 712 | 3 | 0 | 3 |
| Launch Readiness — Operational | 8 | 0 | 8 |
| Backend — Endpoints | 2 | 0 | 2 |
| Backend — Data Models | 5 | 0 | 5 |
| Backend — Check History | 5 | 0 | 5 |
| Backend — Retirement | 6 | 0 | 6 |
| Frontend — Help System | 1 | 0 | 1 |
| Frontend — Supervisor Dashboard | 1 | 0 | 1 |
| Frontend — Supporting Modules | 1 | 0 | 1 |
| Frontend — Check Wizard UX | 4 | 1 | 5 |
| Frontend — Check History | 1 | 1 | 2 |
| Frontend — Settings | 5 | 0 | 5 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Infrastructure / Security | 1 | 1 | 2 |
| Equipment & Station Admin | 3 | 0 | 3 |
| Station Membership Frontend | 5 | 0 | 5 |
| User Acceptance Testing | 9 | 2 | 11 |
| **Total open** | **85** | **5** | **90** |

*Completed items — Sessions A–K — are in backlog_completed.md.*
*v1.62 — 2026-06-06: Backlog cleaned. All ✅ Done items moved to backlog_completed.md.*
*v1.63 — 2026-06-06: Session K complete. Supply Room Redesign (14 items) moved to completed.*
*v1.64 — 2026-06-06: Session K post-close. Migration 0018 fix + supply room setup endpoint + graceful 404 handling + initial_stock.csv.*
*v1.65 — 2026-06-08: Session L complete. Automated test suite: 3 persona files + priority items suite. 304 tests passing. See backlog_completed.md for TEST-* items.*
*v1.66 — 2026-06-08: Seed fix — removed orphan Unit 710 Jump Bag from Newberg Township. Unit 710 has no ambulance seeded; its jump bag was appearing as an orphan in the check wizard Step 1 picker. Unit 712 Jump Bag remains. LAUNCH-OPS3 updated when Unit 710 ambulance is eventually seeded.*
*v1.67 — 2026-06-08: Session L post-close. Safety + seed integrity tests: test_seed_integrity.py (32 tests against seeded dev DB via seeded_db fixture), test_safety_checks.py (13 tests + 1 xfail documenting requires_full_check enforcement gap). Total: 349 passed, 1 xfailed.*
*v1.68 — 2026-06-09: Security/performance improvements partially implemented. Completed: slowapi rate limiting wired (core/limiter.py, main.py), check_date server-derived from timestamp, performed_by uses email, check_history.py ownership checks updated. In progress: test suite broken (60 failures) due to rate limiter firing in tests + conftest/limiter interaction. Continuing in new chat. New backlog items added: PERF-1, PERF-2, TECH-1, TECH-2, TECH-3.*
*v1.69 — 2026-06-09: Post-session L complete. Tests green (349 passed, 1 xfailed). RATE-FIX done; RATE-CI (ruff in CI), RATE-MIG/PERF-2 (migration 0019 + model), RATE-DOCS (CLAUDE.md) all implemented and moved to completed. Session plan expanded: M–Q now covers all pre-launch items with session labels.*
*v1.70 — 2026-06-09: Frontend test suite complete. Vitest + React Testing Library: 10 component test files + MSAL mocks. Covers check wizard, supervisor dashboard, vehicles, admin, check history, and all shared utilities. Role-gating regression (Session J canAccess 'admin' alias) now has automated coverage. No backend changes.*
