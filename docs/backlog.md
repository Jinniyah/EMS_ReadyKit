# EMS ReadyKit — Active Backlog
# v1.95 | Updated: 2026-06-14 | Session Z: ACC-B6, ACC-B7, ACC-B8 implemented
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–Z complete — see backlog_completed.md

---

## LAUNCH PHILOSOPHY (established 2026-06-04)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## Launch gate criteria — ALL MET except items marked below:
##   ✓ Check wizard redesign complete (No Change / Modify / Priority Items)
##   ✓ After-call reset flow complete
##   ✓ Damaged item marking complete
##   ✓ First-run tutorial complete (3-screen minimum)
##   ✓ All responder-facing language plain English (no jargon, no technical errors)
##   ✓ Open repair count visible on compliance dashboard
##   ✓ Vehicle + location retirement actions complete
##   ✓ Priority items configured in admin for Unit 712 (AED, LUCAS, O2, Truck Ops)
##   ✓ UAT complete — Responder, Supervisor, Administrator, cross-role, edge cases all passed
##   ✓ Physical stock count entered for Unit 712
##   ✓ All tests passing (437 collected, 0 failed -- run again after migration 0027)
##   ✓ Code cleanup complete (CQ-B4/B5/B6/B7/F1; admin split; schemas clean)
##   ✗ Help & Tutorial updated for current feature set (LAUNCH-F1)
##   ✗ PII/sensitive data disclaimer banner on login screen (LAUNCH-F2)

---

## NEXT STEPS
## 1. Run: cd app ; alembic upgrade head  (applies migration 0027)
## 2. Run: pytest tests/ -v  (verify 0 failures including new test_member_management.py)
## 3. Commit Session Z changes
## 4. Then tackle LAUNCH-F1 and LAUNCH-F2 before go-live

---

## 2. Pre-Launch Engineering — Must ship before go-live
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| LAUNCH-F1 | Update Help & Tutorial screens for current feature set | High | 📋 | Review all first-run tutorial content against shipped feature set -- wizard steps, supply room, after-call reset, damaged items, check history. Update stale copy and add missing flows. |
| LAUNCH-F2 | PII / sensitive data disclaimer banner on login screen | High | 📋 | Before any real user logs in: clear notice that EMS ReadyKit is not configured or approved for PII, PHI, or other sensitive information. Plain-text banner on the login screen, visible before entering the app. |

---

## 3. Launch Readiness — Operational Checklist
| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 in production admin | EMS chief | 📋 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device Ready Check, O2 PSI as priority. Set custom question text. |
| LAUNCH-OPS2 | Enter actual physical stock count for Unit 712 | EMS chief | 📋 | Seed has par levels (targets) not actual counts. Physical count required before first live check. |
| LAUNCH-OPS3 | Enter actual stock count for Unit 712 Jump Bag | EMS chief | 📋 | |
| LAUNCH-OPS4 | Add all EMS team members in admin | EMS chief | 📋 | Use the new CSV import in Settings → Team Members to bulk-add the team. |
| LAUNCH-OPS5 | Chief full walkthrough -- shift-start check on Unit 712 | EMS chief | 📋 | Complete check in production. Every compartment. Priority items. Submit. Verify compliance dashboard reflects it. |
| LAUNCH-OPS6 | Volunteer walkthrough -- Earl or equivalent | Volunteer | 📋 | One less tech-comfortable volunteer runs a complete check cold. Observe without helping. Questions = UX issues. |
| LAUNCH-OPS7 | Marcellus Township -- NOT in initial launch | -- | N/A | Q-19 resolved: Newberg Township only at launch. |
| LAUNCH-OPS8 | Remove TEST STATION from production | Engineering | 📋 | `SEED_TEST_DATA=false` env var check in seed.py. |
| LAUNCH-OPS9 | Verify Azure AD user emails match station member emails | Engineering | 📋 | StationMember.user_id keyed on email. Mismatch = "not listed" error on first login. Verify before launch day. |

---

## 1. AI Item Identification — Groundwork
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| AI-F2 | Barcode search in After-Call Reset | Medium | 📋 | Post-launch. Camera barcode scan → item lookup. Graceful text search fallback. |
| AI-F3 | Barcode search in supply room receive | Medium | 📋 | Post-launch. Scan barcode to identify item being received. |

---

## 8. Frontend — Help System
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5C2 | Contextual "?" help -- bottom sheet per wizard step | Medium | 📋 | Post-launch. Based on what questions the team actually asks after first month. |

---

## 10. Frontend — Supporting Modules
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5G3 | Data export -- CSV for history, audit, repairs | Medium | 📋 | Post-launch. Build when first compliance report is due. |

---

## 11. Frontend — Check Wizard UX
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX10 | Scroll-to-card on return from compartment item list | Low | 📋 | Post-launch. |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 (started_by field) -- post-launch. |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | Post-launch. IndexedDB queue retries on reconnect. |

---

## 16. Infrastructure / Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall | Medium | 📋 | Post-launch. Before scaling to second service. |
| I-2 | Re-add route table | Medium | ⛔ | |
| TECH-2 | React Query for frontend data management | Low | 📋 | Post-launch refactor. |
| TECH-3 | Offline submission queue (F-UX9) | Low | 📋 | Post-launch. |

---

## 17. Equipment & Station Administration
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-F10 | Member list search | Low | 📋 | Post-launch. |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Pre-Launch Engineering | 2 | 0 | 2 |
| Launch Readiness -- Operational | 8 | 0 | 8 |
| AI Identification -- Groundwork | 2 | 0 | 2 |
| Frontend -- Help System | 1 | 0 | 1 |
| Frontend -- Supporting Modules | 1 | 0 | 1 |
| Frontend -- Check Wizard UX | 2 | 1 | 3 |
| Infrastructure / Security | 2 | 1 | 3 |
| Equipment & Station Admin | 1 | 0 | 1 |
| **Total open** | **19** | **2** | **21** |

*v1.95 -- 2026-06-14: Session Z. ACC-B6/B7/B8 complete. Migration 0027 (multi-role constraint). test_member_management.py added. UserPill and useRoleMode updated for multi-role switching.*
*v1.94 -- 2026-06-14: Five new admin/launch items added from Jennifer's review.*
*v1.93 -- 2026-06-14: F-5F7 closed. v1.92: Q-3/Q-6 closed. v1.91: UAT complete.*
