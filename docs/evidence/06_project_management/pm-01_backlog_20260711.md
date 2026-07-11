# EMS ReadyKit — Active Backlog
# v3.18 | Updated: 2026-06-23 | Session AQ: F-5C2 Help & Tutorial screen delivered and moved to
# backlog_completed.md (Session AP) — priority items configured, Unit 712 +
# Jump Bag stock counts entered, EMS team members added. Also fixed this
# session and logged in backlog_completed.md: PATCH /admin/items/{id} 422 on
# edit (ItemUpdate schema split from ItemCreate). LAUNCH-OPS5/6 (chief +
# volunteer walkthroughs) remain open below.
# Version-history footer (v1.95-v2.07) moved to backlog_completed.md
# to keep this file small — see that file's "Changelog Archive" section for history.
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AP complete — see backlog_completed.md

---

## LAUNCH GATE — ✅ ALL CRITERIA MET (Session AN)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## ITM-1..8 ✅ all complete (Sessions AG–AN). VERIFY-AL1 ✅ confirmed.
## Production deploy live and confirmed working: Session AO sweep deployed clean;
## Session AM's VehiclesScreen crash, compartment-PATCH bug, and
## PortableLocationsScreen crash (same root-cause pattern, found and fixed in the
## same session) are all fixed and confirmed live. No known outstanding bugs.
## Dead routers/admin.py fully removed (CLEANUP-AM1 ✅).

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | 🔄 In progress — surfaced ITM-1..8 among other findings. |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | 📋 Not started |

### Post-launch engineering
| # | Item | Pri | Notes |
|---|------|-----|-------|
| F-5G3 | CSV data export | Medium | One download button each in: Check History (supervisor view), Audit Log, Repair Requests. Same streaming CSV pattern as the receive-stock template. |
| ADMIN-F10 | Member list search/filter | Low | Search box in `MemberManagementSection` (`modules/admin/`) filtering by name or email. Client-side, no new backend endpoint. |
| TEST-AE1 | Test coverage for MembersScreen / MemberManagementSection | Medium | Multi-role grouping/display, CSV import happy path + errors, name edit, member_id-based role removal, Supervisor-vs-Admin role-gating. |
| TEST-AF1 | Test coverage for the rewritten ComplianceCalendar.jsx | Medium | Jump bags in month view, Station Supplies Count reminder strip, EntityPicker, getLocationCheckHistory data source. Pair with TEST-AE1. |
| TEST-AM3 | Component tests for VehicleAdminCard and ShelfManager expanded-state rendering | Medium | Both bugs this session (`station is not defined` in two sibling components) shipped because no existing test rendered a card/shelf in its *expanded* state — only collapsed-list rendering was covered. Add tests that expand a card/shelf and assert `CompartmentParLevels` renders without throwing, for both `VehiclesScreen` and `PortableLocationsScreen`. |
| AI-F2 | Barcode search in After-Call Reset | Medium | Deferred by decision. |
| AI-F3 | Barcode search in supply room receive | Medium | Deferred by decision. |
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
| Pre-launch | 0 — ITM-1..8 ✅ all complete (Sessions AG–AN); launch gate closed; production deploy live and fully verified, no known outstanding bugs |
| Cleanup carried forward | 0 — CLEANUP-AM1 ✅ confirmed complete |
| Post-launch operational | 2 (1 🔄 in progress — OPS5; 1 📋 not started — OPS6; OPS1-4 ✅ done, moved to backlog_completed.md) |
| Post-launch engineering | 14 |
| **Total remaining** | **16** |
