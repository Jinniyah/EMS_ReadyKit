# EMS ReadyKit — Active Backlog
# v3.20 | Updated: 2026-07-12 | Session AS: Marcellus onboarding kicked off —
# second real station joining UAT. Added ordered 4-item sequence (ONBOARD-1,
# F-5G3a, VALID-1, INFRA-UAT1) per Jennifer's explicit sequencing: ingest
# Marcellus's inventory docs, build Bobby's compliance CSV export, validate
# it live in UAT, THEN split into UAT(F1)/PROD(B1) — deliberately last since
# there's no real data yet worth protecting from a mid-flight split.
# Previous: v3.19 Session AR: SEC-03 fixed — OpenAPI docs gating
# decoupled from APP_ENV/is_production via new enable_api_docs setting
# (secure by default, same pattern as REQUIRE_REAL_AUTH). Applying the fix
# surfaced a separate pre-existing Key Vault firewall gap as a full outage
# (App Service subnet was never allowlisted on the Key Vault's network_acls);
# fixed by adding the Microsoft.KeyVault service endpoint to snet-app and
# virtual_network_subnet_ids on the Key Vault, mirroring the existing
# snet-data pattern. Full write-up in backlog_completed.md Session AR.
# LAUNCH-OPS5/6 (chief + volunteer walkthroughs) remain open below.
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

## MARCELLUS ONBOARDING — IN PROGRESS (Session AS)
## Second real station (Marcellus) joining UAT. Ordered sequence per Jennifer —
## do not reorder; UAT/PROD split is deliberately last since there's no real
## data yet worth protecting from a split done mid-flight.

| # | Task | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ONBOARD-1 | Ingest Marcellus's station documentation | High | 📋 Not started | 2 fire trucks, 1 ambulance, 1 jump bag, station storage. Jennifer to supply converted images/docs; update vehicle/inventory records to match. Check for hardcoded single-station assumptions in station/vehicle models while in there. |
| F-5G3a | Daily check CSV export for station-license compliance (Bobby) | High | 📋 Not started | New download button, Check History (supervisor view). Filters: date range + vehicle (or "all"). Manual download only — Bobby uploads to OneDrive himself, no Graph API integration. Narrows part of F-5G3's Check History scope; pairs with B-E3 (date-range compliance query) for the filter logic. |
| VALID-1 | Validate CSV export end-to-end in current UAT environment | High | 📋 Not started | Confirm with Marcellus/Bobby before promoting anything — correct fields, correct filtering, file opens cleanly, matches what a station inspector would expect to see. |
| INFRA-UAT1 | Split deployed app into UAT (F1) / PROD (B1) environments | High | 📋 Not started | New F1 App Service Plan + Linux Web App for UAT ($0/mo); existing B1 app becomes PROD; new database on existing PostgreSQL Flexible Server (no new server); SWA free-tier PR-preview staging covers frontend UAT already, no new SWA resource needed. Branch-based promotion: `develop`→UAT auto-deploy, `main`→PROD gated by GitHub Environment manual-approval rule. Rename resources as needed once split. No data migration required (no real data in the tool yet). Terraform: new `azurerm_service_plan` (F1) + `azurerm_linux_web_app` + `azurerm_postgresql_flexible_server_database` + updated Key Vault secret refs + AD redirect URI. |

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
| F-5G3 | CSV data export | Medium | Audit Log and Repair Requests download buttons. Same streaming CSV pattern as the receive-stock template. Check History download now scoped separately as F-5G3a (Bobby's compliance export, see Marcellus Onboarding section above). |
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
| Marcellus onboarding | 4 (all 📋 not started — ONBOARD-1, F-5G3a, VALID-1, INFRA-UAT1) |
| Post-launch engineering | 14 |
| **Total remaining** | **20** |
