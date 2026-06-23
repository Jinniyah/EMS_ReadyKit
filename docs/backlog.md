# EMS ReadyKit — Active Backlog
# v3.14 | Updated: 2026-06-23 | PortableLocationsScreen had the same `station is
# not defined` ReferenceError as VehiclesScreen (Session AM) — ShelfManager
# never received a station prop. Fixed using location.station_id. Confirmed
# via npm test + npm run build, deployed. StationSuppliesScreen checked and
# confirmed clean (station is a real top-level prop there, no nested helper
# component). All three CompartmentParLevels consumers now verified correct.
# Version-history footer (v1.95-v2.07) moved to backlog_completed.md
# to keep this file small — see that file's "Changelog Archive" section for history.
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AO complete — see backlog_completed.md

---

## LAUNCH GATE — ✅ ALL CRITERIA MET (Session AN)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## ITM-1..8 ✅ all complete (Sessions AG–AN). VERIFY-AL1 ✅ confirmed.
## Production deploy live and confirmed working (Session AO sweep; AM-era
## VehiclesScreen + compartment-PATCH fixes verified live; PortableLocationsScreen
## ReferenceError fix pushed and pending live verification).

---

## VERIFY NEXT SESSION (or immediately, if still in this one)

### VERIFY-AM2 — Confirm Jump Bag compartments load on live site
| Field | Value |
|---|---|
| Priority | High (until confirmed) |
| Status | 📋 Not started |
| Notes | `PortableLocationsScreen.jsx`'s `ShelfManager` had the same `ReferenceError: station is not defined` bug as `VehiclesScreen.jsx`'s `VehicleAdminCard` (Session AM) — `stationId={station.station_id}` referenced a `station` that was never in scope inside the nested helper component. Fixed with `location.station_id` instead, confirmed via `npm test` + `npm run build`, and pushed. Confirm live: Station Administration → Jump Bags → expand Unit 712 Jump Bag → compartments load with no console error. |

---

## CLEANUP — carried forward from Session AM

### CLEANUP-AM1 — Finalize dead routers/admin.py removal
| Field | Value |
|---|---|
| Priority | Low |
| Status | 📋 Not started |
| Notes | `routers/admin.py` — the pre-split monolithic admin router superseded by `admin_items.py`/`admin_stations.py`/`admin_vehicles.py` since Session X — was confirmed unreferenced by `main.py` and moved out of `app/ems_readykit/routers/` into `_session_AM_removed/admin.py` at the repo root (filesystem MCP has no delete; this is the project's standard staging pattern). Run `git rm -r _session_AM_removed` (or `git rm _session_AM_removed/admin.py` followed by removing the now-empty directory) to finalize. Confirmed safe: 0% coverage on 436 dead statements was distorting the project-wide coverage total by roughly nine points; removing it does not change `main.py`'s router-include list or any test, since nothing imported it. |

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
| TEST-AM3 | Component tests for VehicleAdminCard and ShelfManager expanded-state rendering | Medium | Both bugs this session (`station is not defined` in two sibling components) shipped because no existing test rendered a card/shelf in its *expanded* state — only collapsed-list rendering was covered. Add tests that expand a card/shelf and assert `CompartmentParLevels` renders without throwing, for both `VehiclesScreen` and `PortableLocationsScreen`. |
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
| Pre-launch | 0 — ITM-1..8 ✅ all complete (Sessions AG–AN); launch gate closed; production deploy live |
| Verify next | 1 — VERIFY-AM2 (confirm Jump Bag fix live, high priority until confirmed) |
| Cleanup carried forward | 1 — CLEANUP-AM1 (finalize staged dead-file removal, low priority) |
| Post-launch operational | 6 (1 🔄 in progress, 2 previously blocked now unblocked) |
| Post-launch engineering | 15 |
| **Total remaining** | **23** |
