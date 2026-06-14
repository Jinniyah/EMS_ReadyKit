# EMS ReadyKit — Completed Items
# Last updated: 2026-06-14 (Session X: CQ-B4, CQ-B5, CQ-B6, CQ-B7, CQ-F1 — full code quality cleanup)
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X
# Active backlog -> docs/backlog.md

---

## Session X — Code Quality Cleanup (2026-06-14)
All five CQ backlog items implemented. Codebase is now portfolio-ready.
Migration 0026 added for check_date Date type. Old admin.py replaced by three sub-routers.
Run `cd app ; pytest tests/ -v` and `alembic upgrade head` to verify.

| # | Item | Completed |
|---|------|-----------|
| CQ-B7 | `create_par_level` pre-check queries removed; DB constraint + IntegrityError only | 2026-06-14 |
| CQ-B4 | `LastReadingItem` → `schemas/checks.py`; `_ItemStatusPatch` → `schemas/inventory.py` as `ItemStatusPatch` | 2026-06-14 |
| CQ-B5 | `admin.py` (30KB) split into `admin_items.py`, `admin_vehicles.py`, `admin_stations.py`; `main.py` updated | 2026-06-14 |
| CQ-F1 | `check-wizard/index.jsx` 18 `useState` calls → `useReducer`; `submissionResult` object groups submit fields | 2026-06-14 |
| CQ-B6 | `check_date` `String(10)` → `Date` type; migration 0026; model + router + schema updated | 2026-06-14 |

---

## Session W — Check History Endpoints + Usage Log Gap Closure (2026-06-13)
CH-B4 (force hard-delete) and CH-B5 (list deleted) were already implemented; CH-B6 (restore) added.
Tests added for all three. Frontend: restoreCheck API call added; Restore button added to DeletedChecksList.
USAGE-B1 and USAGE-B2 discovered to already be implemented; closed from backlog. UAT-10 unblocked.
No new migrations.

| # | Item | Completed |
|---|------|-----------|
| CH-B4 | `DELETE /checks/daily/{id}/force` -- Admin only, permanent hard-delete; 6 new tests | 2026-06-13 |
| CH-B5 | `GET /checks/daily/deleted?station_id=` -- Supervisor+, list soft-deleted; 6 new tests | 2026-06-13 |
| CH-B6 | `PATCH /checks/daily/{id}/restore` -- Supervisor+, restore soft-deleted; 7 new tests | 2026-06-13 |
| USAGE-B1 | `get_last_readings` subtracts post-check usage via `_get_post_check_usage()` -- already done | 2026-06-13 |
| USAGE-B2 | `location_id` on UsageEvent + schema validation + location-scoped usage query -- already done | 2026-06-13 |

---

## Session V — UAT Continued (2026-06-12)
Administrator and Supervisor UAT both complete. Four bugs found and fixed.

| # | Item | Completed |
|---|------|-----------|
| UAT-3 | Supervisor UAT passed | 2026-06-12 |
| UAT-4 | Administrator UAT passed | 2026-06-12 |
| UAT-BUG4 | Progress bar showed "Vehicle" for supply room checks | 2026-06-12 |
| UAT-BUG5 | "This check" as check subject -- selection_label fix | 2026-06-12 |
| UAT-BUG6 | Check date blank on Step 5 -- todayIso() fallback | 2026-06-12 |
| UAT-BUG7 | Supply room check did not update View Supplies -- SR-B5 reconcile | 2026-06-12 |
| DEAD-CODE | RestockVehiclePanel, StockSummaryView, getStationChecksToday deleted | 2026-06-12 |
| CI-AUDIT | npm audit --omit=dev so esbuild CVEs don't block deploy | 2026-06-12 |
| PAR-FIX | list_location_par_levels filters ParLevel.active (UAT-BUG8) | 2026-06-12 |

---

## Session U — Supervisor UAT + Damaged Items (2026-06-12)

| # | Item | Completed |
|---|------|-----------|
| UAT-BUG-LOG | Log Items Used showed no ambulances (v.status vs v.active fix) | 2026-06-12 |
| UAT-BUG-NC | No Change bypassed Reconcile when items short | 2026-06-12 |
| USAGE-FLAKY | test_usage.py flaky unique constraint (id(station) → uuid4().hex[:12]) | 2026-06-12 |
| SUP-DMG-FIX1 | FAIL banner persisted after repair resolved | 2026-06-12 |
| SUP-DMG1 | GET /stations/{id}/damaged-items; DamagedItemsPanel; 13 tests | 2026-06-12 |

---

## Session T — Par Level Deactivation (2026-06-11)
| # | Item | Completed |
|---|------|-----------|
| B-M6 | deactivated_at + deactivation_reason on par_levels; migration 0024; PATCH /admin/par-levels/{id} | 2026-06-11 |

---

## Session S — Retirement (2026-06-10)
| # | Item | Completed |
|---|------|-----------|
| RET-B1--B6 | Retire vehicle/location/station/lot; list retired; RBAC | 2026-06-10 |
| RET-F1--F5 | VehicleManagementSection, StationManagementSection, RetiredListSection | 2026-06-10 |
| RET-M1/M2/M3 | Migration 0023: retired_at/by/reason on vehicles/locations/stations/lots | 2026-06-10 |

---

## Sessions A–R — Foundation through Settings (2026-05-26 to 2026-06-10)
Full history in git. Highlights: Azure AD JWT auth, 3-role RBAC, check wizard 5-step flow,
compliance dashboard, supply room, retirement, security headers, CI/CD pipeline.
304–410 tests across these sessions.

---

## Post-Session L — Frontend Tests + Rate Limiting (2026-06-08/09)
| # | Item | Completed |
|---|------|-----------|
| FE-TEST-INFRA--10 | MSAL mocks, useAuth mock, 10 component test files | 2026-06-09 |
| RATE-FIX | slowapi rate limiter; TESTING flag; check_date server-derived; performed_by email | 2026-06-09 |
| RATE-CI | ruff in CI; migration 0019 composite index | 2026-06-09 |
