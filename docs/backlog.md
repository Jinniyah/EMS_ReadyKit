# EMS ReadyKit — Active Backlog
# v3.06 | Updated: 2026-06-21 | Session AK closed. ITM-7 pulled into Session AL alongside ITM-8.
# Version-history footer (v1.95-v2.07) moved to backlog_completed.md
# to keep this file small — see that file's "Changelog Archive" section for history.
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AK complete — see backlog_completed.md

---

## LAUNCH GATE
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## All prior gate criteria met as of Session AF (full list in backlog_completed.md's
## Changelog Archive). Gate reopened 2026-06-20 — ITM-1..6 ✅ complete (Sessions AG–AK);
## launch is blocked on ITM-7 + ITM-8 below (being done together in Session AL).

---

## PRE-LAUNCH — ITM-7 + ITM-8 (together in Session AL)
## ITM-1..6 ✅ complete — see backlog_completed.md Sessions AG–AK for full detail.

### ITM-7 — Multi-location assign-from-item (pulled into Session AL)
| Field | Value |
|---|---|
| Priority | Medium — pulled into AL alongside ITM-8 per user decision |
| Status | 🔄 In progress (Session AL) |
| Notes | Let one item be assigned to several locations in one pass from `ItemAssignments`. UX: after a successful assign, offer "+ Assign to another location" in the same expanded panel rather than collapsing. The "Where" picker and compartment picker reset; min/max carry over as defaults. No backend change needed — `POST /admin/items/{id}/assign` already handles each assignment independently. Decide exact flow in-session (keep-open vs re-expand vs inline repeat). |

### ITM-8 — Tests + docs (launch gate close)
| Field | Value |
|---|---|
| Priority | Critical (launch-blocking) |
| Status | 🔄 In progress (Session AL) |
| Notes | Frontend gaps from ITM-6: (1) `ItemAssignments.test.jsx` — new file covering the "Where" picker (vehicle/jump bag/supply room paths, auto-select supply room, correct payload shape, assignment display row shows location_label for non-vehicle). (2) Confirm `ItemCatalog.test.jsx` at 15 tests passing. Backend `test_item_station_scoping.py` already complete (14 tests, Session AJ). Close the launch gate: update `CODEBASE_INDEX.md` Next Session table, move ITM-7+8 to `backlog_completed.md`, set all LAUNCH-OPS2/3 unblocked. Deploy after AL close. |

### Sequencing
ITM-1 ✅ → ITM-2 ✅ → ITM-3 ✅ → ITM-4 ✅ → ITM-5 ✅ → ITM-6 ✅ → ITM-7+8 (Session AL) → LAUNCH.

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
| Pre-launch ITM-7..8 | 2 (ITM-7 fast-follow not blocking) — ITM-1..6 ✅ complete (Sessions AG–AK) |
| Post-launch operational | 6 (1 🔄 in progress, 2 ⛔ blocked on ITM reseed) |
| Post-launch engineering | 14 (2 ⛔) |
| **Total remaining** | **22** |
