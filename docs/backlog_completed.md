# EMS ReadyKit — Completed Items
# Last updated: 2026-06-19 (Session AF closed; PAR-B1 par-level reactivation + audit date-range timezone fix; verified + deployed to Azure)
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, AA, AB, AC, AD, AE, AF
# Active backlog -> docs/backlog.md

---

## Session AF — Compliance Calendar Fixes + PAR-B1 Reactivation + Audit Test Timezone Bug (2026-06-19)

Three frontend/UX bugs found by Jennifer in UAT, plus a backend test-suite failure
that took three diagnostic passes (across two root causes) to fully resolve.

**1. Compliance Dashboard showing retired vehicles** (calendar + today list). Root
cause: `GET /stations/{id}/vehicles` returns ALL vehicles (active + retired) unless
`active=true` is explicitly passed; nothing downstream filtered `retired_at`. Fix:
`supervisorApi.getTodayCompliance` now filters `!v.retired_at` at the source
(`frontend/src/modules/supervisor/api/supervisorApi.js`), with defensive
`!v.retired_at` checks also added in `index.jsx` and `ComplianceCalendar.jsx`,
matching the documented BUG-AD1 convention.

**2. Jump bag missing from Compliance Calendar month view; Station Supplies Count
missing entirely from the calendar.** `ComplianceCalendar.jsx` rewritten: week view =
active (non-retired) vehicles + jump bags only (Station Supply Room intentionally
excluded — wasted space at weekly cadence per Jennifer's direction). Month view =
combined vehicle/jump-bag picker + grid, plus a month-only "Station Supplies Count"
reminder strip (new `supervisorApi.getSupplyRoomLocation`, excludes a retired supply
room via `!loc.retired_at` check after fetch since `GET /stations/{id}/supply-room`
has no server-side retired filter).

**3. PAR-B1 — "This item is already assigned to this compartment" on re-add after
removal; check wizard Step 3 stuck on a removed item.** Root cause:
`ParLevel.uq_par_item_compartment (item_id, compartment_id)` unique constraint has no
concept of `active`. Soft-deactivating a par level (Remove) leaves a row occupying
that slot; re-adding the same item to the same compartment always hit the
`IntegrityError` → 409 fallback even with no active duplicate present. Fixed in both
creation entry points — reactivate the matching inactive row (clear
`deactivated_at`/`deactivation_reason`, apply new min/max) instead of inserting a
duplicate, preserving the original `par_id` and its history:
- `app/ems_readykit/routers/admin_items.py` :: `assign_item_to_compartment`
  (`POST /admin/items/{id}/assign` — the actual UI path)
- `app/ems_readykit/routers/inventory.py` :: `create_par_level`
  (`POST /inventory/par-levels` — not currently called from any frontend UI, fixed
  for consistency since it has the identical flaw)

New test file: `app/tests/test_par_level_reactivation.py`.

**4. Backend test suite — two separate root causes found across the session, both
on the test side, not the application side:**

*First pass:* `test_audit_from_date_tomorrow_returns_empty` and
`test_audit_to_date_yesterday_returns_empty` were asserting `== []` against the
**entire, unfiltered** `GET /audit` endpoint. Every route handler in this app calls
`db.commit()`, which releases the active SAVEPOINT — committed rows are never rolled
back between tests within a pytest session (documented behavior). With 480+ tests in
the suite, many of which write audit events, the global audit table legitimately had
hundreds of unrelated rows in it by the time these two tests ran. Fixed by scoping
both tests to a station they create themselves, matching the pattern their siblings
`test_list_audit_events_filter_by_severity`/`_by_action` already used.

A first attempt at this fix incorrectly suspected `routers/audit.py`'s naive-vs-aware
datetime comparison (`DateTime(timezone=True)` on SQLite). This was verified WRONG
via isolated repro against the pinned SQLAlchemy version (2.0.30) — the comparison
logic was never actually broken. That change was made and explicitly reverted before
the station-scoping fix above was applied instead.

*Second pass (new failure on a fresh run, after the station-scoping fix landed):*
`test_audit_from_date_tomorrow_returns_empty` still failed — but now genuinely scoped
to its own station, so this was new evidence, not the same bug recurring. The full
traceback showed the test's own freshly-written audit event being returned despite
querying `from_date=<tomorrow>`. Root cause: the test computed `tomorrow` from local
wall-clock `date.today()`, while `AuditEvent.timestamp` is always written as
`datetime.now(timezone.utc)` (`core/audit.py`). The captured log line on the failing
run showed local time `20:29:35` with `from_date=2026-06-20` — at US Eastern evening
hours, UTC has already rolled to the next calendar day, so the event's actual UTC
timestamp satisfied `>= from_date` and was incorrectly included. This is a test-data
bug (wrong clock for the boundary), not a defect in `routers/audit.py`'s comparison
logic (left untouched both times, confirmed unmodified throughout the session). Fixed
by computing `tomorrow`/`yesterday` from `datetime.now(timezone.utc).date()` instead
of local `date.today()` in both tests.

**Dependency fix (treated as a separate quick fix, not part of this session's
backlog):** GitHub Actions' `pip-audit` CI gate flagged `pydantic-settings==2.14.1`
(GHSA-4xgf-cpjx-pc3j); bumped to `2.14.2` in `app/requirements.txt`. Unrelated to the
audit-test timezone fix above — pure dependency patch bump, no code changes.

**Verified:** `cd app; pytest` (484/484), `cd app; ruff check .`, and
`cd app; black --check .` all confirmed green by Jennifer. Deployed to Azure and
confirmed live.

| # | Item | Completed |
|---|------|-----------|
| CAL-AF1 | Compliance Dashboard/Calendar — retired vehicles filtered out at source (supervisorApi.getTodayCompliance) plus defensive checks | 2026-06-19 |
| CAL-AF2 | ComplianceCalendar rewritten — jump bags in month view; Station Supplies Count reminder strip added | 2026-06-19 |
| PAR-B1 | Par-level reactivation on re-add after removal — assign_item_to_compartment + create_par_level reactivate inactive rows instead of erroring; new test_par_level_reactivation.py | 2026-06-19 |
| AUDIT-AF1 | test_audit_from_date_tomorrow_returns_empty / test_audit_to_date_yesterday_returns_empty scoped to a station the test creates (fixed global-table pollution) | 2026-06-19 |
| AUDIT-AF2 | Same two tests' tomorrow/yesterday boundary computed from UTC today (datetime.now(timezone.utc).date()) instead of local date.today() — fixed a local/UTC day-boundary mismatch found on a later run | 2026-06-19 |
| SEC-AF1 | pydantic-settings 2.14.1 → 2.14.2 (GHSA-4xgf-cpjx-pc3j); quick fix, not part of Session AF backlog proper | 2026-06-19 |

---

## Session AE — Member Management Consolidation (MERGE-1) (2026-06-19)

Jennifer reported that Station Administration → Members and Settings → Team Members
were two overlapping, confusing screens, and that removing a member in Station
Administration threw `"Input should be a valid integer, unable to parse string as
an integer"`.

**Root cause:** the frontend had two independent member-CRUD implementations hitting
the same backend routes:
- `modules/admin/api/adminApi.js` — old, broken. Called
  `DELETE /stations/{id}/members/{userId}` and the equivalent PATCH using a
  `user_id` (email string). This was correct before ACC-B7 (Session Z), but ACC-B7
  changed `station_members.py`'s PATCH/DELETE routes to take `member_id` (an integer
  primary key) so a person could hold multiple roles as separate rows. `adminApi.js`
  was never updated to match, so every removal sent a string where Pydantic expected
  an int.
- `modules/settings/api/membersApi.js` — correct, already `member_id`-based, with
  fuller functionality (multi-role grouping by person, edit name, CSV import) than
  the admin module's flat-list version.

No backend changes were needed — `station_members.py` was already correct.

**Fix:** consolidated to one screen and one API module:
- `MemberManagementSection.jsx`, `EmailAlignmentSection.jsx`, and `membersApi.js`
  moved from `modules/settings/` to `modules/admin/`.
- `modules/admin/components/MembersScreen.jsx` rewritten to wrap them (replacing the
  old `MemberList.jsx` + `AddMemberForm.jsx` pair, retired).
- The broken `getStationMembers`/`addMember`/`updateMember`/`removeMember` functions
  removed from `adminApi.js`.
- `modules/settings/index.jsx` no longer renders any member UI — Settings is now
  exclusively admin-only station/vehicle configuration (check workflow toggle,
  station/vehicle/location retirement).
- CSS: `.settings-section`, `.settings-row`, `.badge`, `.member-*`, and
  `.email-alignment__*` classes moved from `settings.css` to `index.css` since they
  became genuinely cross-module (same pattern already used for `.item-combobox`
  and `.csv-import`).
- Supervisors can now manage their own station's members (add, edit name, add
  additional roles, CSV import) without Administrator access — this was already
  true of the underlying SUPERVISOR_PLUS-gated endpoints; only the split UI was
  obscuring it. The Email Alignment Check stays Admin-only within the same screen.

Answering Jennifer's question about what removal actually does: removing a member
in the (working) Settings screen only deactivated that one role row
(`member.active = False` on that `member_id`) — it never deleted the person. If
they held other roles, those were untouched; if it was their only role, they lost
station access but the row persisted, soft-deleted, for audit history.

Six superseded files (old `MemberList.jsx`, `AddMemberForm.jsx`, and the pre-move
copies of `MemberManagementSection.jsx`, `EmailAlignmentSection.jsx`, `membersApi.js`,
`EmailAlignmentSection.test.jsx` from `settings/`) were staged in a
`_session_AE_removed/` folder since the filesystem tooling available had no delete
operation — confirmed deleted by Jennifer after review.

**Verified:** `cd app; pytest` passing (468+ baseline unchanged — no backend changes),
`cd frontend; npm test` passing (`EmailAlignmentSection.test.jsx` moved cleanly
alongside its component), deployed to Azure and confirmed live.

| # | Item | Completed |
|---|------|-----------|
| MERGE-1 | Member management consolidated from two screens into Station Administration -> Members; fixed broken member_id/user_id mismatch in adminApi.js; Settings narrowed to admin-only config; pytest + npm test green; deployed to Azure | 2026-06-19 |

---

## Session AD — Retired Vehicle Leak Fix (2026-06-19)

Found by Jennifer during LAUNCH-OPS5/6 walkthroughs: after retiring the "TEST UAT"
vehicle from Settings, it still appeared in Admin → Vehicles with "Show out-of-service
vehicles" unchecked, with a working "Return to Service" button.

Root cause: `active` and `retired_at` are two independent fields on the Vehicle model
(documented in CLAUDE.md as `v.active === true && !v.retired_at`). Retiring a vehicle
sets `active = False` as a side effect, but several frontend call sites only ever
checked `active` and never `retired_at` directly -- meaning the "no longer in active
service" signal worked by coincidence, not by design, and didn't distinguish a
permanently retired vehicle from a genuinely temporary out-of-service one. The retire
endpoint itself (`PATCH /vehicles/{id}/retire`) was correct the whole time; this was
purely a frontend display/action-gating bug.

Four call sites patched:
- `admin/components/VehiclesScreen.jsx` -- screen-level filter excluded `retired_at`
  rows outright (regardless of the "Show out-of-service" toggle); `VehicleAdminCard`
  now shows a "Retired" badge and the retirement reason instead of editable fields,
  Return to Service, or compartment edit controls.
- `vehicles/index.jsx` (V&E Status) + `vehicles/components/VehicleCard.jsx` -- same
  screen-level exclusion; card now shows "Retired" badge instead of "Out of Service"
  and hides Report an Issue / Mark Out of Service / Return to Service entirely.
- `pages/HomePage.jsx` -- `useStationIssues` excluded retired vehicles before
  fetching repair requests, so old repair history on a retired vehicle can no longer
  trigger the home screen's "Unresolved Issue" badge.
- `check-wizard/components/Step1Vehicle.jsx` -- defensive fix only (this path was
  already safe because the server-side `active=true` filter combined with
  retirement's `active=False` side effect happened to exclude retired vehicles), but
  now checks `retired_at` directly via a shared `isCheckableVehicle()` helper rather
  than relying on that side effect continuing to hold.

`usage-log/index.jsx` already filtered correctly (`v.active === true && !v.retired_at`)
and served as the reference pattern for the fix.

4 new/updated test files: `VehicleCard.test.jsx` (4 new regression cases),
`VehiclesScreen.test.jsx` (new file, 3 cases -- this screen had no test coverage
before, which is how the bug shipped unnoticed).

| # | Item | Completed |
|---|------|-----------|
| BUG-AD1 | Retired vehicles excluded from VehiclesScreen, V&E Status, HomePage issue badge, check wizard picker; 7 new frontend tests | 2026-06-19 |

---

## Session AC — Email Alignment Diagnostic + Settings UI (2026-06-19)

LAUNCH-OPS9 was the one remaining engineering item on the post-launch operational list;
everything else there (priority items config, physical stock counts, team member CSV
import, chief/volunteer walkthroughs) is the EMS chief's job, not engineering, and was
handed off as a walkthrough checklist instead.

Built as an on-demand Admin diagnostic rather than a startup-time check, since
StationMember rows can be added or imported at any time after the app is already
running -- a one-time startup scan would miss anything added later. `GET
/admin/email-alignment-check` scans StationMember rows and flags any whose `user_id`
doesn't look like a valid email (blank, contains whitespace, missing `@`/domain, or
not lowercase), which is the standard symptom of an admin typing a display name into
the email field during manual add or CSV import. Read-only; never modifies data.
Optional `station_id` filter; `include_inactive` to also scan soft-deleted rows.
Added to `admin_stations.py` (Admin-only, alongside the other admin diagnostics like
`/admin/retired`) rather than a new router. 12 new tests in `test_email_alignment.py`.

Follow-up same session: wired a "Run Check" button into Settings (Admin-only section,
`EmailAlignmentSection.jsx`, placed above StationManagementSection). On a flagged
result, an Admin can pick recipients from existing Administrators/Supervisors at the
station (excluding anyone who is themselves flagged, since their address may not be
reachable) or type in additional emails, then draft a notification email. No email
account is connected in this environment, so the draft opens via a `mailto:` link
in the Admin's own mail app rather than sending automatically. New CSS block added
to `settings.css` (`.email-alignment__*`), reusing existing color tokens. 17 new
frontend tests in `EmailAlignmentSection.test.jsx`.

(Session AE later moved `EmailAlignmentSection.jsx` and its test file from
`settings/` to `admin/` as part of the member-management consolidation — same
behavior, new home.)

| # | Item | Completed |
|---|------|-----------|
| LAUNCH-OPS9 | `GET /admin/email-alignment-check` — flags malformed StationMember.user_id values; Admin only; 12 tests | 2026-06-19 |
| LAUNCH-OPS9-UI | Settings → Email Alignment Check section: Run Check button, flagged-issue list, recipient picker, draft email via mailto; 17 frontend tests | 2026-06-19 |

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
