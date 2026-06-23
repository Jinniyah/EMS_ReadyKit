# EMS ReadyKit — Active Backlog
# v3.12 | Updated: 2026-06-23 | Session AO closed (pre-deploy security + correctness sweep:
# 15 findings, all resolved — db.commit() gap in deactivate routes, missing station scoping
# on update_par_level + list_vehicle_compartments, <form> CLAUDE.md violations, stale
# stationId closure in ItemSearchCombobox, deriveLocType Option A, CSS cross-module fix,
# useApi error fields, PAR-B1 ORDER BY, test fixture cleanup, dead file deletion).
# Version-history footer (v1.95-v2.07) moved to backlog_completed.md
# to keep this file small — see that file's "Changelog Archive" section for history.
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AN complete — see backlog_completed.md

---

## LAUNCH GATE — ✅ ALL CRITERIA MET (Session AN)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## ITM-1..8 ✅ all complete (Sessions AG–AN). VERIFY-AL1 ✅ confirmed.
## Deploy to production to launch.

---

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter physical stock count for Unit 712 | 📋 Unblocked — ITM-4 reseed complete; catalog is deduplicated and canonical. |
| LAUNCH-OPS3 | Enter stock count for Unit 712 Jump Bag | 📋 Unblocked — same. |
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
| Pre-launch | 0 — ITM-1..8 ✅ all complete (Sessions AG–AN); launch gate closed |
| Post-launch operational | 6 (1 🔄 in progress, 2 previously blocked now unblocked) |
| Post-launch engineering | 14 |
| **Total remaining** | **20** |
