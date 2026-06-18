# EMS ReadyKit — Completed Items
# Last updated: 2026-06-18 (Session AB closed; all launch gates met)
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, AA, AB
# Active backlog -> docs/backlog.md

---

## Session AB — Training Station + Security + Settings Polish (2026-06-18)

Training station added as a permanent safe playground for crew training — orange (#e65100)
so it is immediately distinct from the real blue stations. Two BLS ambulances (Training Unit A/B)
and two jump bags (Training Jump Bag A/B) with ~1/3 of Unit 712's inventory. All 6 check types
are represented including AED + LUCAS priority items, O2 PSI measurement, AED pads expiry,
and requires_full_check compartments (Truck Operations, Under Hood). A training check takes
~5 minutes vs 20 for Unit 712.

Training seed split into a standalone `seed_training.py` called by `startup.sh` on every deploy
— including production — so the training station is automatically restored after any database
teardown without manual intervention. The main `seed.py` operational guard remains in place.

Six pip-audit CVEs resolved by bumping starlette (1.1.0→1.3.1), python-multipart (0.0.27→0.0.31),
and cryptography (46.0.7→48.0.1). The starlette upgrade introduced a StarletteDeprecationWarning
for plain httpx — resolved by switching to httpx2==2.4.0. Migration 0025 fixed for both SQLite
and PostgreSQL (inline unnamed FK constraint removed from batch_alter_table).

Settings screen CSS overhauled: member rows match the settings-row vertical rhythm,
role chip indent removed, settings-section__heading works on both h2 and button elements
without a modifier class, RetiredListSection inline styles replaced with CSS classes.

| # | Item | Completed |
|---|------|-----------|
| TRAIN-1 | Newberg Training Station — orange, 2 BLS ambulances + 2 jump bags, all check types | 2026-06-18 |
| TRAIN-2 | `seed_training.py` — standalone idempotent script, always seeded including production | 2026-06-18 |
| TRAIN-3 | `startup.sh` split into Pass 1 (operational, dev-only) and Pass 2 (training, always) | 2026-06-18 |
| SEC-AB1 | starlette 1.1.0 → 1.3.1 (CVE-2026-54283, CVE-2026-54282) | 2026-06-18 |
| SEC-AB2 | python-multipart 0.0.27 → 0.0.31 (CVE-2026-53540, CVE-2026-53539, CVE-2026-53538) | 2026-06-18 |
| SEC-AB3 | cryptography 46.0.7 → 48.0.1 (GHSA-537c-gmf6-5ccf) | 2026-06-18 |
| SEC-AB4 | httpx → httpx2==2.4.0 (StarletteDeprecationWarning resolved) | 2026-06-18 |
| BUG-AB1 | Migration 0025 — removed inline unnamed FK from batch_alter_table; SQLite + PostgreSQL compatible | 2026-06-18 |
| CSS-AB1 | Settings screen — member row padding, role chip indent, heading button pattern, RetiredListSection inline styles removed | 2026-06-18 |
| CSS-AB2 | MemberManagementSection — all missing CSS classes added to settings.css (member-row-*, badge-*, btn--small) | 2026-06-18 |

---

## Session AA — Help Screen + PII Banner + Launch Gate (2026-06-14)

| # | Item | Completed |
|---|------|-----------|
| LAUNCH-F1 | Help screen — Quick Reference, Feature Guide, Show Tutorial Again button | 2026-06-14 |
| LAUNCH-F2 | PII disclaimer banner on login screen — always visible, no acknowledgement required | 2026-06-14 |
| LAUNCH-OPS8 | TEST STATION production guard — replaced with Training Station strategy | 2026-06-14 |

---

## Session Z — Station Member Management + Azure Publish (2026-06-14)
ACC-B6 (edit member name), ACC-B7 (multiple roles per person, Option A),
and ACC-B8 (CSV bulk import) implemented together as one cohesive set.
Migration 0027 drops the single-user unique constraint and replaces it with
(station_id, user_id, role). PATCH and DELETE now use member_id for precision.
The UserPill role switcher updated to show all available roles fetched from
a new /stations/my/roles endpoint. test_member_management.py added (32 tests).
Three ruff errors fixed post-implementation. App published to Azure.

| # | Item | Completed |
|---|------|-----------|
| ACC-B6 | `PATCH /stations/{id}/members/{member_id}` — update preferred_name; propagates to all rows for same user | 2026-06-14 |
| ACC-B7 | Multi-role support (Option A): migration 0027; `GET /stations/my/roles`; UserPill and useRoleMode updated | 2026-06-14 |
| ACC-B8 | `POST /stations/{id}/members/import` CSV bulk import + template download; `MemberManagementSection.jsx` in Settings | 2026-06-14 |
| RUFF-Z | Three ruff errors fixed: B018 in station_members.py, two F841 in test_member_management.py | 2026-06-14 |
| AZURE-PUBLISH | App published to Azure — live at lively-bush-0ed75ca10.7.azurestaticapps.net | 2026-06-14 |

---

## Session Y — UAT Complete + Test Suite Fix + Questions Closed (2026-06-14)
All UAT scenarios passed. Test suite fixed: two root causes resolved (audit metadata date
serialization from CQ-B6; par level NULL compartment duplicate detection from CQ-B7).
437 tests collected, 0 failed. All open questions resolved. App is launch-ready.

| # | Item | Completed |
|---|------|-----------|
| UAT-2 | Responder UAT passed | 2026-06-14 |
| UAT-5 | Cross-role test cases passed | 2026-06-14 |
| UAT-6 | Edge case test cases passed | 2026-06-14 |
| UAT-7 | Pending assignment test case passed | 2026-06-14 |
| UAT-8 | Multi-station test case passed | 2026-06-14 |
| UAT-9 | Unit 712 full shift-start check — cold run passed | 2026-06-14 |
| UAT-10 | After-call usage log — cold run passed | 2026-06-14 |
| UAT-11 | Damaged item scenario — cold run passed | 2026-06-14 |
| BUG-Y1 | `check_history.py` audit metadata passed `date` object to JSON serializer — converted via `_check_date_str()` helper | 2026-06-14 |
| BUG-Y2 | `create_par_level` NULL compartment duplicate not caught by DB constraint — pre-check restored for NULL case | 2026-06-14 |
| Q-3 | Download check history CSV — resolved: yes, build as F-5G3 when first compliance report is due | 2026-06-14 |
| Q-6 | Auto-hard-delete of soft-deleted checks — resolved: Azure Function on 90-day timer | 2026-06-14 |
| F-5F7 | Supply room stock view on supervisor dashboard — resolved: inline low-stock alerts (SR-B3) and DamagedItemsPanel cover this | 2026-06-14 |

---

## Session X — Code Quality Cleanup (2026-06-14)
All five CQ backlog items implemented. Codebase is portfolio-ready.
Migration 0026 added for check_date Date type. Old admin.py replaced by three sub-routers.

| # | Item | Completed |
|---|------|-----------|
| CQ-B7 | `create_par_level` pre-check refined — DB IntegrityError for compartment-scoped; pre-check retained for NULL compartment_id | 2026-06-14 |
| CQ-B4 | `LastReadingItem` → `schemas/checks.py`; `_ItemStatusPatch` → `schemas/inventory.py` as `ItemStatusPatch` | 2026-06-14 |
| CQ-B5 | `admin.py` (30KB) split into `admin_items.py`, `admin_vehicles.py`, `admin_stations.py`; `main.py` updated | 2026-06-14 |
| CQ-F1 | `check-wizard/index.jsx` 18 `useState` calls → `useReducer`; `submissionResult` object groups submit fields | 2026-06-14 |
| CQ-B6 | `check_date` `String(10)` → `Date` type; migration 0026; model + router + schema updated | 2026-06-14 |

---

## Session W — Check History Endpoints + Usage Log Gap Closure (2026-06-13)

| # | Item | Completed |
|---|------|-----------|
| CH-B4 | `DELETE /checks/daily/{id}/force` — Admin only, permanent hard-delete; 6 new tests | 2026-06-13 |
| CH-B5 | `GET /checks/daily/deleted?station_id=` — Supervisor+, list soft-deleted; 6 new tests | 2026-06-13 |
| CH-B6 | `PATCH /checks/daily/{id}/restore` — Supervisor+, restore soft-deleted; 7 new tests | 2026-06-13 |
| USAGE-B1 | `get_last_readings` subtracts post-check usage via `_get_post_check_usage()` | 2026-06-13 |
| USAGE-B2 | `location_id` on UsageEvent + schema validation + location-scoped usage query | 2026-06-13 |

---

## Session V — UAT Continued (2026-06-12)

| # | Item | Completed |
|---|------|-----------|
| UAT-3 | Supervisor UAT passed | 2026-06-12 |
| UAT-4 | Administrator UAT passed | 2026-06-12 |
| UAT-BUG4 | Progress bar showed "Vehicle" for supply room checks | 2026-06-12 |
| UAT-BUG5 | "This check" as check subject — selection_label fix | 2026-06-12 |
| UAT-BUG6 | Check date blank on Step 5 — todayIso() fallback | 2026-06-12 |
| UAT-BUG7 | Supply room check did not update View Supplies — SR-B5 reconcile | 2026-06-12 |
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

## Sessions A–T — Foundation through Par Level Deactivation (2026-05-26 to 2026-06-11)
Full history in git. Highlights: Azure AD JWT auth, 3-role RBAC, check wizard 5-step flow,
compliance dashboard, supply room, retirement, security headers, CI/CD pipeline.

---

## Post-Session L — Frontend Tests + Rate Limiting (2026-06-08/09)

| # | Item | Completed |
|---|------|-----------|
| FE-TEST-INFRA--10 | MSAL mocks, useAuth mock, 10 component test files | 2026-06-09 |
| RATE-FIX | slowapi rate limiter; TESTING flag; check_date server-derived; performed_by email | 2026-06-09 |
| RATE-CI | ruff in CI; migration 0019 composite index | 2026-06-09 |
