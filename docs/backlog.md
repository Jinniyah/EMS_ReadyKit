# EMS ReadyKit — Active Backlog
# v1.77 | Updated: 2026-06-10 | Current: Post-session Q complete
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–Q complete — see backlog_completed.md

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
##   ✓ All tests passing (368 tests green — Session Q post-close)
##   ✓ Code cleanup complete (dead files deleted, CSS consolidated)

---

## UPCOMING SESSIONS
##
## Session N — COMPLETE (2026-06-10)
##   RX-B1/RX-F6/RX-F11 done — see backlog_completed.md
##
## Session O — COMPLETE (2026-06-10)
##   SEED-GAP2/RX-F3/RX-F4/RX-F5/RX-F9b/RX-F10/RX-F13/SUP-F1/SUP-F2 done — see backlog_completed.md
##
## Session P — COMPLETE (2026-06-10)
##   RX-B2/RX-F12/DMG-F3/SS-B1/SS-F1/SS-F2/ADMIN-F7/SUP-F3 done — see backlog_completed.md
##
## Session Q — COMPLETE (2026-06-10)
##   B-M10/CH-B7/CH-B8/ACC-F1-F5/S-F1/S-F3 done — see backlog_completed.md
##
## Session R — Retirement + Security (~4 hrs)
##   RET-M1-M3    Migrations: retired_at/by/reason                          ~30 min
##   RET-B1-B6    Retire vehicle/location/station endpoints                  ~60 min
##   RET-F1-F5    Retire actions in UI                                       ~60 min
##   S-F6/F7/F8   Station/vehicle/par level management in Settings           ~60 min
##   I-3          HTTPSRedirectMiddleware (3 lines)                          ~10 min
##   SEC-OPS1     Monthly dependency audit workflow                          ~20 min
##
## Session S — UAT Dress Rehearsal + Launch
##   LAUNCH-OPS1–9  Operational checklist
##   UAT-2–11       Execute all test cases

---

## 0. Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-3 | `HTTPSRedirectMiddleware` in `main.py` | Low | 📋 | Azure App Service enforces HTTPS at platform level. Application-layer enforcement is defence-in-depth. Three lines in main.py. Session R. |
| SEC-OPS1 | Scheduled monthly dependency audit workflow | Low | 📋 | `.github/workflows/dependency-audit.yml` — runs pip-audit + npm audit on first of each month, opens GitHub issue on findings above moderate. Session R. |

---

## 1. AI Item Identification — Groundwork
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| AI-B1 | `PATCH /admin/items/{id}/ai-fields` | High | 📋 | Admin-only. Sets ai_tags, alternate_names, reference_image_url, barcode. Fields exist in DB since migration 0009. |
| AI-F1 | AI fields editor in Item admin screen | High | 📋 | Collapsible "AI Identification" section in ItemForm.jsx (collapsed by default, admin only). Barcode, alternate names, reference image URL, AI tags. Save via AI-B1. |
| AI-F2 | Barcode search in After-Call Reset | Medium | 📋 | Post-launch. Camera barcode scan → item lookup in RX-F6. Graceful text search fallback. |
| AI-F3 | Barcode search in supply room receive | Medium | 📋 | Post-launch. Scan barcode to identify item being received. |

---

## 2. Seed Data Gaps — Unit 712
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEED-GAP4 | O2 PSI items — priority consideration | Medium | 📋 | "On-Board O2 PSI" (DS EC 1) and "Stretcher O2 PSI" — both min 500 PSI. Chief decides whether to mark priority. Stretcher O2 likely priority. |
| SEED-GAP5 | Jump bag O2 PSI priority consideration | Low | 📋 | "Jump Bag O2 PSI" MEASUREMENT item. Same priority decision as SEED-GAP4. |

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
| # | Endpoint | Description | Pri | Status |
|---|----------|-------------|-----|--------|
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 |

---

## 5. Backend — Data Models
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 | |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | Session R. |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | Session R. |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | Session R. |

---

## 6. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Force hard-delete | High | 📋 | Admin only. Post-launch. |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks | Medium | 📋 | Supervisor+. Post-launch. |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted (Q-8: all roles) | Low | 📋 | Post-launch. |

---

## 7. Backend — Retirement Endpoints
| # | Endpoint | Pri | Status | Notes |
|---|----------|-----|--------|-------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | High | 📋 | Session R. |
| RET-B2 | `PATCH /locations/{id}/retire` | High | 📋 | Session R. |
| RET-B3 | `PATCH /stations/{id}/retire` | High | 📋 | Session R. |
| RET-B4 | `GET /admin/retired?type=&station_id=` | Medium | 📋 | Session R. |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | High | 📋 | Session R. |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | Medium | 📋 | Session R. |

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
| F-UX10 | Scroll-to-card on return from compartment item list | Low | 📋 | Sticky button handles the common case. Revisit post-launch if team finds it insufficient. ~30 min |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 (started_by field) — post-launch |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | Already in seed data, just needs display |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | Post-launch |

---

## 12. Frontend — Check History
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note | High | 📋 | |

---

## 13. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F6 | Station management | High | 📋 | Session R. Needs RET-B3/B4. |
| S-F7 | Vehicle management | High | 📋 | Session R. Needs RET-B1/B2. |
| S-F8 | Par level management | Medium | 📋 | Session R. Needs B-E9. |

---

## 14. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle | High | 📋 | Session R. Needs RET-B1. |
| RET-F2 | Retire jump bag / portable location | High | 📋 | Session R. Needs RET-B2. |
| RET-F3 | Retire inventory lot | High | 📋 | Session R. Needs RET-B5. |
| RET-F4 | Retire station | High | 📋 | Session R. Needs RET-B3. |
| RET-F5 | Retired objects list | Medium | 📋 | Session R. Needs RET-B4. |

---

## 15. Frontend — Tests
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| FE-TEST-11 | `UsageItemPicker.test.jsx` — item picker | High | 📋 | Catalog renders; search filters by `item_name`; +/- controls update quantity; selected items highlighted; "Used most often" section shown when frequentItems provided; "Common items" + history note shown when no history. |
| FE-TEST-12 | `UsageLogScreen.test.jsx` — full flow | High | 📋 | Vehicle picker shown for multi-vehicle stations; auto-skipped for single vehicle; item step renders picker; Done submits correct payload; "Nothing used" calls onBack; submit error displayed. |

---

## 16. Infrastructure / Security
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

## 17. Equipment & Station Administration
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-F10 | Member list search | Low | 📋 | Post-launch. |

---

## 18. User Acceptance Testing
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-2 | Execute Responder test cases | High | 📋 | Against live Azure, real Unit 712 data |
| UAT-3 | Execute Supervisor test cases | High | 📋 | Chief logged in as Supervisor |
| UAT-4 | Execute Administrator test cases | High | 📋 | |
| UAT-5 | Execute cross-role test cases | Medium | 📋 | |
| UAT-6 | Execute edge case test cases | Medium | 📋 | |
| UAT-7 | Pending assignment test case | High | 📋 | |
| UAT-8 | Multi-station test case | Medium | 📋 | |
| UAT-9 | Unit 712 full shift-start check — cold run | Critical | 📋 | Chief + one volunteer, no coaching, production. Pass: zero calls for help, check submitted, dashboard reflects it. |
| UAT-10 | After-call usage log — cold run | Critical | 📋 | Log 2-3 items used. Verify restock list updates. Pass: completed in under 60 seconds without explanation. |
| UAT-11 | Damaged item scenario — cold run | High | 📋 | Simulate discovering a damaged item during UAT-9. Verify in-context path, repair request created, chief sees it on dashboard. |

---

## 19. Open Questions
| # | Question | Notes |
|---|----------|-------|
| Q-3 | Download check history CSV? | Yes — add to F-5G3 scope when first compliance report is due |
| Q-6 | Auto-hard-delete: Azure Function | Resolved: Azure Function (Q-6 answered) |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Security | 2 | 0 | 2 |
| AI Identification — Groundwork | 4 | 0 | 4 |
| Seed Data Gaps — Unit 712 | 2 | 0 | 2 |
| Launch Readiness — Operational | 8 | 0 | 8 |
| Backend — Endpoints | 2 | 0 | 2 |
| Backend — Data Models | 4 | 0 | 4 |
| Backend — Check History | 3 | 0 | 3 |
| Backend — Retirement | 6 | 0 | 6 |
| Frontend — Help System | 1 | 0 | 1 |
| Frontend — Supervisor Dashboard | 1 | 0 | 1 |
| Frontend — Supporting Modules | 1 | 0 | 1 |
| Frontend — Check Wizard UX | 4 | 1 | 5 |
| Frontend — Check History | 1 | 0 | 1 |
| Frontend — Settings | 3 | 0 | 3 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Frontend — Tests | 2 | 0 | 2 |
| Infrastructure / Security | 1 | 1 | 2 |
| Equipment & Station Admin | 1 | 0 | 1 |
| User Acceptance Testing | 11 | 0 | 11 |
| **Total open** | **63** | **2** | **65** |

*Completed items — Sessions A–K — are in backlog_completed.md.*
*v1.62 — 2026-06-06: Backlog cleaned. All ✅ Done items moved to backlog_completed.md.*
*v1.63 — 2026-06-06: Session K complete. Supply Room Redesign (14 items) moved to completed.*
*v1.64 — 2026-06-06: Session K post-close. Migration 0018 fix + supply room setup endpoint + graceful 404 handling + initial_stock.csv.*
*v1.65 — 2026-06-08: Session L complete. Automated test suite: 3 persona files + priority items suite. 304 tests passing. See backlog_completed.md for TEST-* items.*
*v1.66 — 2026-06-08: Seed fix — removed orphan Unit 710 Jump Bag from Newberg Township. Unit 710 has no ambulance seeded; its jump bag was appearing as an orphan in the check wizard Step 1 picker. Unit 712 Jump Bag remains. LAUNCH-OPS3 updated when Unit 710 ambulance is eventually seeded.*
*v1.67 — 2026-06-08: Session L post-close. Safety + seed integrity tests: test_seed_integrity.py (32 tests against seeded dev DB via seeded_db fixture), test_safety_checks.py (13 tests + 1 xfail documenting requires_full_check enforcement gap). Total: 349 passed, 1 xfailed.*
*v1.68 — 2026-06-09: Security/performance improvements partially implemented. Completed: slowapi rate limiting wired (core/limiter.py, main.py), check_date server-derived from timestamp, performed_by uses email, check_history.py ownership checks updated. In progress: test suite broken (60 failures) due to rate limiter firing in tests + conftest/limiter interaction. Continuing in new chat. New backlog items added: PERF-1, PERF-2, TECH-1, TECH-2, TECH-3.*
*v1.69 — 2026-06-09: Post-session L complete. Tests green (349 passed, 1 xfailed). RATE-FIX done; RATE-CI (ruff in CI), RATE-MIG/PERF-2 (migration 0019 + model), RATE-DOCS (CLAUDE.md) all implemented and moved to completed. Session plan expanded: M–Q now covers all pre-launch items with session labels.*
*v1.71 — 2026-06-09: Session M complete. Unit 712 inventory corrections: LUCAS Device changed SUPPLY→FUNCTIONAL with priority_check=True ("LUCAS shows READY?"), AED Pads Adult/Pediatric gained recurrence_days=730 for OVERDUE tracking, Stretcher O2 Tank w/ Regulator and On-Board O2 Tank w/ Regulator 15LPM SUPPLY par levels removed (PSI MEASUREMENT items are canonical), Passenger Side EC 1 compartment removed (empty on Unit 712), Under Hood restriction note removed + requires_full_check=True added. Step2Compartments.jsx: reading rows suppressed for requires_full_check compartments (Truck Ops + Under Hood). wizard.css: priority card body padding fixed. Ruff lint: 117 violations cleared across 15 backend files + 1 frontend test file; B904 added to ignore list (FastAPI exception translation pattern); pyproject.toml updated.*
*v1.73 — 2026-06-10: Added RX-F13 (Same/Different UX for expiry DATE_RECORD items) to Session O.*
*v1.74 — 2026-06-10: Split Session O into O (wizard UX ~3.5 hrs) and P (admin + supply room ~4.5 hrs). Sessions Q/R shift down; UAT becomes Session S. Added SS-B1/SS-F1/SS-F2 (Station Supplies management). ADMIN-B14 renamed SS-B1 and moved to Section 4.*
*v1.75 — 2026-06-10: Session O complete. SEED-GAP2 (requires_full_check enforcement, 364 tests, 0 xfailed), RX-F13 (EXPIRY_DATE check type + Same/Different wizard UX), RX-F9b (priority last-confirmed display), RX-F10 (responder language + error messages) implemented. RX-F3/F4/F5/SUP-F1/SUP-F2 confirmed already implemented from prior sessions. Migration 0021 applied.*
*v1.76 — 2026-06-10: Session P complete. RX-B2 confirmed already implemented. RX-F12 (priority toggle+question in CompartmentParLevels), DMG-F3 (damaged badge in SupplyCatalogView + shelf grouping), SS-B1 (PATCH /admin/locations/{id}), SS-F1 (StationSuppliesScreen.jsx), SS-F2 (per-shelf add in SupplyCatalogView), ADMIN-F7 (PortableLocationsScreen.jsx full CRUD), SUP-F3 (EXPIRY_DATE items in get_expiring_soon). 364 tests passing. No new migrations.*
*v1.77 — 2026-06-10: Session Q complete. B-M10 (migration 0022: allow_check_modification on stations), CH-B7 (PATCH /stations/{id}/settings, Admin), CH-B8 (GET /stations/{id}/settings, Supervisor+), ACC-F1-F5 confirmed already implemented (station_members.py + frontend), S-F1 (Settings nav card), S-F3 (allow_check_modification toggle). CH-F6 unblocked (B-M10+CH-B8 done). UAT-7/UAT-8 unblocked (ACC-F1-F5 done). 368 tests passing. 22 migrations total.*
