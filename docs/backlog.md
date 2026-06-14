# EMS ReadyKit — Active Backlog
# v1.90 | Updated: 2026-06-14 | Session X: All CQ items complete — codebase is portfolio-ready
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–X complete — see backlog_completed.md

---

## LAUNCH PHILOSOPHY (established 2026-06-04)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## Launch gate criteria -- ALL must be met before any user sees the app:
##   ✓ Check wizard redesign complete (No Change / Modify / Priority Items)
##   ✓ After-call reset flow complete
##   ✓ Damaged item marking complete
##   ✓ First-run tutorial complete (3-screen minimum)
##   ✓ All responder-facing language plain English (no jargon, no technical errors)
##   ✓ Open repair count visible on compliance dashboard
##   ✓ Vehicle + location retirement actions complete
##   ✓ Priority items configured in admin for Unit 712 (AED, LUCAS, O2, Truck Ops)
##   ✓ UAT executed against live Azure deployment with real Unit 712 inventory
##   ✓ Physical stock count entered for Unit 712 (not seed quantities -- actual counts)
##   ✓ All tests passing
##   ✓ Code cleanup complete (CQ-B4/B5/B6/B7/F1 all done; admin split; schemas clean)

---

## NEXT STEPS
## Run: cd app ; pytest tests/ -v ; alembic upgrade head
## Then take portfolio evidence screenshots + commit Session X changes.
## Remaining UAT: UAT-2 (Responder), UAT-5-8 (cross-role/edge cases)
## Then: LAUNCH-OPS1-9 operational checklist before go-live

---

## 1. AI Item Identification — Groundwork
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| AI-F2 | Barcode search in After-Call Reset | Medium | 📋 | Post-launch. Camera barcode scan -> item lookup. Graceful text search fallback. |
| AI-F3 | Barcode search in supply room receive | Medium | 📋 | Post-launch. Scan barcode to identify item being received. |

---

## 3. Launch Readiness — Operational Checklist
| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 in production admin | EMS chief | 📋 | After RX-F12 ships. Mark AED Battery, LUCAS Device Ready Check, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter actual physical stock count for Unit 712 | EMS chief | 📋 | Seed has par levels (targets) not actual counts. Do physical count before UAT. |
| LAUNCH-OPS3 | Enter actual stock count for Unit 712 Jump Bag | EMS chief | 📋 | |
| LAUNCH-OPS4 | Add all EMS team members in admin | EMS chief | 📋 | ~10 team members need Azure AD login + station member assignment. |
| LAUNCH-OPS5 | Chief full walkthrough -- shift-start check on Unit 712 | EMS chief | 📋 | Complete check in production. Every compartment. Priority items. Submit. Verify dashboard. |
| LAUNCH-OPS6 | Volunteer walkthrough -- Earl or equivalent | Volunteer | 📋 | One less tech-comfortable volunteer runs a complete check cold. Observe without helping. |
| LAUNCH-OPS7 | Marcellus Township -- NOT in initial launch | -- | N/A | Q-19 resolved: Newberg Township only at launch. |
| LAUNCH-OPS8 | Remove TEST STATION from production | Engineering | 📋 | `SEED_TEST_DATA=false` env var check in seed.py. |
| LAUNCH-OPS9 | Verify Azure AD user emails match station member emails | Engineering | 📋 | StationMember.user_id keyed on email. Mismatch = "not listed" error on first login. |

---

## 8. Frontend — Help System
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5C2 | Contextual "?" help -- bottom sheet per wizard step | Medium | 📋 | Post-launch. Based on what questions the team actually asks after first month. |

---

## 9. Frontend — Supervisor Dashboard
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5F7 | Supply room stock view on dashboard | Medium | 📋 | Post-launch enhancement |

---

## 10. Frontend — Supporting Modules
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5G3 | Data export -- CSV for history, audit, repairs | Medium | 📋 | When first compliance report is due. |

---

## 11. Frontend — Check Wizard UX
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX10 | Scroll-to-card on return from compartment item list | Low | 📋 | Post-launch. |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 (started_by field) -- post-launch |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | Post-launch |

---

## 16. Infrastructure / Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall | Medium | 📋 | Post-launch. Before scaling to second service. |
| I-2 | Re-add route table | Medium | ⛔ | |
| TECH-2 | React Query for frontend data management | Low | 📋 | Post-launch refactor. |
| TECH-3 | Offline submission queue (F-UX9) | Low | 📋 | Post-launch. IndexedDB queue retries on reconnect. |

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
| UAT-3 | Execute Supervisor test cases | High | ✅ | Passed -- 2026-06-12 |
| UAT-4 | Execute Administrator test cases | High | ✅ | Passed -- 2026-06-12 |
| UAT-5 | Execute cross-role test cases | Medium | 📋 | |
| UAT-6 | Execute edge case test cases | Medium | 📋 | |
| UAT-7 | Pending assignment test case | High | 📋 | |
| UAT-8 | Multi-station test case | Medium | 📋 | |
| UAT-9 | Unit 712 full shift-start check -- cold run | Critical | 📋 | Chief + one volunteer, no coaching, production. |
| UAT-10 | After-call usage log -- cold run | Critical | 📋 | Log 2-3 items used. Verify no supply room change; next check flags short; dashboard shows restock needed. |
| UAT-11 | Damaged item scenario -- cold run | High | 📋 | Simulate discovering a damaged item during UAT-9. |

---

## 20. Open Questions
| # | Question | Notes |
|---|----------|-------|
| Q-3 | Download check history CSV? | Yes -- add to F-5G3 scope when first compliance report is due |
| Q-6 | Auto-hard-delete: Azure Function | Resolved: Azure Function (Q-6 answered) |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| AI Identification -- Groundwork | 2 | 0 | 2 |
| Launch Readiness -- Operational | 8 | 0 | 8 |
| Frontend -- Help System | 1 | 0 | 1 |
| Frontend -- Supervisor Dashboard | 1 | 0 | 1 |
| Frontend -- Supporting Modules | 1 | 0 | 1 |
| Frontend -- Check Wizard UX | 2 | 1 | 3 |
| Infrastructure / Security | 2 | 1 | 3 |
| Equipment & Station Admin | 1 | 0 | 1 |
| User Acceptance Testing | 8 | 0 | 8 |
| **Total open** | **26** | **2** | **28** |

*v1.90 -- 2026-06-14: Session X. CQ-B4/B5/B6/B7/F1 all complete. Code quality section removed (done). Portfolio-ready.*
*v1.89 -- 2026-06-13: USAGE-B1/B2 closed; UAT-10 unblocked. Unscheduled section removed.*
*v1.88 -- 2026-06-13: Session W. CH-B4/B5/B6 + tests. restoreCheck frontend.*
