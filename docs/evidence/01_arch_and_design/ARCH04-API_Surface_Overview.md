## Backend — Routers (app/ems_readykit/routers/)

All routes are prefixed `/api/v1/`. Router registration order in main.py matters (station_members before stations; check_history before checks).

| File | Size | Route Prefix | Roles | Purpose |
|------|------|-------------|-------|---------|
| `deps.py` | 5 KB | — | — | Shared: `get_current_user`, `require_role`, `get_vehicle_or_404`, `require_station_membership`, role constants |
| `stations.py` | 11 KB | `/stations` | All / Admin | CRUD; GET /my; GET supply-room (404 if missing); POST supply-room (get-or-create + Shelf 1–4); `GET /stations/{id}/expiring-soon` includes EXPIRY_DATE check-type items (SUP-F3); `GET /stations/{id}/settings` (Supervisor+, CH-B8); `PATCH /stations/{id}/settings` (Admin only, CH-B7); `PATCH /stations/{id}/retire` (Admin, RET-B3); `GET /stations/{id}/damaged-items` (Supervisor+, SUP-DMG1). `GET /stations/{id}/supply-room` has no `retired_at` filter server-side — a retired supply room is still returned; the frontend filters it out (see supervisorApi.js note below). |
| `station_members.py` | 8 KB | `/stations/{id}/members` | Supervisor+ | Membership management; PATCH/DELETE by `member_id` (integer PK, ACC-B7); CSV bulk import + template download (ACC-B8). This is the only correct member endpoint set — frontend consolidated onto it in Session AE (MERGE-1) after a stale `user_id`-based caller in `adminApi.js` was found broken. |
| `vehicles.py` | 6 KB | `/vehicles` | All + membership | Vehicle CRUD; OOS/RTS status toggle; `PATCH /vehicles/{id}/retire` (Admin, RET-B1) — sets `retired_at`, `retired_by`, `retirement_reason`, AND `active=False`. Frontend must check `retired_at` directly, not just `active` (see BUG-AD1, Session AD). `GET /stations/{id}/vehicles` returns ALL vehicles (active + retired) unless `?active=true` is explicitly passed — callers that don't pass it must filter `retired_at` client-side (Session AF, found in `supervisorApi.getTodayCompliance`). |
| `checks.py` | 26 KB | `/checks/daily` | All + membership | Check wizard: create with embedded line_items; `_compute_line_item_status`; `_auto_decrement_supply_room` (SR-B4, N+1 batched PERF-1); `_reconcile_supply_room_check` (SR-B5 — called on STATION_SUPPLY_ROOM submission; reconciles quantity_found back to StockLot quantities FIFO); helpers: `_resolve_check_location`, `_enforce_full_check_compartments`, `_build_lot_map`, `_build_line_items` (CQ-B3); `GET /daily/last-readings`. Two distinct list endpoints with very different scope, worth knowing apart: `GET /daily/station/{station_id}` (date-range, capped at 90 days, 422s above that) vs `GET /daily/location/{location_id}` (single location, ALL checks ever, no range limit at all) — see BUG-AF2 note below for why picking the wrong one breaks an "all-time most recent" lookup. |
| `check_history.py` | 7 KB | `/checks/daily` | All / Supervisor+ | Read-only history; soft-delete; acknowledgement; hard-delete (Admin only); `my-history` accepts optional `station_id` filter |
| `repair_requests.py` | 9 KB | `/vehicles/{id}/repair-requests` | All roles | File, update, resolve repair requests; `resolution_notes` required on RESOLVED |
| `inventory.py` | 28 KB | `/inventory` | All + membership | Locations, compartments, par levels, lots, stock summary, CSV receive. `GET /supply-catalog?station_id=` (SR-B1). `PATCH /supply-catalog/items/{id}/count` (SR-B2). `PUT /lots/{id}` (SR-F7). `PATCH /inventory/items/{id}/status` marks/clears damaged. `PATCH /locations/{id}/retire` (Admin, RET-B2). `GET /lots/retired?location_id=` (Supervisor+, RET-B6). `PATCH /lots/{id}/retire` (Supervisor+, RET-B5) — registered BEFORE `/lots/{lot_id}` to avoid path ambiguity. `PATCH /par-levels/{id}` soft-deactivate with reason + membership check (B-E9). `POST /par-levels` (`create_par_level`) reactivates a matching soft-deactivated `(item_id, compartment_id)` row instead of inserting a duplicate (PAR-B1, Session AF) — see note below. |
| `items.py` | 3 KB | `/items` | Supervisor+ (create/edit) / All (read) | Item catalog; `POST /items` is SUPERVISOR_PLUS (not admin-only); deactivation is ADMIN_ONLY via admin router. Note: `GET /items` is not station-scoped (it's a lightweight read-only catalog; scoping lives in the admin routes via ITM-5). |
| `admin_items.py` | — | `/admin` | Admin (most) / Supervisor+ | Item catalog admin, par levels, CSV import (split from monolithic admin.py, CQ-B5). **ITM-5 ✅ (Session AJ):** All 11 routes now require `station_id` and call `require_station_membership` before any data access. `_conflict_on_name` is per-station; `_conflict_on_barcode` remains global. `POST /admin/items/{id}/assign` (`assign_item_to_compartment`) reactivates a matching soft-deactivated `(item_id, compartment_id)` par level instead of inserting a duplicate (PAR-B1, Session AF) — see note below. Already accepts `location_id` for any `InventoryLocation` (vehicle, jump bag, or supply room) — the frontend (`ItemAssignments.jsx`) just never exposes jump-bag/supply-room options yet (ITM-6). |
| `admin_vehicles.py` | — | `/admin` | Admin | Vehicle color and details admin (split from monolithic admin.py, CQ-B5) |
| `admin_stations.py` | — | `/admin` | Admin | `POST /admin/stations` (ADMIN-B15, auto-creates supply room + StationMember). `PATCH /admin/locations/{id}` renames a location label (SS-B1). `GET /admin/retired?type=&station_id=` lists retired vehicles/locations/stations (RET-B4). `GET /admin/email-alignment-check?station_id=&include_inactive=` — flags StationMember rows whose `user_id` doesn't look like a valid email (blank, contains whitespace, missing `@`/domain, not lowercase); read-only diagnostic for catching display-name-instead-of-email mistakes from manual add or CSV import (LAUNCH-OPS9, Session AC). |
| `usage.py` | 9 KB | `/checks` | All + membership | `POST /checks/usage` (log items used, FIFO decrement); `GET /checks/usage/station/{id}` (history); `GET /checks/usage/station/{id}/frequent` (top 10 items, 90-day window) |
| `audit.py` | 2 KB | `/audit` | Supervisor+ | Paginated audit event log; `GET /audit?from_date=&to_date=` date-range filter (B-E18). Unmodified across Session AF — two separate suspicions about a naive/aware datetime comparison here were each checked via isolated repro and ruled out; the real bug both times was on the test side (global-table pollution, then a local-vs-UTC date computed in the wrong timezone). See `docs/backlog_completed.md` Session AF write-up for the full two-pass diagnosis before touching this file's date filters. |

---

## Frontend — Modules (frontend/src/modules/)

Each module is self-contained with its own `index.jsx`, `api/`, `components/`.

### check-wizard/  (PWA 5-step check flow)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 15 KB | Wizard orchestration, step routing, draft state. Passes `selectionLabel` to `WizardProgress`. |
| `components/Step1Vehicle.jsx` | 14 KB | Vehicle/location selection + CS check toggle; detects `draft._supplyRoom` for supply room wizard path. `isCheckableVehicle(v)` helper checks both `active !== false` AND `!retired_at` (defensive fix, BUG-AD1 Session AD — this path was already safe via a side effect of the server-side `active=true` filter, but now checks `retired_at` directly instead of relying on that). |
| `components/Step2Compartments.jsx` | 14 KB | Priority items section (inline confirm) + compartment list with reading confirmations; No Change / Modify / stock preview. Short count based on last check quantity_found. Reading confirmation rows are suppressed for `requires_full_check` compartments. Calls `onCompartmentsLoaded(compartments)` via `useEffect` so wizard index can populate `compartmentList` for progress bar, Step3 nav, and Step5 summary. Correctly filters `pl.active !== false` everywhere already. |
| `components/Step3Items.jsx` | 7 KB | Item counting per compartment. Reads par levels from the already-`active`-filtered backend response, so it reflects whatever is currently active for the compartment — see PAR-B1 above for why a "removed but still expected" item was actually a server-side reactivation bug, not a frontend filtering bug. |
| `components/ItemRow.jsx` | 16 KB | Per-item row — all check types (supply/measurement/functional/date) |
| `components/Step4Reconcile.jsx` | 13 KB | Flagged items review |
| `components/Step4Review.jsx` | 7 KB | Final summary before submit |
| `components/Step5Submit.jsx` | 9 KB | Submission + CS check dual-sign. `checkSubject` uses `selectionLabel` for supply room checks. `displayDate` has `todayIso()` fallback. |
| `components/SubmittedScreen.jsx` | 6 KB | Post-submit confirmation |
| `components/DraftBanner.jsx` | 5 KB | Resume-draft prompt on load; last-known station cached in localStorage |
| `components/WizardProgress.jsx` | 3 KB | Top progress bar. Step 1 label uses `selectionLabel` prop (defaults to 'Vehicle'). |

### supervisor/  (Compliance dashboard)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 7 KB | Dashboard entry; loads supply alerts (SR-B3) for SupplyLowStockPanel. Session AF: `vehicles` re-filtered defensively by `!v.retired_at` (source-of-truth fix is in `supervisorApi.js`, this is a second defensive layer matching the BUG-AD1 convention). |
| `components/ComplianceCalendar.jsx` | — | Calendar view of check compliance. Rewritten Session AF: week view = active (non-retired) vehicles + jump bags only; Station Supply Room intentionally excluded from week view (periodic count, not daily — would just be empty space). Month view = combined vehicle/jump-bag picker (`EntityPicker`) + traditional grid. The `SupplyRoomReminder` strip lives directly under the Week/Month toggle (visible in both views, moved there mid-session per UAT feedback that a chip buried in month view would get seen far less often). Supply room fetched via `supervisorApi.getSupplyRoomLocation`, which filters out a retired supply room client-side; its check history is fetched via `supervisorApi.getLocationCheckHistory` (BUG-AF2 fix — NOT `getComplianceRange`, which is range-capped and cannot answer "most recent ever"). Has an explicit error state (`.cal__supply-reminder--error`) instead of silently rendering as if no count existed. No test file yet — see TEST-AF1 in `docs/backlog.md`. |
| `components/CheckDetailPanel.jsx` | 9 KB | Drill-down check detail — read-only + comments only |
| `components/VehicleComplianceCard.jsx` | 7 KB | Per-vehicle compliance summary card |
| `components/PortableComplianceCard.jsx` | — | Per-portable-location compliance summary card |
| `components/ExpiringItemsPanel.jsx` | — | SUP-F3: expandable expiring lots panel |
| `components/SupplyLowStockPanel.jsx` | — | SR-F5: expandable supply low-stock panel; red if out, amber if below par |
| `components/DamagedItemsPanel.jsx` | — | SUP-DMG1: collapsible panel listing damaged items (item name, vehicle, compartment). allClear only when no FAIL + no damaged items. |
| `api/supervisorApi.js` | — | Session AF: `getTodayCompliance` now filters `vehicles = vehiclesRaw.filter(v => !v.retired_at)` at the source, since `GET /stations/{id}/vehicles` returns retired vehicles unless `active=true` is passed. `getSupplyRoomLocation(stationId, getToken)` fetches the station's supply room and returns `null` if missing OR retired (`!loc.retired_at` checked client-side, since the backend endpoint has no such filter). `getLocationCheckHistory(locationId, getToken)` (BUG-AF2) — all checks ever recorded at one location, no date-range limit; the correct source for "when was this last counted," unlike `getComplianceRange` which is capped at 90 days and exists for windowed calendar views, not all-time lookups. |

### admin/  (Station administration — Option B layout: station header + nav cards)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 21 KB | Admin hub: nav cards → Members / Items / Vehicles / Supplies / Jump Bags screens |
| `components/MembersScreen.jsx` | — | **Station Administration -> Members** — the single member-management entry point (Session AE, MERGE-1). Wraps `MemberManagementSection` (visible to Supervisor+) and `EmailAlignmentSection` (Admin only). Replaces the old flat-list MemberList/AddMemberForm pair, which called a broken user_id-based removal endpoint. |
| `components/MemberManagementSection.jsx` | — | Moved from `settings/` (Session AE). Member list grouped by person, edit name, multi-role chips with per-role remove, CSV import. ACC-B6/B7/B8. No test file yet — see TEST-AE1 in `docs/backlog.md`. |
| `components/EmailAlignmentSection.jsx` | — | Moved from `settings/` (Session AE). LAUNCH-OPS9 diagnostic — flags malformed `user_id` entries; notify-panel with mailto draft. Admin only. |
| `components/VehiclesScreen.jsx` | 25 KB | Vehicle + compartment CRUD, par assignment entry. Display filter excludes retired vehicles outright (`!v.retired_at`), independent of the "Show out-of-service vehicles" toggle (BUG-AD1, Session AD). `VehicleAdminCard` shows a "Retired" badge + retirement reason and hides Edit/Color-still-shown/OOS-RTS/compartment-edit controls for retired vehicles. |
| `components/ItemCatalog.jsx` | — | Item catalog browser. **ITM-6 ✅ (Session AK):** station-scoped (`stationId` → `adminApi.listItems`); 7 cabinet-group chip filters (Airway/Wound Care/PPE/Diagnostic/Medications/Documents/Vehicle Ops) replace old 4-category chips; groups items by `category_group` (falls back to `category` when null); fetches `getStationLocations` and passes `locations` to each `ItemAssignments`. |
| `components/ItemForm.jsx` | 16 KB | Add/edit item form |
| `components/ItemAssignments.jsx` | — | Par level assignment — item-centric. **ITM-6 ✅ (Session AK):** `AddAssignmentForm`/`EditRow` now have a "Where" picker (Vehicle / Jump Bag / Station Supply Room). Vehicles use `vehicle_id`; jump bags and supply room use `location_id`. Supply room auto-selects. Compartments loaded via `getVehicleCompartments` (vehicle) or `getLocationCompartments` (other). Assignment display row shows `vehicle_number ?? location_label`. Button renamed to "+ Add assignment". **ITM-7 ✅ (Session AN):** After a successful assign, shows inline confirmation ("✓ Assigned to …") with "+ Assign to another location" (resets form, carries min/max) and "Done" (closes panel) instead of collapsing. |
| `components/CompartmentParLevels.jsx` | — | Par level assignment — per-compartment item list. Accepts `vehicleId` OR `locationId` (for supply room / portable locations). Priority checkbox + question field (RX-F12). Remove → re-add round trip fixed by PAR-B1 (Session AF) — this was the exact UI path the bug was reported through. |
| `components/StationSuppliesScreen.jsx` | — | SS-F1: Admin screen — manage supply room shelves and their par levels. Fetches supply room → compartments → CompartmentParLevels per shelf. |
| `components/PortableLocationsScreen.jsx` | — | ADMIN-F7: Full CRUD for portable locations (Jump Bags). List → create → rename + ShelfManager (compartment CRUD + par levels). |
| `components/CsvImport.jsx` | 8 KB | Bulk item import with template download |
| `api/adminApi.js` | — | Station CRUD, item catalog, par levels, vehicles, portable locations. **No longer has member endpoints** — those moved to `api/membersApi.js` (Session AE). **ITM-6 ✅:** `listItems` and `searchItems` now accept `stationId` option and append `station_id=` to the query string. |
| `api/membersApi.js` | — | Moved from `settings/api/` (Session AE). Member CRUD by `member_id` + CSV import/template (ACC-B6/B7/B8); `checkEmailAlignment` (LAUNCH-OPS9). The only frontend module that should call `/stations/{id}/members*` endpoints. |

### supply-room/  (Station Supplies — redesigned Session K)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 6 KB | Landing: 3 large cards (View Supplies, Count Supplies, Usage Log). Detects 404 → setup state with "Set Up Supply Room" button (calls POST supply-room). |
| `supply-room.css` | — | All supply-room CSS using design tokens |
| `api/supplyApi.js` | 3 KB | getSupplyRoom, createSupplyRoom (POST), catalog (SR-B1), patchCount (SR-B2), putLot (SR-F7), retireLot (RET-B5), CSV, station locations |
| `components/SupplyCatalogView.jsx` | — | SR-F3: catalog from SR-B1; items grouped by shelf; ⚠ Damaged badge (DMG-F3); per-shelf CompartmentParLevels add button for Supervisor+ (SS-F2). |
| `components/ReceiveStockPanel.jsx` | 8 KB | Manual add + CSV bulk upload |
| `components/TransferHistory.jsx` | 4 KB | Inbound/outbound transfer log |
| `components/UsageLogView.jsx` | — | Session N: Usage history — event rows with date/user/vehicle/items. |

### usage-log/  (After-Call Reset — Session N)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Orchestrator: loading → vehicle (if multiple) → item picker → submitting → done. Auto-skips vehicle step for single-vehicle stations. Filters: `v.active === true && !v.retired_at` — this was always correct and served as the reference pattern for fixing BUG-AD1 elsewhere (Session AD). |
| `api/usageApi.js` | — | logUsage (POST /checks/usage), getHistory (GET), getFrequentItems (GET frequent) |
| `components/UsageItemPicker.jsx` | — | Item picker with sections: "Used most often" (from history) or "Common items" (hardcoded defaults) + "All items". +/− controls. Selected items highlighted. 60px tap targets. |
| `usage-log.css` | — | All usage-log + history CSS using design tokens |

### vehicles/  (V&E Status)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 4 KB | Vehicle list with open-issue badges. `displayVehicles` filters out `v.retired_at` before computing in-service/out-of-service counts (BUG-AD1, Session AD). |
| `components/VehicleCard.jsx` | 9 KB | Vehicle detail + OOS/RTS toggle. Shows "Retired" badge instead of "Out of Service" and hides Report an Issue / Mark Out of Service / Return to Service entirely when `vehicle.retired_at` is set (BUG-AD1, Session AD — defensive layer in case a retired vehicle ever reaches this component). |
| `components/RepairRequestList.jsx` | 12 KB | Repair request list + status lifecycle |
| `components/RepairRequestForm.jsx` | 4 KB | File new repair request |

### help/  (Help & Tutorial screen — Session AQ)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Role-aware help screen. Crew-member section (7 accordions: shift-start check, after-call logging, status colors, missed checks, missing/expired items, repair reporting, auto-save draft). Supervisor section (4 accordions: compliance dashboard, FAIL triage, adding members, supply room stock — shown only when `canAccess(user, 'supervisor')`). Quick Reference grid (home screen buttons, role-filtered). "Show me the basics again" button + header button render `Tutorial` as overlay; `onDone` stays on Help screen, does not clear `ems_tutorial_complete`. No API calls — all content is static JSX. |
| `help.css` | — | Scoped to `.help-screen`. Accordion trigger/body/chevron, 2-col quick-reference grid (`.help-quick-grid`/`.help-quick-item`), replay button. Tokens only — no hardcoded hex/px. |

### check-history/
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | 6 KB | My Checks / All Checks tabs + detail navigation |
| `components/` | — | Check list items and detail view |

### settings/  (Station configuration — Admin-only config; Session Q/R, narrowed Session AE)
| File | Size | Purpose |
|------|------|---------|
| `index.jsx` | — | Settings screen orchestration. Visible to Supervisor+ for the check-workflow toggle row; everything else (StationManagementSection, VehicleManagementSection, RetiredListSection) is Admin only. Member management and the Email Alignment Check moved to Station Administration -> Members (Session AE, MERGE-1) — Settings no longer has any member UI. |
| `api/settingsApi.js` | — | `getSettings(stationId, getToken)`, `updateSettings(stationId, payload, getToken)` |
| `api/retirementApi.js` | — | `getStationVehicles`, `getStationLocations`, `retireVehicle`, `retireLocation`, `retireStation`, `getRetired` |
| `components/VehicleManagementSection.jsx` | — | S-F7/RET-F1/F2: lists active vehicles + portable locations with Retire buttons |
| `components/StationManagementSection.jsx` | — | S-F6/RET-F4: station info + Retire Station button |
| `components/RetiredListSection.jsx` | — | RET-F5: collapsible ▲/▼ section; three sub-lists |
| `settings.css` | — | Settings-screen-only styles (shell, toggle, retirement). Cross-module classes (`.settings-section`, `.settings-row`, `.badge`, `.member-*`, `.email-alignment__*`) moved to `index.css` (Session AE) since they're now used by both `settings/` and `admin/`. |

