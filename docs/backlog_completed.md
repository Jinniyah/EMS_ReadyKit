# EMS ReadyKit — Completed Items
# Last updated: 2026-06-11 (Session S: Pre-Launch Polish)
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S
# Active backlog -> docs/backlog.md

---

## Session S — Pre-Launch Polish (2026-06-11)
Tests TBD (user to confirm count after running pytest + npm test). No new migrations.

| # | Item | Description | Date |
|---|------|-------------|------|
| CQ-F2 | `compartmentList` dead state fix | Added `onCompartmentsLoaded` callback prop to `Step2Compartments`; fires `useEffect` when compartments load, populating `setCompartmentList` in wizard index. Fixes: progress bar never showing, Step3 prev/next arrows always disabled, Step5 compartment summary empty on FAIL checks. Also resets on `handleStartNew`. | 2026-06-11 |
| F-UX6 | Compartment location descriptor on cards | Already implemented in prior sessions — `location_descriptor` displays on all Step2 compartment card states and Step3 header. CSS class `.compartment-card__location` present. Confirmed done, no changes needed. | 2026-06-11 |
| CH-F6 | Acknowledgement / corrective note on checks | Already implemented in prior sessions — `CheckDetail.jsx` (check-history module) has `CommentPanel` with Add/Update Note flow using `acknowledgeCheck` endpoint; displays `reviewed_by` + timestamp. `CheckDetailPanel.jsx` (supervisor module) has equivalent. Confirmed done. | 2026-06-11 |
| SEED-GAP4 | Stretcher O2 PSI priority flag | Added `priority_check=True, priority_question="Stretcher O2 above 500 PSI?"` to Stretcher O2 PSI `add_par()` call in `seed.py`. `add_par` updates existing par levels on re-seed. | 2026-06-11 |
| SEED-GAP5 | Jump Bag O2 PSI priority flag | Added `priority_check=True, priority_question="Jump Bag O2 above 500 PSI?"` to Jump Bag O2 PSI `add_par()` call in `seed.py`. On-Board O2 PSI (DS EC 1) left non-priority — exterior compartment, less directly patient-facing. | 2026-06-11 |
| PERF-1 | Batch N+1 in `_auto_decrement_supply_room` | Replaced N per-item `db.query(StockLot)` calls with one batch query filtered by `StockLot.item_id.in_(...)`, grouped in Python. Ordering: `item_id, expiration_date asc` preserves FIFO correctness within each item group. | 2026-06-11 |
| F-UX4 | Expired item replacement prompt | Added `.item-row__replace-prompt` alert div in `ItemRow.jsx`: (1) below lot info when `isExpired(lot.expiration_date)` — "Lot expired — count any replacement stock and enter that quantity below"; (2) in `ExpiryDateInput` when entered date is past — "This item is expired — replace it and enter the new expiry date from the package". CSS added to `wizard.css`. | 2026-06-11 |
| FE-TEST-11 | `UsageItemPicker.test.jsx` | 13 tests: catalog renders; search filters by item_name + empty state; +/- controls call onQuantityChange; decrement disabled at 0; selected class applied; "Used most often" section + no history note when frequentItems provided; "Common items" section + history note when no history. | 2026-06-11 |
| FE-TEST-12 | `UsageLogScreen.test.jsx` | 6 tests: vehicle picker shown for multi-vehicle; auto-skipped for single vehicle; catalog items rendered in picker; Done calls logUsage with correct payload + shows done screen; "Nothing used" calls onBack without submitting; submit error shows alert. | 2026-06-11 |
| CQ-B3 | Extract helpers from `create_daily_check` | Extracted 4 helpers in `checks.py`: `_resolve_check_location` (vehicle/location validation), `_enforce_full_check_compartments` (compartment ID existence + requires_full_check enforcement), `_build_lot_map` (lot fetch + validate), `_build_line_items` (CheckLineItem ORM construction). No logic changes. Added `CheckLineItemCreate` import. `create_daily_check` reduced to ~35 lines of orchestration. | 2026-06-11 |

---

## Session R — Retirement + Security (2026-06-11)
381 tests passing. Migration 0023 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| RET-M1 | Alter `vehicles`: add retirement fields | Migration 0023: `retired_at` (DateTime nullable), `retired_by` (String 255 nullable), `retirement_reason` (String 500 nullable). Batch mode for SQLite compat. Fields added to `Vehicle` model. | 2026-06-11 |
| RET-M2 | Alter `locations`: add retirement fields | Same 3 fields added to `inventory_locations` table and `InventoryLocation` model. Combined with RET-M1/M3 in single migration 0023. | 2026-06-11 |
| RET-M3 | Alter `stations` and `stock_lots`: add retirement fields | Same 3 fields added to `stations` and `stock_lots` tables and their models. Combined in migration 0023. | 2026-06-11 |
| RET-B1 | `PATCH /vehicles/{id}/retire` — Admin only | New endpoint in `vehicles.py`. Sets `retired_at`, `retired_by`, `active=False`. 409 on double-retire. Writes VEHICLE_RETIRED audit event. | 2026-06-11 |
| RET-B2 | `PATCH /inventory/locations/{id}/retire` — Admin only | New endpoint in `inventory.py`. Same pattern. 409 on double-retire. Writes LOCATION_RETIRED audit event. | 2026-06-11 |
| RET-B3 | `PATCH /stations/{id}/retire` — Admin only | New endpoint in `stations.py`. Sets station retired and `active=False`. 409 on double-retire. Writes STATION_RETIRED audit event. | 2026-06-11 |
| RET-B4 | `GET /admin/retired?type=&station_id=` — Admin only | New endpoint in `admin.py`. `type` param validated against `^(vehicles\|locations\|stations)$` (422 otherwise). Returns list with id/name/retired_at/retired_by/reason. | 2026-06-11 |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` — Supervisor+ | New endpoint in `inventory.py`. Zeros quantity, sets retirement fields. 409 on double-retire. Writes STOCK_LOT_RETIRED audit event. Route registered BEFORE `/lots/{lot_id}` to avoid FastAPI path ambiguity. | 2026-06-11 |
| RET-B6 | `GET /inventory/lots/retired?location_id=` — Supervisor+ | New endpoint in `inventory.py`. Returns retired lots for a location ordered by retired_at desc. Route registered before `/lots/{lot_id}`. | 2026-06-11 |
| RET-F1 | Retire vehicle UI | `VehicleManagementSection.jsx`: lists active vehicles with Retire button. `RetireConfirmSheet` sub-component — reason textarea + Retire/Cancel. Calls `retirementApi.retireVehicle()`. | 2026-06-11 |
| RET-F2 | Retire portable location UI | `VehicleManagementSection.jsx`: separate section lists active portable (JUMP_BAG) locations with Retire button. Same confirm sheet pattern as RET-F1. | 2026-06-11 |
| RET-F3 | Retire inventory lot UI | `SupplyCatalogView.jsx`: "Dispose" button added to each lot row (beside "Correct expiry"). `sr-confirm-overlay`/`sr-confirm-sheet` confirmation with reason textarea. Calls `supplyApi.retireLot()`. | 2026-06-11 |
| RET-F4 | Retire station UI | `StationManagementSection.jsx`: shows station info + Retire Station button. If already retired, shows retired badge + reason. Calls `retirementApi.retireStation()`, then `onStationRetired()` (navigates back). | 2026-06-11 |
| RET-F5 | Retired objects list UI | `RetiredListSection.jsx`: collapsible section (▲/▼ toggle). Three sub-lists: Retired Vehicles, Retired Locations, Retired Stations. Uses `retirementApi.getRetired()`. | 2026-06-11 |
| S-F6 | Station management section in Settings | `StationManagementSection.jsx` added to `settings/index.jsx` admin block. See RET-F4. | 2026-06-11 |
| S-F7 | Vehicle management section in Settings | `VehicleManagementSection.jsx` added to `settings/index.jsx` admin block. See RET-F1/F2. | 2026-06-11 |
| S-F8 | Par level management in Settings | **Skipped** — depends on B-E9 (soft-deactivate par level endpoint, Session T). No code written. | 2026-06-11 |
| I-3 | `HTTPSRedirectMiddleware` | **Won't do** — Azure App Service terminates TLS at the platform/load balancer level before requests reach the Python process. Adding the middleware would break all requests (double-redirect). Documented in `docs/adr/ADR-006-Azure-AD-Token-Lifetime.md`. | 2026-06-11 |
| SEC-OPS1 | Monthly dependency audit workflow | New `.github/workflows/dependency-audit.yml`. Cron: 1st of each month at 08:00 UTC. Runs `pip-audit` on `app/requirements.txt` + `npm audit` in frontend. Opens a GitHub issue if findings above moderate severity. Also has `workflow_dispatch` trigger. | 2026-06-11 |
| TECH-1 | `pytest-cov` coverage reporting | Added `pytest-cov==6.1.0` to `requirements.txt`. Added `[tool.coverage.run]` and `[tool.coverage.report]` sections to `pyproject.toml`. Coverage is opt-in (`pytest --cov`), not forced in `addopts`. | 2026-06-11 |
| I-5 | Document Azure AD token lifetime | New `docs/adr/ADR-006-Azure-AD-Token-Lifetime.md`. Documents 1-hour access token, 90-day sliding refresh, MSAL silent refresh, and the HTTPSRedirectMiddleware decision. | 2026-06-11 |
| CQ-B1 | `check_type` coercion → `Item` model property | Added `check_type_value` property to `Item` model. Replaced two `hasattr(item.check_type, "value")` guards in `checks.py` with `item.check_type_value`. | 2026-06-11 |
| CQ-B2 | `_DATE` regex + `or_` import cleanup | `_DATE = re.compile(...)` moved to module level in `checks.py` (was compiled on every call). `from sqlalchemy import or_` moved from function body to top of `inventory.py`. | 2026-06-11 |

---

## Session Q — Station Settings + Membership (2026-06-10)
368 tests passing. Migration 0022 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| B-M10 | Alter `stations`: add `allow_check_modification` | Migration 0022 (`app/alembic/versions/0022_station_allow_check_modification.py`). Boolean column, `server_default=true()`, batch mode for SQLite compat. Column added to `Station` model. | 2026-06-10 |
| CH-B8 | `GET /stations/{id}/settings` — Supervisor+ | New endpoint in `stations.py`. Returns `StationSettingsRead` (station_id, allow_check_modification). Requires station membership. | 2026-06-10 |
| CH-B7 | `PATCH /stations/{id}/settings` — Admin only | New endpoint in `stations.py`. Accepts `StationSettingsPatch`. Writes STATION_SETTINGS_UPDATED audit event. Returns updated `StationSettingsRead`. | 2026-06-10 |
| ACC-F1 | Station picker uses `GET /stations/my` | Already implemented. Confirmed `station_members.py` router with GET/POST/PATCH/DELETE `/stations/{id}/members` endpoints and all frontend components in `admin/components/`. | 2026-06-10 |
| ACC-F2 | Member list view | Already implemented. See ACC-F1 note. | 2026-06-10 |
| ACC-F3 | Add member form | Already implemented. See ACC-F1 note. | 2026-06-10 |
| ACC-F4 | Remove member confirmation | Already implemented. See ACC-F1 note. | 2026-06-10 |
| ACC-F5 | "Pending assignment" screen | Already implemented. See ACC-F1 note. | 2026-06-10 |
| S-F1 | Settings nav entry | New lazy-loaded `SettingsScreen` module. Nav card added to `HomePage.jsx` (Supervisor+, disabled without station, ⚙️ icon). `modules/settings/index.jsx` orchestrates settings read/write. `modules/settings/settings.css` with token-based design. | 2026-06-10 |
| S-F3 | Allow check modification toggle | `modules/settings/index.jsx`: Admin sees interactive toggle (On/Off button). Supervisor sees read-only label. Non-supervisor note: "Contact your administrator". Toggle saves via `settingsApi.updateSettings`. | 2026-06-10 |

---

## Session P — Admin + Supply Room (2026-06-10)
364 tests passing. No new migrations.

| # | Item | Description | Date |
|---|------|-------------|------|
| RX-B2 | PATCH /admin/par-levels/{id} priority fields | Already implemented since migration 0015. Endpoint accepts `priority_check` (bool) and `priority_question` (VARCHAR 150). Confirmed and marked done. | 2026-06-10 |
| RX-F12 | Priority toggle + question in par level edit form | `CompartmentParLevels.jsx`: Edit row now shows "Priority item" checkbox and conditional "Custom check question" text input (max 150 chars). Saves via PATCH /admin/par-levels/{id}. ★ badge shown on assigned items where priority_check=True. | 2026-06-10 |
| DMG-F3 | Damaged item badge in supply catalog | `SupplyCatalogView.jsx`: Items with `is_damaged=True` show ⚠ Damaged badge. `get_supply_catalog` (SR-B1) extended to return `compartment_id`, `compartment_name`, `is_damaged` per item. Items grouped by shelf in the view. | 2026-06-10 |
| SS-B1 | PATCH /admin/locations/{id} label rename | New endpoint in `admin.py`. Admin only. Validates station membership. Writes LOCATION_RENAMED audit event. | 2026-06-10 |
| SS-F1 | Station Supplies admin screen | New `StationSuppliesScreen.jsx`. Fetches supply room → compartments. Shows each shelf with rename button + `CompartmentParLevels` (locationId=supplyRoom.location_id). "+ Add Shelf" adds compartments. Reachable via "Station Supplies" nav card in admin index. | 2026-06-10 |
| SS-F2 | "+ Add item" per shelf in View Supplies | `SupplyCatalogView.jsx`: Supervisor+ sees embedded `CompartmentParLevels` below each shelf section. Uses `locationId` prop (not vehicleId) for supply room compartments. | 2026-06-10 |
| ADMIN-F7 | Portable locations full CRUD (Jump Bags) | New `PortableLocationsScreen.jsx`. Lists JUMP_BAG/EQUIPMENT locations. Create / rename locations. Per-location `ShelfManager` with compartment CRUD + par levels. Reachable via "Jump Bags" nav card in admin index. | 2026-06-10 |
| SUP-F3 | Expiring items from EXPIRY_DATE checks | `get_expiring_soon` in `stations.py` extended with second subquery: finds most recent check per vehicle+item for EXPIRY_DATE items, surfaces those expiring within 30 days. Negative `line_item_id` used as synthetic lot_id to avoid key collision with stock lot IDs. | 2026-06-10 |

---

## Session O — Check Wizard UX + Responder Language (2026-06-10)
364 tests passing (0 xfailed — SEED-GAP2 enforcement cleared). Migration 0021 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| SEED-GAP2 | requires_full_check enforcement | `create_daily_check` now returns 422 if any compartment with `requires_full_check=True` has omitted line items. xfail test promoted to passing. | 2026-06-10 |
| RX-F3 | Single-station Step 1 collapse | Already implemented: Step1Vehicle.jsx has collapsible date/crew disclosure since Session M. Confirmed and marked done. | 2026-06-10 |
| RX-F4 | Simplify Step 5 for PASS | Already implemented: Step5Submit.jsx has PASS fast path (status badge + single submit, no compartment review). Confirmed and marked done. | 2026-06-10 |
| RX-F5 | Restock list persists on SubmittedScreen | Already implemented: SubmittedScreen.jsx has "View restock list" toggle for NEEDS_RESTOCK. Confirmed and marked done. | 2026-06-10 |
| RX-F9b | Priority "last confirmed" display | Step2Compartments.jsx priority cards now show "Last confirmed: [date] · [N] days ago" (amber >7 days, red >14 days) or "Last check: [date] — FAILED" or "Not yet confirmed". | 2026-06-10 |
| RX-F10 | Responder language + error messages | "Reconcile →" → "Review flagged items →" in Step2. `checkTypeLabel` updated (EXPIRY_DATE=Expiry date). Error messages updated: 401 → "Your session expired. Sign out and sign back in." / 403 → "You don't have permission to do that. Ask your supervisor if something seems wrong." | 2026-06-10 |
| RX-F13 | EXPIRY_DATE check type | New `ItemCheckType.EXPIRY_DATE` (stored as VARCHAR, no schema change). `_compute_line_item_status` returns EXPIRED when today > date_value. Migration 0021 updates AED Pads Adult + Pediatric to EXPIRY_DATE (recurrence_days=None). Frontend: deriveDraftItemStatus, checkTypeLabel, Step2 EXPIRY_DATE reading row (Same / Different UX), ItemRow ExpiryDateInput. | 2026-06-10 |
| SUP-F1 | Open repair count on compliance dashboard | Already implemented: supervisorApi fetches repair requests per vehicle, supervisor/index.jsx shows repair count alert. Confirmed and marked done. | 2026-06-10 |
| SUP-F2 | Repair count drill-down to V&E Status | Already implemented: repair count alert taps via onNavigateToVehicles. Confirmed and marked done. | 2026-06-10 |

---

## Session N — After-Call Reset + Usage Log (2026-06-10)
363 tests passing, 1 xfailed. Migration 0020 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| RX-B1 | POST /checks/usage | New `usage_events` + `usage_event_items` tables (migration 0020). FIFO stock lot decrement (best-effort, never blocks). Audit event "USAGE_LOGGED". GET history + GET frequent endpoints. 15 new tests in `test_usage.py`. | 2026-06-10 |
| RX-F6 | After-Call Reset flow | `modules/usage-log/` — vehicle auto-select if ≤1, item picker with frequency sections (Used most often / Common items / All items), +/− controls, ≤3 taps for typical case. "Log Items Used" hero button on home screen wired. Note shown while frequency data is being collected. | 2026-06-10 |
| RX-F11 | Tutorial slide updates | Updated all 3 Tutorial.jsx slides to reference "Log Items Used" button name and describe what each button does (Option B — improve existing slide content only, no new overlay UI). | 2026-06-10 |

---

## Session M — Unit 712 Inventory Corrections + Lint Cleanup (2026-06-09)

| Item | Description | Date |
|------|-------------|------|
| SEED-M1 | LUCAS Device: SUPPLY → FUNCTIONAL, priority_check=True, priority_question="LUCAS shows READY?" | 2026-06-09 |
| SEED-M2 | AED Pads Adult + Pediatric: added recurrence_days=730 for OVERDUE expiry tracking | 2026-06-09 |
| SEED-M3 | Stretcher O2 Tank w/ Regulator SUPPLY par level removed; Stretcher O2 PSI MEASUREMENT is canonical | 2026-06-09 |
| SEED-M4 | On-Board O2 Tank w/ Regulator 15LPM SUPPLY par level removed; On-Board O2 PSI MEASUREMENT is canonical | 2026-06-09 |
| SEED-M5 | Passenger Side EC 1 compartment removed from seed (empty on Unit 712); purge_stale_par_levels() cleans existing DBs | 2026-06-09 |
| SEED-M6 | Under Hood: restriction_note removed (not enforced), requires_full_check=True added | 2026-06-09 |
| SEED-M7 | get_or_create_item() now updates check_type + recurrence_days + unit_of_measure on re-seed so existing DBs pick up item changes | 2026-06-09 |
| SEED-M8 | make_compartment() now updates restriction_note on re-seed | 2026-06-09 |
| SEED-M9 | purge_stale_par_levels() helper added — removes retired par levels and empty compartments idempotently | 2026-06-09 |
| FE-M1 | Step2Compartments.jsx: readingPars suppressed for requires_full_check compartments — Truck Ops + Under Hood items no longer show inline on outer card | 2026-06-09 |
| FE-M2 | wizard.css: priority-card__body padding fixed (0 top → var(--space-sm)) — spacing between toggle row and expanded ItemRow | 2026-06-09 |
| LINT-M1 | ruff check: 117 violations cleared across 15 backend files + roleGuard.test.js; B904 added to pyproject.toml ignore list | 2026-06-09 |

## Post-Session L — Frontend Test Suite (2026-06-09)
Vitest + React Testing Library component tests. 10 new test files. No backend changes. Backend remains at 349 passed, 1 xfailed.

| # | Item | Completed |
|---|------|-----------|
| FE-TEST-INFRA | `__mocks__/@azure/msal-react.js` + `msal-browser.js` — root-level auto-mocks for MSAL; `MsalProvider`, `useMsal`, `useIsAuthenticated`, `PublicClientApplication`, `InteractionRequiredAuthError` | 2026-06-09 |
| FE-TEST-AUTH | `src/shared/hooks/__mocks__/useAuth.jsx` — manual mock with Jamie (Responder), Earl (Supervisor), Jennifer (Administrator) personas; mirrors `Bearer test-{role}` backend token pattern | 2026-06-09 |
| FE-TEST-1 | `roleGuard.test.js` — `canAccess()` all three roles; Session J regression: `canAccess(admin, 'admin')` alias returns true | 2026-06-09 |
| FE-TEST-2 | `DraftBanner.test.jsx` — hidden when no draft; station label; Resume calls onResume; Discard opens confirmation; multi-draft picker | 2026-06-09 |
| FE-TEST-3 | `WizardProgress.test.jsx` — step labels; aria-current active step; completed steps show ✓; progress bar aria-valuenow | 2026-06-09 |
| FE-TEST-4 | `Step1Vehicle.test.jsx` — vehicle list renders; OOS vehicles excluded; Continue disabled until selection; supply room auto-advance calls onSelect with STATION_SUPPLY_ROOM params | 2026-06-09 |
| FE-TEST-5 | `ItemRow.test.jsx` — all five check types (SUPPLY counter, MEASUREMENT number input, FUNCTIONAL pass/fail radios, DATE_RECORD date + Today button, DOCUMENT counter); confirmed/locked state; damaged badge show/hide; onMarkDamaged callback | 2026-06-09 |
| FE-TEST-6 | `SupplyLowStockPanel.test.jsx` — hidden when empty/null; amber vs red styling; expand/collapse; aria-expanded; out-of-stock count display | 2026-06-09 |
| FE-TEST-7 | `VehicleCard.test.jsx` — OOS badge; open repair count; RTS/OOS toggle visible to Supervisor, hidden from Responder; Report an Issue visible to all roles | 2026-06-09 |
| FE-TEST-8 | `ItemCatalog.test.jsx` — item list renders; search filters; add button visible to Supervisor+, hidden from Responder | 2026-06-09 |
| FE-TEST-9 | `StatusBadge.test.jsx` — correct label/severity for PASS, NEEDS_RESTOCK, FAIL; all LineItemStatus values | 2026-06-09 |
| FE-TEST-10 | `CheckHistory.test.jsx` — Responder sees only My Checks, no tabs; Supervisor sees All Checks + Deleted tabs; All Checks active by default for Supervisor; station name in header | 2026-06-09 |

---

## Post-Session L — Rate Limiting + CI Lint + Performance Index (2026-06-09)
349 tests passing, 1 xfailed. Rate limiting wired end-to-end; ruff in CI; migration 0019 deployed.

| # | Item | Completed |
|---|------|-----------|
| RATE-FIX | slowapi rate limiter wired: `core/limiter.py` singleton, `main.py` middleware, `POST /checks/daily` decorated; `check_date` server-derived from `timestamp`; `performed_by` uses `current_user.email`; `check_history.py` ownership checks updated; `TESTING=true` in `conftest.py` disables limiter in tests | 2026-06-09 |
| RATE-CI | `ruff check ems_readykit/` step added to `test-backend` job in `deploy.yml` (runs before pytest) | 2026-06-09 |
| RATE-MIG / PERF-2 | Migration 0019 — `ix_check_station_date` composite index on `daily_inventory_checks(station_id, check_date)`; model `__table_args__` updated | 2026-06-09 |
| RATE-DOCS | CLAUDE.md updated with rate limiting patterns: limiter location, TESTING flag, check_date server-derived, performed_by email; added to Key Architectural Decisions table | 2026-06-09 |

---

## Session L post-close — Safety Tests + Seed Integrity (2026-06-08)
349 tests passing, 1 xfailed (requires_full_check router enforcement — open in backlog as SEED-GAP2b).

| # | Item | Completed |
|---|------|-----------|
| TEST-SAFETY-1 | `test_safety_checks.py` — O2 PSI below minimum → LOW status (patient safety) | 2026-06-08 |
| TEST-SAFETY-2 | `test_safety_checks.py` — AED date recurrence overdue → OVERDUE → check FAIL | 2026-06-08 |
| TEST-SAFETY-3 | `test_safety_checks.py` — LUCAS date overdue at 31 days (30-day recurrence) | 2026-06-08 |
| TEST-SAFETY-4 | `test_safety_checks.py` — requires_full_check=True with all items passes; No Change xfail documents router gap | 2026-06-08 |
| TEST-SEED-1 | `test_seed_integrity.py` — Newberg/Marcellus/TEST stations exist and are active | 2026-06-08 |
| TEST-SEED-2 | `test_seed_integrity.py` — Unit 712 is BLS, belongs to Newberg, has inventory location | 2026-06-08 |
| TEST-SEED-3 | `test_seed_integrity.py` — Unit 712 Jump Bag exists; Unit 710 Jump Bag does NOT exist | 2026-06-08 |
| TEST-SEED-4 | `test_seed_integrity.py` — PC 8 has all 7 AED/LUCAS items with correct check types | 2026-06-08 |
| TEST-SEED-5 | `test_seed_integrity.py` — AED Battery priority_check=True, priority_question set | 2026-06-08 |
| TEST-SEED-6 | `test_seed_integrity.py` — AED Date of Last Charge recurrence_days=90 | 2026-06-08 |
| TEST-SEED-7 | `test_seed_integrity.py` — LUCAS Date of Last Charge recurrence_days=30 | 2026-06-08 |
| TEST-SEED-8 | `test_seed_integrity.py` — AED/LUCAS items have station_supply=False | 2026-06-08 |
| TEST-SEED-9 | `test_seed_integrity.py` — O2 PSI items have measurement_minimum=500.0 and correct compartments | 2026-06-08 |
| TEST-SEED-10 | `test_seed_integrity.py` — Truck Operations has requires_full_check=True and 10+ FUNCTIONAL items | 2026-06-08 |
| CONF-1 | `conftest.py` — `seeded_db` fixture: read-only connection to ems_readykit_dev.db; skips if absent | 2026-06-08 |
| SEED-FIX-1 | Removed orphan Unit 710 Jump Bag from Newberg Township seed (Unit 710 has no ambulance) | 2026-06-08 |
| DOCS-1 | CODEBASE_INDEX.md, project_index.md, README.md, CONTRIBUTING.md, architecture.md, osi_security_review.md — full documentation audit | 2026-06-08 |

---

## Session L — Automated Test Suite (2026-06-08)
304 tests passing on delivery.

| # | Item | Completed |
|---|------|-----------|
| TEST-P1 | `test_priority_items.py` — AED all four check types; FAIL preservation; immutability; priority flag DB persistence | 2026-06-08 |
| TEST-P2 | `test_priority_items.py` — LUCAS FUNCTIONAL + DATE_RECORD; FAIL original record preserved | 2026-06-08 |
| TEST-R1 | `test_persona_responder.py` — Jamie: all 5 check types; FAIL+comment+continue; multiple checks/day | 2026-06-08 |
| TEST-R2 | `test_persona_responder.py` — role boundary: 403 on admin endpoints (not 500); station today visibility | 2026-06-08 |
| TEST-S1 | `test_persona_supervisor.py` — Earl: check detail; acknowledge FAIL; repair file + resolve (resolution_notes) | 2026-06-08 |
| TEST-S2 | `test_persona_supervisor.py` — REGRESSION: write_audit_event actor/metadata kwargs (500 bug from Session J) | 2026-06-08 |
| TEST-S3 | `test_persona_supervisor.py` — station today view for shift handoff; supervisor role boundary | 2026-06-08 |
| TEST-A1 | `test_persona_admin.py` — Jennifer: admin superset of supervisor; all supervisor actions pass as admin | 2026-06-08 |
| TEST-A2 | `test_persona_admin.py` — supply room auto-decrement math; FUNCTIONAL items excluded from catalog | 2026-06-08 |
| TEST-A3 | `test_persona_admin.py` — REGRESSION: canAccess('admin') role alias; test-admin token acts as Administrator | 2026-06-08 |
| TEST-A4 | `test_persona_admin.py` — admin-only deactivation boundary; SUPERVISOR_PLUS item creation confirmed | 2026-06-08 |
| CONF-2 | `conftest.py` — auth header fixtures for all three personas | 2026-06-08 |

---

## Session K post-close — Production Fixes + Supply Room Setup (2026-06-06)
| # | Item | Completed |
|---|------|-----------|
| FIX-1 | Migration 0018 fix — added `CURRENT_TIMESTAMP` for `created_at`/`updated_at` in raw SQL INSERTs; `TimestampMixin` uses Python-side `default=` only | 2026-06-06 |
| FIX-2 | `POST /stations/{id}/supply-room` — get-or-create + Shelf 1–4; Supervisor+; fixes stations created via admin UI | 2026-06-06 |
| FIX-3 | Supply room screen — 404 detected as `roomMissing` state; shows "Set Up Supply Room" button; calls FIX-2 then loads normal UI | 2026-06-06 |
| FIX-4 | `app/initial_stock.csv` — 10 seed stock items ready to upload via Receive New Stock → CSV | 2026-06-06 |

---

## Session K — Supply Room Redesign (2026-06-06)
250 tests passing.

| # | Item | Completed |
|---|------|-----------|
| SR-M1 | Migration 0017: `station_supply` BOOL NOT NULL DEFAULT TRUE on `items` (Alembic batch mode) | 2026-06-06 |
| SR-SEED1 | `station_supply=False` for 29 items (AED, LUCAS, drugs, date checks) in seed.py | 2026-06-06 |
| SR-B1 | `GET /inventory/supply-catalog?station_id=` — on-hand counts; Responder+; 10 tests | 2026-06-06 |
| SR-B2 | `PATCH /inventory/supply-catalog/items/{id}/count` — FIFO lot adjustment; audit event; 10 tests | 2026-06-06 |
| SR-B3 | `GET /stations/{id}/supply-alerts` — items below par min; Supervisor+; 4 tests | 2026-06-06 |
| SR-B4 | `_auto_decrement_supply_room` in `create_daily_check`; best-effort; never blocks submit; 2 tests | 2026-06-06 |
| SR-B5 | `POST /inventory/transfer` removed; `TransferRequest` schema removed | 2026-06-06 |
| SR-F1 | "Station Supplies" home screen card — Responder+ visible; renamed from "Supply Room" | 2026-06-06 |
| SR-F2 | Supply room landing: 2 large nav cards (View Supplies, Count Supplies) + secondary text links | 2026-06-06 |
| SR-F3 | `SupplyCatalogView.jsx` — SR-B1 data; on-hand/par display; inline count correction (Supervisor+) | 2026-06-06 |
| SR-F4 | `Step1Vehicle.jsx` — auto-advance for supply room checks (`draft._supplyRoom=true`) | 2026-06-06 |
| SR-F5 | `SupplyLowStockPanel.jsx` on supervisor dashboard — red if out, amber if low; hidden if nothing low | 2026-06-06 |
| SR-F6 | `RestockVehiclePanel` removed from supply room routing | 2026-06-06 |
| SR-F7 | Inline lot expiry editor in `SupplyCatalogView` — uses `PUT /inventory/lots/{id}`; Supervisor+ only | 2026-06-06 |

---

## Session J — UX Polish + Bug Fixes (2026-06-06)
237 tests passing.

| # | Item | Completed |
|---|------|-----------|
| CH-F7 CSS | Deleted records list styling in check-history.css | 2026-06-06 |
| CH-F8 CSS | Hard-delete confirmation modal styling | 2026-06-06 |
| F-UX2 | Left/right chevron navigation between compartments — confirmed already built | 2026-06-06 |
| F-UX3 | Sticky jump-to-next-unvalidated button (Step2Compartments.jsx + wizard.css) | 2026-06-06 |
| B-E8 | `PUT /inventory/lots/{id}` — correct expiry date on lot; 6 new tests | 2026-06-06 |
| BUG-J1 | `canAccess(user, 'admin')` silently returned false — added 'admin' alias to roleGuard.js | 2026-06-06 |
| BUG-J2 | `patch_item_status` used wrong `write_audit_event` kwargs (performed_by/detail → actor/metadata) — 500 on mark/clear damaged | 2026-06-06 |
| DMG-F1 | Mark Damaged / Clear Damaged on ItemRow actions bar (all roles, any item) | 2026-06-06 |
| DOCS-J | Backlog cleaned — 164 → 106 open items; 3 architectural decisions added to CLAUDE.md | 2026-06-06 |

---

## Session I — Features (2026-06-05)
231 tests passing.

| # | Item | Completed |
|---|------|-----------|
| RX-F3 | Collapse Step 1 for single-station users | 2026-06-05 |
| RX-F4 | Simplify Step 5 for clean PASS | 2026-06-05 |
| RX-F5 | Restock list persists on SubmittedScreen | 2026-06-05 |
| RX-F10 | Responder-facing language + error message replacement | 2026-06-05 |
| RX-F11 | First-run tutorial — Tutorial.jsx, 3 screens, ems_tutorial_complete flag | 2026-06-05 |
| SUP-F1 | Open repair count on compliance dashboard header | 2026-06-05 |
| SUP-F3 | Expiring items alert on compliance dashboard | 2026-06-05 |
| DMG-B1 | Migration 0016: `is_damaged` on `par_levels` | 2026-06-05 |
| DMG-B2 | `PATCH /inventory/items/{id}/status` — damaged flag on par level | 2026-06-05 |
| DMG-F2 | Damaged item badge in compartment preview; No Change blocked for damaged items | 2026-06-05 |
| CH-F7 | Deleted records screen — Supervisor+ tab in Check History (CSS deferred to Session J) | 2026-06-05 |
| CH-F8 | Force hard-delete confirmation modal — Administrator only (CSS deferred to Session J) | 2026-06-05 |

---

## Session H — Published to Production (2026-06-05)
231 backend tests passing. 63/63 frontend tests passing. 0 npm vulnerabilities.

| # | Item | Completed |
|---|------|-----------|
| RX-F1 | Home screen "Check the Truck" hero button + "Log Items Used" secondary | 2026-06-05 |
| RX-F2 | Auto-confirm supply items at par | 2026-06-05 |
| RX-F7 | "Save compartment" → "Done — [Name]" / "Next — [Name]" | 2026-06-05 |
| RX-F8 | No Change / Modify compartment flow — stock preview; No Change attests at par; Undo | 2026-06-05 |
| RX-F8a | No Change — writes all line items with quantity_found = min_quantity | 2026-06-05 |
| RX-F9 | Priority items section — pinned above compartment list in Step 2 | 2026-06-05 |
| RX-F9a | Priority item custom question text from par_level.priority_question | 2026-06-05 |
| SEED-GAP1 | "LUCAS Device Ready Check" FUNCTIONAL item added to seed.py PC 8 | 2026-06-05 |
| SEED-GAP2 | `requires_full_check=True` set in seed.py for Truck Operations compartment (data only — router enforcement is open, see backlog) | 2026-06-05 |
| SEED-GAP3 | AED Battery `priority_check=True`, `priority_question="AED shows READY?"` in seed.py | 2026-06-05 |
| SEC-H1 | HTTPSRedirectMiddleware — documented as intentionally omitted; Azure "HTTPS Only" platform setting handles it | 2026-06-05 |
| SEC-H2 | MSAL `cacheLocation: "sessionStorage"` — confirmed already set | 2026-06-05 |
| SEC-H3 | `/health` returns `{"status": "ok"}` only — env field removed | 2026-06-05 |
| SEC-PRE1 | `staticwebapp.config.json` — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, SWA routing | 2026-06-05 |
| SEC-PRE2 | `npm audit --audit-level=high` added to CI frontend job | 2026-06-05 |
| SEC-PRE3 | `seed.py` production guard + `startup.sh` APP_ENV check | 2026-06-05 |
| SEC-PRE4 | ESLint (eslint@8, react-hooks plugin) + lint script + CI step (0 warnings) | 2026-06-05 |
| TECH-THEME1–4 | CSS token enforcement across all module CSS files | 2026-06-05 |
| FIX-H1 | npm audit — vite 5→7, vitest 1→4, @vitejs/plugin-react 4→5; resolved GHSA-5xrq-8626-4rwp (CVSS 9.8) | 2026-06-05 |
| FIX-H2 | Migration 0014 boolean 0/1 → True/False for PostgreSQL | 2026-06-05 |
| FIX-H3 | Station bleed — my-history scoped by station_id | 2026-06-05 |
| FIX-H4 | Vehicle on-hand computed from last check quantity_found, not stock lots | 2026-06-05 |
| FIX-H5 | No Change 422 + FAIL — compartment_id stored on draft; MEASUREMENT excluded from No Change line items | 2026-06-05 |

---

## Session G — Supply Room & Restocking (2026-06-03)

| # | Item | Completed |
|---|------|-----------|
| SUPPLY-M1 | `STATION_SUPPLY_ROOM` auto-created per station | 2026-06-03 |
| SUPPLY-B1 | `POST /inventory/transfer` | 2026-06-03 |
| SUPPLY-B2 | `GET /inventory/locations/{id}/stock-summary` | 2026-06-03 |
| SUPPLY-B3 | `GET /stations/{id}/supply-room` | 2026-06-03 |
| SUPPLY-F1 | Supply room stock view | 2026-06-03 |
| SUPPLY-F2 | Restock vehicle flow | 2026-06-03 |
| SUPPLY-F3 | Receive stock into supply room | 2026-06-03 |
| SUPPLY-F4 | Transfer history | 2026-06-03 |

---

## Session F — Station Setup, Compliance Calendar & Par Levels (2026-05-30 → 2026-06-01)
217 tests passing. All Block 5 UAT test cases pass.

| # | Item | Completed |
|---|------|-----------|
| B-M11 | Migration 0011: `primary_color` on stations | 2026-05-30 |
| NEW-M1 | Migration 0011: `vehicle_color` on vehicles | 2026-05-30 |
| NEW-M2 | Migration 0012: `call_sign` on stations | 2026-05-30 |
| BLOCK-1 | Color system: `primary_color` on stations, `vehicle_color` on vehicles, `ColorPickerWidget` | 2026-05-30 |
| BLOCK-2 | Add Station: `call_sign`, `POST /admin/stations`, "+ Add Station" form | 2026-05-30 |
| BLOCK-3 | Compliance Calendar: `ComplianceCalendar.jsx`, 90-day rolling, per-vehicle color rows | 2026-05-30 |
| BLOCK-4 | Last Check Banner: `LastCheckBanner.jsx` on home screen | 2026-05-30 |
| BLOCK-5 | Par Level Assignment UI: vehicle-centric view, `CompartmentParLevels.jsx`, inline add/edit/remove | 2026-05-30 |
| BLOCK-6 | UAT document: `docs/uat_test_cases.md` | 2026-06-01 |
| RX-M1 | Migration 0015: `priority_check` + `priority_question` on `par_levels`; `requires_full_check` on `compartments` | 2026-06-05 |
| — | Migration 0013: `vehicle_id` nullable on `daily_inventory_checks`; `location_id` FK for portable checks | 2026-05-30 |
| — | Migration 0009: `items` — add `ai_tags`, `alternate_names`, `reference_image_url`, `barcode` | 2026-05-30 |
| — | Migration 0010: `par_levels` — add `active` flag with index | 2026-05-30 |
| F-UX7 | Last Check Banner on home screen | 2026-05-30 |
| B-E5 | `POST /inventory/transfer` — move stock between locations | 2026-05-30 |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` — stock vs par per item | 2026-05-30 |

---

## Session E — Admin Redesign, Item Catalog & Vehicle Management (2026-05-30)
200+ tests passing. 0 CVEs.

| # | Item | Completed |
|---|------|-----------|
| ADMIN-UX1-F1–F8 | Admin redesigned — station header + 3 nav cards (Members, Item Catalog, Vehicles) | 2026-05-30 |
| ADMIN-B1–B10 | Full item catalog endpoints including typeahead search | 2026-05-30 |
| ADMIN-B17 | CSV bulk import with template download | 2026-05-30 |
| ADMIN-B18 | CSV template download endpoint | 2026-05-30 |
| ADMIN-F1–F5 | Item catalog frontend | 2026-05-30 |
| ADMIN-F11 | Par level assignment UI — item-centric | 2026-05-30 |
| ADMIN-UX1-B1 | `PATCH /inventory/compartments/{id}` | 2026-05-30 |
| FIX-E1 | Check wizard 403 bug fix | 2026-05-30 |
| FIX-E2 | Sort order input, station selection, OOS form, repair list for Responders fixes | 2026-05-30 |
| FIX-E3 | Check History read-only enforcement | 2026-05-30 |

---

## Session D — Features (2026-05-29)
200+ tests passing.

| # | Item | Completed |
|---|------|-----------|
| B-E3 | `GET /checks/daily/station/{id}?from=&to=` — date-range compliance query | 2026-05-29 |
| VE-F5 | Open issue badge on V&E Status home card | 2026-05-29 |
| VE-F5b | Vehicle card badge on mount — repair list fetched eagerly | 2026-05-29 |
| D-R1 | Documentation audit — README + project_index.md rewritten; 14 stale files archived | 2026-05-29 |

---

## Session C — Access Control Enforcement (2026-05-29)
179 tests passing. OWASP A01 enforcement complete.

| # | Item | Completed |
|---|------|-----------|
| ACC-B7 | Station membership enforced on all `/checks` endpoints | 2026-05-29 |
| ACC-B8 | Station membership enforced on all `/vehicles` and `/inventory` endpoints | 2026-05-29 |
| ACC-B9 | Supervisor dashboard endpoints enforced via ACC-B7/B8 | 2026-05-29 |
| — | Human-readable error messages on 401/403 throughout | 2026-05-29 |
| — | 26 new tests in `test_station_membership.py` | 2026-05-29 |

---

## Session B — Refactor Sprint (2026-05-27)
153 tests passing. 0 deprecation warnings.

| # | Item | Completed |
|---|------|-----------|
| REF-1 | `write_audit_event()` extracted to `core/audit.py` | 2026-05-27 |
| REF-2 | `get_vehicle_or_404()` moved to `deps.py` | 2026-05-27 |
| REF-3 | `ALL_ROLES`, `SUPERVISOR_PLUS`, `ADMIN_ONLY` moved to `deps.py` | 2026-05-27 |
| REF-4 / ACC-B10 | `require_station_membership()` moved to `deps.py` | 2026-05-27 |
| REF-5 | CSS files merged into `src/styles/wizard.css` | 2026-05-27 |
| REF-6 | All `logger.warning()` calls in `auth.py` include `extra={}` | 2026-05-27 |
| REF-7 | `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT` | 2026-05-27 |
| FIX-B1 | MSAL popup→redirect flow; `msalInstance.initialize()` awaited; `handleRedirectPromise()` removed | 2026-05-27 |

---

## Session A — Security Gate (2026-05-26)
153 tests passing. pip-audit 0 CVEs.

| # | Item | Completed |
|---|------|-----------|
| SEC-1 | `pip-audit` step added to CI before pytest | 2026-05-26 |
| SEC-2 | Disable OpenAPI `/docs`, `/redoc`, `/openapi.json` in production | 2026-05-26 |
| SEC-3 | Security headers middleware (`X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`) | 2026-05-26 |
| SEC-4 | Startup assertion: fail loud if `SECRET_KEY == "change-me-in-production"` | 2026-05-26 |
| SEC-5a–d | Structured `logger` calls in inventory/stations/vehicles/items routers | 2026-05-26 |
| SEC-6 | Document `secondary_signer` free-text limitation in checks.py | 2026-05-26 |
| DEP-1 | Dependency upgrades: fastapi 0.111→0.136.1, starlette 0.37→1.1, pydantic 2.7→2.13, PyJWT 2.8→2.12, cryptography 42→46; resolved 12+ CVEs | 2026-05-26 |
| CLEAN-1 | Dead code removed: `routers/_patch_cs_message.py`, `routers/_patch_get_check.py`, `tests/test_rbac_block.py` | 2026-05-26 |
| CLEAN-2 | `ems_readykit_dev.db` and `deploy.zip` added to `.gitignore` | 2026-05-26 |

---

## Pre-Session — Foundation (before Session A)

| # | Item | Completed |
|---|------|-----------|
| B-T1 | `TestCheckTypes` class: MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, Jump Bag location | 2026-05-22 |
| B-T2 | `test_multiple_checks_same_vehicle_same_day_all_succeed` | 2026-05-22 |
| B-M0 | Migration 0005: drop `uq_check_vehicle_date`; non-unique `ix_check_vehicle_date` | 2026-05-22 |
| B-M1 | New table: `repair_requests` | 2026-05-23 |
| B-M5 | `vehicles`: add `inactive_reason`, `inactive_since` | 2026-05-23 |
| B-M7 | `daily_inventory_checks`: add `reviewed_by`, `reviewed_at`, `corrective_action` | 2026-05-23 |
| B-M9 | `daily_inventory_checks`: add `deleted_at`, `deleted_by`, `deletion_reason`, `force_deleted` | 2026-05-23 |
| B-E0 | `GET /api/v1/stations/{id}/locations` | 2026-05-22 |
| B-E1 | `PATCH /vehicles/{id}` — mark vehicle active/inactive | 2026-05-23 |
| B-E2 | `PATCH /checks/daily/{id}/acknowledge` — supervisor corrective action | 2026-05-23 |
| B-E4 | `POST /vehicles/{id}/repair-requests` — file repair request | 2026-05-23 |
| B-E16 | `PATCH /vehicles/{id}/repair-requests/{rid}` — update repair request status | 2026-05-23 |
| B-E17 | `GET /vehicles/{id}/repair-requests` — list repair requests for vehicle | 2026-05-23 |
| F-5E1 | Repair request form — severity selector, description, URGENT escalation | 2026-05-23 |
| F-5E2 | Mark vehicle inactive toggle (Supervisor+) | 2026-05-23 |
| F-5E3 | Repair request status tracking display | 2026-05-23 |
| VE-F1 | Rename "Vehicle Status" → "Vehicle & Equipment Status" | 2026-05-23 |
| CH-B1 | `GET /checks/daily/my-history` | 2026-05-23 |
| CH-B2 | `GET /checks/daily/{id}/detail` | 2026-05-23 |
| CH-B3 | `DELETE /checks/daily/{id}` — soft-delete | 2026-05-23 |
| CH-F1 | "My Checks" screen | 2026-05-23 |
| CH-F2 | Check detail view (read-only for Responders) | 2026-05-23 |
| CH-F3 | Supervisor acknowledgement on check detail | 2026-05-23 |
| CH-F4 | Supervisor check history list — filterable by status | 2026-05-23 |
| CH-F5 | Soft-delete check (Supervisor+) — mandatory reason | 2026-05-23 |
| F-UX1 | Station picker on home screen | 2026-05-16 |
| F-UX11–F-UX16 | Check wizard UX: discard modal, color tiers, compartment badges, force-confirm, jump bags | 2026-05-21 |
| F-UX17–F-UX31 | Check wizard: Reconcile, 5 steps, back routing, DATE_RECORD Today, multiple checks/day, DraftBanner, top-off button | 2026-05-22 |
| F-UX33 | FAIL check → repair request prompt on submitted screen | 2026-05-23 |
| F-UX35 | Draft banner station fallback — localStorage cache | 2026-05-25 |
| F-5H1–F-5H4 | Azure Static Web Apps provisioning and CI/CD 4-job pipeline | 2026-05-24 |
| I-7 | Azure deployment healthy — App Service B1, VNet, CI/CD green | 2026-05-24 |