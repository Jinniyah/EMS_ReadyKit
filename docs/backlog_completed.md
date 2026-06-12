# EMS ReadyKit — Completed Items
# Last updated: 2026-06-12 (Session V: Administrator + Supervisor UAT complete)
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V
# Active backlog -> docs/backlog.md

---

## Session V — UAT Continued (2026-06-12)
Administrator and Supervisor UAT both complete. Four bugs found and fixed.
No new migrations. Test count to be confirmed after commit + pytest run.

| # | Item | Description | Date |
|---|------|-------------|------|
| UAT-3 | Supervisor UAT — confirmed complete | All Supervisor test cases passed (carried from Session U close). | 2026-06-12 |
| UAT-4 | Administrator UAT — confirmed complete | All Administrator test cases executed against live Azure deployment. All pass. | 2026-06-12 |
| UAT-BUG4 | Step 5 progress bar shows "Vehicle" for Supply Room check | `WizardProgress` had step labels hardcoded as `['Vehicle', 'Compartments', ...]`. Added `selectionLabel` prop; step 1 now uses `selectionLabel || 'Vehicle'`. Orchestrator passes `selectionLabel={selectionLabel}` to `WizardProgress`. Supply Room checks now correctly show "Station Supply Room". | 2026-06-12 |
| UAT-BUG5 | Step 5 check subject shows "This check" for Supply Room | `initialDraft` created by `HomePage.onCountSupplies` had no `selection_label` field, so the orchestrator initialized `selectionLabel` to `''`. Fixed: added `selection_label: 'Station Supply Room'` directly to the `initialDraft` object in `HomePage` so it is present on mount and on draft resume. | 2026-06-12 |
| UAT-BUG6 | Step 5 check date blank for Supply Room check | `displayDate = checkDate ?? draft?.check_date` could resolve to undefined. Added `?? todayIso()` final fallback in `Step5Submit`. Also imported `todayIso` from `dateHelpers.js`. | 2026-06-12 |
| UAT-BUG7 | Supply Room check submission did not update View Supplies | **Root cause (architectural gap):** `View Supplies` reads `on_hand` from `sum(StockLot.quantity)`. Check wizard submission recorded `quantity_found` as check line items but nothing reconciled those counts back to stock lots. `_auto_decrement_supply_room` (SR-B4) only fires for vehicle checks (`payload.vehicle_id` set). **Fix:** Added `_reconcile_supply_room_check()` (SR-B5) to `checks.py`. Called from `create_daily_check` when the location type is `STATION_SUPPLY_ROOM`. For each SUPPLY line item: `quantity_found < on_hand` => FIFO deduction from existing lots; `quantity_found > on_hand` => new adjustment lot; equal => no change. Same FIFO logic as `patch_supply_catalog_count` (SR-B2). Best-effort: never raises, always lets the check save. | 2026-06-12 |

---

## Session U — UAT Dress Rehearsal (2026-06-12)
418 backend tests passing, 201 npm tests passing. Supervisor UAT complete — all cases pass.
Three bugs found and fixed during UAT. No new migrations.

| # | Item | Description | Date |
|---|------|-------------|------|
| UAT-3 | Supervisor UAT | All Supervisor test cases executed against live Azure deployment. All pass. | 2026-06-12 |
| UAT-BUG1 | Log Items Used — no ambulance buttons | `buildUnits` in `usage-log/index.jsx` filtered `v.status === 'ACTIVE'` — field does not exist on Vehicle API response. All vehicles were filtered out silently. Fixed to `v.active === true && !v.retired_at`. Also switched to `getActiveStationVehicles`. Test fixtures in `UsageLogScreen.test.jsx` had same wrong shape — both fixed. | 2026-06-12 |
| UAT-BUG2 | No Change bypassed Reconcile when items were short | `buildNoChangeLineItems` used `quantity_found: pl.min_quantity`. Fixed to `lastQtyMap[pl.item_id] ?? pl.min_quantity` so actual last-known quantities are preserved. Short items now surface in Reconcile. | 2026-06-12 |
| UAT-BUG3 | Flaky test — UNIQUE constraint on vehicle_number | `_make_setup` used `vehicle_number=f"LR-{id(station)}"` — same value for all 5 tests sharing the same fixture instance. Fixed to `uuid4().hex[:12]`. | 2026-06-12 |
| CLAUDE-U1 | `filesystem:edit_file` permanently banned | Added hard rule to CLAUDE.md: always use `filesystem:write_file`. The edit tool silently fails on Windows CRLF files — reports success but leaves the file unchanged. | 2026-06-12 |
| CLAUDE-U2 | Vehicle API shape documented in CLAUDE.md | No `status` field exists. Filter: `v.active === true && !v.retired_at`. Added to Key Architectural Decisions table. | 2026-06-12 |

---

## Session U (earlier) — Damaged Items Dashboard (2026-06-12)
410 backend tests passing after SUP-DMG1 work.

| # | Item | Description | Date |
|---|------|-------------|------|
| SUP-DMG-FIX1 | Compliance dashboard FAIL banner fix | FAIL banner persisted after repair resolved. Switched to `unresolvedFail` count — banner only when FAIL check AND open repair both present. | 2026-06-12 |
| SUP-DMG1 | `GET /stations/{id}/damaged-items` endpoint | New endpoint in `stations.py`. Returns par levels with `is_damaged=True`. Supervisor+ + station membership enforced. | 2026-06-12 |
| SUP-DMG1-FE | Damaged items panel on compliance dashboard | Collapsible `DamagedItemsPanel`. Green banner only when no FAIL + no damaged items. | 2026-06-12 |
| SUP-DMG1-TEST | `test_damaged_items.py` — 13 tests | Happy path, portable locations, retired excluded, inactive excluded, station isolation, RBAC, 404. | 2026-06-12 |

---

## Session T — Admin Backend (2026-06-11)
Migration 0024 added.

| # | Item | Description | Date |
|---|------|-------------|------|
| B-M6 | `par_levels` deactivation fields | Migration 0024: `deactivated_at` + `deactivation_reason` on `par_levels`. | 2026-06-11 |
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate with reason + membership check + PAR_DEACTIVATED audit event. | 2026-06-11 |
| B-E18 | `GET /audit?from_date=&to_date=` | Date-range filter on audit log. | 2026-06-11 |
| AI-B1 | `PATCH /admin/items/{id}/ai-fields` | Admin-only. Updates ai_tags/alternate_names/reference_image_url/barcode. | 2026-06-11 |
| AI-F1 | AI fields editor — admin-only gate | ItemForm AI section hidden for non-admins. | 2026-06-11 |
| S-F8 | Par level management — confirm+reason flow | Inline ConfirmRemoveRow with reason textarea. | 2026-06-11 |

---

## Session S — Pre-Launch Polish (2026-06-11)
No new migrations.

| # | Item | Description | Date |
|---|------|-------------|------|
| CQ-F2 | `compartmentList` dead state fix | `onCompartmentsLoaded` callback prop added to Step2; fixes progress bar, Step3 nav, Step5 summary. | 2026-06-11 |
| F-UX6 | Compartment location descriptor | Confirmed already implemented. | 2026-06-11 |
| CH-F6 | Acknowledgement / corrective note | Confirmed already implemented. | 2026-06-11 |
| SEED-GAP4 | Stretcher O2 PSI priority flag | `priority_check=True, priority_question="Stretcher O2 above 500 PSI?"` | 2026-06-11 |
| SEED-GAP5 | Jump Bag O2 PSI priority flag | `priority_check=True, priority_question="Jump Bag O2 above 500 PSI?"` | 2026-06-11 |
| PERF-1 | Batch N+1 in `_auto_decrement_supply_room` | One batch query instead of N per-item queries. | 2026-06-11 |
| F-UX4 | Expired item replacement prompt | Alert div in ItemRow + ExpiryDateInput when expired. | 2026-06-11 |
| FE-TEST-11 | `UsageItemPicker.test.jsx` | 13 tests. | 2026-06-11 |
| FE-TEST-12 | `UsageLogScreen.test.jsx` | 6 tests. | 2026-06-11 |
| CQ-B3 | Extract helpers from `create_daily_check` | 4 helpers extracted; handler reduced to ~35 lines. | 2026-06-11 |

---

## Session R — Retirement + Security (2026-06-11)
381 tests passing. Migration 0023 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| RET-M1/M2/M3 | Retirement fields on vehicles/locations/stations/lots | Migration 0023: `retired_at`, `retired_by`, `retirement_reason`. Batch mode. | 2026-06-11 |
| RET-B1--B6 | Retire endpoints (vehicle/location/station/lot) + retired list | Admin/Supervisor+. 409 on double-retire. Audit events. | 2026-06-11 |
| RET-F1--F5 | Retire UI (vehicle/location/station/lot) + retired list | Settings screen retirement flows with confirm sheet + reason textarea. | 2026-06-11 |
| S-F6/F7 | Station + vehicle management in Settings | StationManagementSection + VehicleManagementSection in settings/index.jsx. | 2026-06-11 |
| I-3 | HTTPSRedirectMiddleware | Won't do — Azure terminates TLS at platform level. Documented ADR-006. | 2026-06-11 |
| SEC-OPS1 | Monthly dependency audit workflow | `.github/workflows/dependency-audit.yml`. pip-audit + npm audit, opens GitHub issue. | 2026-06-11 |
| TECH-1 | pytest-cov coverage reporting | Added to requirements.txt + pyproject.toml. | 2026-06-11 |
| I-5 | Azure AD token lifetime ADR | `docs/adr/ADR-006-Azure-AD-Token-Lifetime.md`. | 2026-06-11 |
| CQ-B1/B2 | check_type property + regex/import cleanup | `check_type_value` property on Item; `_DATE` at module level. | 2026-06-11 |

---

## Session Q — Station Settings + Membership (2026-06-10)
368 tests passing. Migration 0022 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| B-M10 | `allow_check_modification` on stations | Migration 0022. Boolean, server_default=true. | 2026-06-10 |
| CH-B7/B8 | Station settings GET/PATCH | Supervisor+ read, Admin write. Audit event. | 2026-06-10 |
| ACC-F1--F5 | Station membership frontend | Confirmed implemented. | 2026-06-10 |
| S-F1/F3 | Settings nav + allow_check_modification toggle | Admin interactive, Supervisor read-only. | 2026-06-10 |

---

## Session P — Admin + Supply Room (2026-06-10)
364 tests passing. No new migrations.

| # | Item | Description | Date |
|---|------|-------------|------|
| RX-B2/F12 | Priority flag backend + admin UI | Backend confirmed. Priority checkbox + question field in CompartmentParLevels. | 2026-06-10 |
| DMG-F3 | Damaged item badge in supply catalog | ⚠ Damaged badge. Items grouped by shelf. | 2026-06-10 |
| SS-B1/F1/F2 | Supply room admin screen + shelf + add-item | Rename endpoint, StationSuppliesScreen, embedded CompartmentParLevels per shelf. | 2026-06-10 |
| ADMIN-F7 | Portable locations CRUD | PortableLocationsScreen.jsx. | 2026-06-10 |
| SUP-F3 | Expiring items — EXPIRY_DATE check type | get_expiring_soon extended. | 2026-06-10 |

---

## Session O — Check Wizard UX + Responder Language (2026-06-10)
364 tests passing. Migration 0021 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| SEED-GAP2 | requires_full_check enforcement | 422 on missing line items. | 2026-06-10 |
| RX-F3/F4/F5 | Step 1 collapse, Step 5 PASS fast path, restock list | Confirmed done. | 2026-06-10 |
| RX-F9b | Priority last-confirmed display | Amber >7d, red >14d. | 2026-06-10 |
| RX-F10 | Responder language + error messages | Plain English throughout. | 2026-06-10 |
| RX-F13 | EXPIRY_DATE check type | Migration 0021. EXPIRED when today > date_value. | 2026-06-10 |
| SUP-F1/F2 | Open repair count + drill-down | Confirmed done. | 2026-06-10 |

---

## Session N — After-Call Reset + Usage Log (2026-06-10)
363 tests passing, 1 xfailed. Migration 0020 applied.

| # | Item | Description | Date |
|---|------|-------------|------|
| RX-B1 | POST /checks/usage | usage_events + usage_event_items. FIFO decrement. 15 tests. | 2026-06-10 |
| RX-F6 | After-Call Reset flow | modules/usage-log/ with vehicle auto-select, item picker, +/- controls. | 2026-06-10 |
| RX-F11 | Tutorial slide updates | All 3 slides reference "Log Items Used". | 2026-06-10 |

---

## Session M — Unit 712 Inventory Corrections + Lint (2026-06-09)

| Item | Description | Date |
|------|-------------|------|
| SEED-M1--M9 | LUCAS FUNCTIONAL, AED Pads recurrence, O2 par level cleanup, compartment corrections, re-seed idempotency | 2026-06-09 |
| FE-M1/M2 | requires_full_check reading suppression, priority card padding fix | 2026-06-09 |
| LINT-M1 | 117 ruff violations cleared across 15 backend files | 2026-06-09 |

---

## Post-Session L — Frontend Tests + Rate Limiting (2026-06-08/09)
349 passed, 1 xfailed. 10 frontend test files.

| # | Item | Completed |
|---|------|-----------|
| FE-TEST-INFRA--10 | MSAL mocks, useAuth mock, 10 component test files | 2026-06-09 |
| RATE-FIX | slowapi rate limiter; TESTING flag; check_date server-derived; performed_by email | 2026-06-09 |
| RATE-CI | ruff in CI; migration 0019 composite index | 2026-06-09 |

---

## Session L — Automated Test Suite (2026-06-08)
304 tests passing.

| # | Item | Completed |
|---|------|-----------|
| TEST-P1/P2 | `test_priority_items.py` | 2026-06-08 |
| TEST-R1/R2 | `test_persona_responder.py` | 2026-06-08 |
| TEST-S1--S3 | `test_persona_supervisor.py` | 2026-06-08 |
| TEST-A1--A4 | `test_persona_admin.py` | 2026-06-08 |
| CONF-1/2 | `conftest.py` — seeded_db fixture + auth headers | 2026-06-08 |
| SEED-FIX-1 | Removed orphan Unit 710 Jump Bag | 2026-06-08 |
| DOCS-1 | Full documentation audit | 2026-06-08 |

---

## Sessions A--K — Foundation through Supply Room (2026-05-26 to 2026-06-06)
Full history in git. Highlights: Azure AD JWT auth, 3-role RBAC, check wizard 5-step flow, compliance dashboard, supply room, retirement, security headers, CI/CD pipeline.
