# EMS ReadyKit — Active Backlog
# v1.86 | Updated: 2026-06-12 | Session V complete — Administrator + Supervisor UAT passed
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–V complete — see backlog_completed.md

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
##   ✓ All tests passing
##   ✓ Code cleanup complete (dead files deleted, CSS consolidated)

---

## NEXT STEPS
## Remaining UAT: UAT-2 (Responder), UAT-5-8 (cross-role/edge cases)
## Then: LAUNCH-OPS1–9 operational checklist before go-live

---

## 1. AI Item Identification — Groundwork
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| AI-F2 | Barcode search in After-Call Reset | Medium | 📋 | Post-launch. Camera barcode scan → item lookup in RX-F6. Graceful text search fallback. |
| AI-F3 | Barcode search in supply room receive | Medium | 📋 | Post-launch. Scan barcode to identify item being received. |

---

## 2. Seed Data Gaps — Unit 712
*(All seed gaps resolved — moved to backlog_completed.md)*

---

## 3. Launch Readiness — Operational Checklist
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

## 4. Backend — Endpoints

| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| USAGE-B1 | `POST /checks/usage` — fix stock decrement | High | 📋 | **Bug:** usage logging currently decrements station supply room immediately, which is wrong. Items are consumed from the vehicle/jump bag, not the supply room. Fix: (1) remove `_decrement_supply_room_fifo()` call from `create_usage_event` in `usage.py` — supply room only decrements during check wizard reconcile (SR-B4, already correct). (2) `get_last_readings` in `checks.py` must subtract post-check usage events from `quantity_found` so the check wizard pre-fills correctly and flags shortages. Formula: `effective_qty = last_check.quantity_found - sum(UsageEventItems for this vehicle/location+item since last check timestamp)`. Never goes below 0. Edge case: no prior check → usage events are audit-only, no quantity effect. |
| USAGE-B2 | `POST /checks/usage` — add location_id support | High | 📋 | **Gap:** `UsageEvent` model has `vehicle_id` but no `location_id`. Jump bag usage cannot be logged against a portable location. Fix requires: (1) migration to add nullable `location_id` FK on `usage_events` table; (2) `UsageEventCreate` schema to accept either `vehicle_id` or `location_id` (exactly one required, validated); (3) `get_last_readings` already accepts `location_id` param — the usage subtraction logic (USAGE-B1) must also handle location-scoped queries; (4) update usage history and frequent-items endpoints to filter by location when relevant. Depends on USAGE-B1 being done first. |

---

## 5. Backend — Data Models

*(B-M6 implemented — see backlog_completed.md)*

---

## 6. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Force hard-delete | High | 📋 | Admin only. Post-launch. |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks | Medium | 📋 | Supervisor+. Post-launch. |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted (Q-8: all roles) | Low | 📋 | Post-launch. |

---

## 8. Frontend — Help System
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | Medium | 📋 | Post-launch. Based on what questions the team actually asks after first month. |

---

## 9. Frontend — Supervisor Dashboard
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5F7 | Supply room stock view on dashboard | Medium | 📋 | Post-launch enhancement |

---

## 10. Frontend — Supporting Modules
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5G3 | Data export — CSV for history, audit, repairs | Medium | 📋 | Q-3 answered: yes, download history. When first compliance report is due. |

---

## 11. Frontend — Check Wizard UX
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX10 | Scroll-to-card on return from compartment item list | Low | 📋 | Post-launch. Sticky button handles the common case. Revisit if team finds it insufficient. |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 (started_by field) — post-launch |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | Post-launch |

---

## 16. Infrastructure / Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall | Medium | 📋 | Post-launch. Before scaling to second service. |
| I-2 | Re-add route table | Medium | ⛔ | |
| TECH-2 | React Query for frontend data management | Low | 📋 | Post-launch refactor. Eliminates manual useEffect+useState pattern; adds background refetch, request deduplication, cache invalidation. |
| TECH-3 | Offline submission queue (F-UX9) | Low | 📋 | Post-launch. IndexedDB queue retries on reconnect. Critical for basement/low-signal scenarios. |

---

## 17. Equipment & Station Administration
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-F10 | Member list search | Low | 📋 | Post-launch. |

---

## 18. User Acceptance Testing
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-2 | Execute Responder test cases | High | 📋 | Against live Azure, real Unit 712 data |
| UAT-3 | Execute Supervisor test cases | High | ✅ | Passed — 2026-06-12 |
| UAT-4 | Execute Administrator test cases | High | ✅ | Passed — 2026-06-12 |
| UAT-5 | Execute cross-role test cases | Medium | 📋 | |
| UAT-6 | Execute edge case test cases | Medium | 📋 | |
| UAT-7 | Pending assignment test case | High | 📋 | |
| UAT-8 | Multi-station test case | Medium | 📋 | |
| UAT-9 | Unit 712 full shift-start check — cold run | Critical | 📋 | Chief + one volunteer, no coaching, production. Pass: zero calls for help, check submitted, dashboard reflects it. |
| UAT-10 | After-call usage log — cold run | Critical | 📋 | Log 2-3 items used on vehicle AND jump bag. Verify: (1) no supply room stock change at time of logging; (2) next check wizard pre-fills flagged short for those items; (3) compliance dashboard shows restock needed. Pass: under 60 seconds without explanation. Blocked on USAGE-B1 + USAGE-B2. |
| UAT-11 | Damaged item scenario — cold run | High | 📋 | Simulate discovering a damaged item during UAT-9. Verify in-context path, repair request created, chief sees it on dashboard. |

---

## 19. Code Quality / Refactoring
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| CQ-F1 | `check-wizard/index.jsx` — `useReducer` refactor | Low | 📋 | Post-launch. 18 `useState` calls → `useReducer`. Group `submitted*` fields as a single `submissionResult` object. No functional change. |
| CQ-B4 | Inline Pydantic schemas → `schemas/` | Low | 📋 | Post-launch. `LastReadingItem` in `checks.py` and `_ItemStatusPatch` in `inventory.py` belong in `schemas/checks.py` and `schemas/inventory.py`. |
| CQ-B5 | `admin.py` (30KB) — split into sub-routers | Low | 📋 | Post-launch. Split into `admin_items.py`, `admin_vehicles.py`, `admin_stations.py`. Also flagged in CODEBASE_INDEX debt table. |
| CQ-B6 | `check_date` column: `String(10)` → `Date` type | Low | 📋 | Post-launch. Requires migration. ISO string comparison works but loses type safety. Range queries become proper date comparisons. |
| CQ-B7 | `create_par_level` duplicate conflict check | Low | 📋 | Post-launch. Function pre-queries for an existing par level then also catches `IntegrityError` for the same condition. Remove the pre-check and rely on the DB constraint + `IntegrityError` handler. |

---

## 20. Open Questions
| # | Question | Notes |
|---|----------|-------|
| Q-3 | Download check history CSV? | Yes — add to F-5G3 scope when first compliance report is due |
| Q-6 | Auto-hard-delete: Azure Function | Resolved: Azure Function (Q-6 answered) |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| AI Identification — Groundwork | 2 | 0 | 2 |
| Launch Readiness — Operational | 8 | 0 | 8 |
| Backend — Endpoints | 2 | 0 | 2 |
| Backend — Check History | 3 | 0 | 3 |
| Frontend — Help System | 1 | 0 | 1 |
| Frontend — Supervisor Dashboard | 1 | 0 | 1 |
| Frontend — Supporting Modules | 1 | 0 | 1 |
| Frontend — Check Wizard UX | 2 | 1 | 3 |
| Infrastructure / Security | 2 | 1 | 3 |
| Equipment & Station Admin | 1 | 0 | 1 |
| Code Quality / Refactoring | 5 | 0 | 5 |
| User Acceptance Testing | 8 | 0 | 8 |
| **Total open** | **36** | **2** | **38** |

*v1.86 — 2026-06-12: Session V complete. Administrator and Supervisor UAT passed. Four bugs found and fixed: UAT-BUG4 (progress bar showed "Vehicle" for supply room checks — WizardProgress selectionLabel prop added); UAT-BUG5 ("This check" as check subject — selection_label added to initialDraft in HomePage); UAT-BUG6 (check date blank — todayIso() fallback added to Step5Submit); UAT-BUG7 (supply room check did not update View Supplies — architectural gap: _reconcile_supply_room_check (SR-B5) added to checks.py, called on STATION_SUPPLY_ROOM submissions, FIFO reconciles quantity_found back to StockLot quantities). UAT-4 complete.*
*v1.85 — 2026-06-12: Session U complete. Supervisor UAT passed. Bugs found and fixed: Log Items Used showed no ambulance buttons (v.status === 'ACTIVE' → v.active === true; also fixed in test fixtures); No Change bypassed Reconcile when items were short (quantity_found used pl.min_quantity instead of lastQtyMap — shortages were silently buried); test_usage.py flaky unique constraint failure (id(station) → uuid4().hex[:12] in _make_setup). CLAUDE.md updated: filesystem:edit_file permanently banned; vehicle API shape documented. 418 tests passing, 201 npm tests passing.*
*v1.84 — 2026-06-12: Session U UAT in progress. Bugs found and fixed: SUP-DMG-FIX1 (FAIL banner persisted after repair resolved), SUP-DMG1 (damaged items not surfaced on compliance dashboard — new endpoint + frontend panel + 13 tests, 410 passing). New backlog: USAGE-B1, USAGE-B2. UAT-10 acceptance criteria updated.*
*v1.83 — 2026-06-12: Session U started. UAT Dress Rehearsal underway.*
