# EMS ReadyKit — Active Backlog
# v2.05 | Updated: 2026-06-19 | Session AF in progress — PAR-B1 done; audit date-range test fix applied; pytest/ruff/black verification pending
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AE complete — see backlog_completed.md

---

## SESSION AF — IN PROGRESS (not yet closed)

### Found this session (Jennifer, UAT)
1. **Compliance Dashboard showing retired vehicles** (calendar + today list) — **FIXED**.
   Root cause: `GET /stations/{id}/vehicles` returns ALL vehicles (active + retired) unless
   `active=true` is explicitly passed; nothing downstream filtered `retired_at`.
   Fix: `supervisorApi.getTodayCompliance` now filters `!v.retired_at` at the source
   (`frontend/src/modules/supervisor/api/supervisorApi.js`). Defensive `!v.retired_at`
   checks also added in `index.jsx` and `ComplianceCalendar.jsx`, matching the documented
   BUG-AD1 convention (CODEBASE_INDEX.md "active vs retired_at").
2. **Jump bag missing from Compliance Calendar month view; Station Supplies Count missing
   entirely from the calendar** — **FIXED**.
   `ComplianceCalendar.jsx` rewritten: week view = active (non-retired) vehicles + jump bags
   only (Station Supply Room intentionally excluded — wasted space at weekly cadence per
   Jennifer's direction). Month view = combined vehicle/jump-bag picker + grid, plus a
   month-only "Station Supplies Count" reminder strip (new `supervisorApi.getSupplyRoomLocation`,
   excludes a retired supply room via `!loc.retired_at` check after fetch since
   `GET /stations/{id}/supply-room` has no server-side retired filter).
3. **"This item is already assigned to this compartment" on re-add after removal; check
   wizard Step 3 stuck on a removed item** — **FIXED (backend)**.
   Root cause (PAR-B1): `uq_par_item_compartment (item_id, compartment_id)` unique
   constraint has no concept of `active`. Soft-deactivating a par level (Remove) leaves a
   row occupying that slot; re-adding the same item to the same compartment always hit the
   `IntegrityError` → 409 fallback even with no active duplicate present.
   Fixed in both creation entry points — reactivate the matching inactive row (clear
   `deactivated_at`/`deactivation_reason`, apply new min/max) instead of inserting a
   duplicate:
   - `app/ems_readykit/routers/admin_items.py` :: `assign_item_to_compartment`
     (`POST /admin/items/{id}/assign` — the actual UI path, Station Administration /
     `CompartmentParLevels.jsx` / `ItemAssignments.jsx`)
   - `app/ems_readykit/routers/inventory.py` :: `create_par_level`
     (`POST /inventory/par-levels` — not currently called from any frontend UI, fixed for
     consistency since it has the identical flaw)
   New test file: `app/tests/test_par_level_reactivation.py`.

### Latest pytest run reviewed — root cause found, fix applied (unverified)
Jennifer supplied a fresh `cd app; pytest` run (484 collected, 483 passed, 1 failed). Full
traceback reviewed before forming a theory, per CLAUDE.md.

**Failing test:** `tests/test_routers.py::TestAuditEndpoints::test_audit_from_date_tomorrow_returns_empty`

**What the traceback actually showed:** the test creates its own station/vehicle (correctly
scoped per the earlier Session AF fix), submits one check, then queries
`GET /audit?station_id={sid}&from_date=<tomorrow>` expecting `[]`. The response instead
contained exactly the one audit event the test itself had just written
(`action=CHECK_COMPLETED`, `entity_id=72`) — so this was NOT the previously-fixed
global-unfiltered-table pollution (the query *was* correctly scoped to the test's own
station), and it was NOT the `routers/audit.py` comparison logic (already verified correct
via isolated repro earlier this session — not revisited).

**Actual root cause (new evidence, distinct from both previously-ruled-out theories):** the
test computed `tomorrow = (date.today() + timedelta(days=1)).isoformat()` using **local
wall-clock date**, while the audit event's `timestamp` is always written as
`datetime.now(timezone.utc)` (`core/audit.py`). The captured log line in the failing run
showed the request at local time `20:29:35` with `from_date=2026-06-20` — i.e. local
"today" was 2026-06-19, so "tomorrow" was computed as 2026-06-20. But at US Eastern local
time in the evening, UTC has already rolled over to the next calendar day (20:29 Eastern
≈ 00:29 UTC the next day). So the event's actual UTC timestamp was already on
2026-06-20 — making it `>= from_date` and incorrectly included. This is a test-data bug
(wrong clock used to compute the boundary), not a defect in the apply's date-filter logic.

**Fix applied:** `test_audit_from_date_tomorrow_returns_empty` and
`test_audit_to_date_yesterday_returns_empty` (same flaw, opposite direction) in
`app/tests/test_routers.py` now compute their `tomorrow`/`yesterday` boundary from
`datetime.now(timezone.utc).date()` instead of local `date.today()`, matching the UTC
clock the application actually uses. `routers/audit.py` was NOT touched — confirmed
unmodified, matching its already-verified-correct form.

**⚠ UNVERIFIED — next session (or Jennifer directly) must do, in order:**
1. Run `cd app; pytest` fresh and confirm 484/484 green (the long_conversation reminder /
   CLAUDE.md rule against an AI agent running pytest itself still applies — this needs a
   human-run confirmation pasted back).
2. If green: run `cd app; ruff check .` and `cd app; black --check .`; fix any violations.
3. If `npm test` hasn't been re-run since the Session AF frontend changes
   (ComplianceCalendar.jsx, supervisorApi.js, supervisor/index.jsx), run `cd frontend; npm test`
   too before considering the session fully closed.
4. Once all three are green: move this section's content into `backlog_completed.md`,
   update this file's version line + summary table, and update `CODEBASE_INDEX.md`'s
   "Last updated" banner to drop the "NOT closed" warning.

---

## LAUNCH PHILOSOPHY (established 2026-06-04)
## This app ships ONCE to a real EMS team. One launch, one chance.
## The first time Earl sees it, it must work without explanation.
##
## Launch gate criteria — ALL MET:
##   ✓ Check wizard redesign complete (No Change / Modify / Priority Items)
##   ✓ After-call reset flow complete
##   ✓ Damaged item marking complete
##   ✓ First-run tutorial complete (3-screen minimum)
##   ✓ All responder-facing language plain English (no jargon, no technical errors)
##   ✓ Open repair count visible on compliance dashboard
##   ✓ Vehicle + location retirement actions complete
##   ✓ Priority items configured in admin for Unit 712 (AED, LUCAS, O2, Truck Ops)
##   ✓ UAT complete — Responder, Supervisor, Administrator, cross-role, edge cases all passed
##   ✓ Physical stock count entered for Unit 712
##   ✓ All tests passing (468 tests, 0 warnings) — ⚠ Session AF: this is currently UNVERIFIED,
##     see "SESSION AF — IN PROGRESS" above. A root-cause fix has been applied but not yet
##     confirmed by a fresh green pytest run. Do not assume this gate still holds.
##   ✓ Code cleanup complete (CQ-B4/B5/B6/B7/F1; admin split; schemas clean)
##   ✓ Published to Azure
##   ✓ Help screen built and tutorial updated for current feature set (LAUNCH-F1) -- Session AA
##   ✓ PII/sensitive data disclaimer banner on login screen (LAUNCH-F2) -- Session AA
##   ✓ Training station seeded and auto-restored on deploy (LAUNCH-OPS8 replacement) -- Session AB
##   ✓ Security vulnerabilities resolved (6 CVEs + starlette deprecation warning) -- Session AB
##   ✓ Settings screen CSS consistent with app-wide patterns -- Session AB
##   ✓ Email alignment diagnostic available to admins (LAUNCH-OPS9) -- Session AC
##   ✓ Retired vehicles no longer leak into active screens (BUG-AD1) -- Session AD, found in UAT
##   ✓ Member management consolidated into one screen, removal bug fixed (MERGE-1) -- Session AE,
##     found by Jennifer in UAT; pytest + npm test green; deployed and confirmed live on Azure

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device Ready Check, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter physical stock count for Unit 712 | Seed has par levels (targets) not actual counts. Physical count before first live check. |
| LAUNCH-OPS3 | Enter stock count for Unit 712 Jump Bag | |
| LAUNCH-OPS4 | Add all EMS team members | Use Station Administration → Members → Import CSV. (Path corrected — was "Settings → Team Members" before MERGE-1 moved member management.) |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | 🔄 In progress — Jennifer is walking this now; BUG-AD1, MERGE-1, and the Session AF items above all surfaced from it. |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | |

### Post-launch engineering
| # | Item | Pri | Notes |
|---|------|-----|-------|
| F-5G3 | CSV data export | Medium | One download button each in: Check History (supervisor view), Audit Log, Repair Requests. Same streaming CSV pattern as the receive-stock template. |
| ADMIN-F10 | Member list search/filter | Low | Search box in `MemberManagementSection` (now in `modules/admin/`) filtering by name or email. Client-side filter, no new backend endpoint. |
| TEST-AE1 | Test coverage for MembersScreen / MemberManagementSection | Medium | Neither the old admin flat-list nor the old settings version had any tests. Good candidates: multi-role grouping/display, CSV import happy path + errors, name edit, member_id-based role removal, Supervisor-vs-Admin role-gating (Administrator option hidden for Supervisors). |
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
| Session AF blocked items | 1 (pytest/ruff/black + npm test re-verification pending — see above) |
| Post-launch operational | 6 (1 🔄 in progress) |
| Post-launch engineering | 13 (2 ⛔) |
| **Total remaining** | **20** |

---

*v2.05 — 2026-06-19: Session AF continued. Reviewed fresh pytest output (484 collected, 483
passed, 1 failed): `TestAuditEndpoints::test_audit_from_date_tomorrow_returns_empty` failed
because its `tomorrow`/`yesterday` boundary was computed from local wall-clock `date.today()`
while the audit event's timestamp is always UTC (`core/audit.py`) — near a local/UTC day
boundary the test's own freshly-written event could already carry a UTC timestamp on the
"tomorrow" side, defeating the `>= from_date` exclusion. This is distinct from both
previously-ruled-out theories (`routers/audit.py`'s comparison logic, already verified
correct; and the original global-unfiltered-audit-table pollution, already fixed by
station-scoping). Fixed `test_audit_from_date_tomorrow_returns_empty` and
`test_audit_to_date_yesterday_returns_empty` in `app/tests/test_routers.py` to compute their
boundary from `datetime.now(timezone.utc).date()` instead. `routers/audit.py` left
untouched. ⚠ Fix is unverified — needs a fresh `cd app; pytest` run (and `ruff check .` +
`black --check .` once green) before the session can be closed. See "SESSION AF — IN
PROGRESS" above for the full required next-steps sequence.*
*v2.04 — 2026-06-19: Session AF in progress, NOT closed. Three frontend/UX bugs found and fixed
(retired vehicles on Compliance Dashboard; jump bag + Station Supplies Count missing from
calendar; PAR-B1 par-level reactivation on re-add after removal). Backend fix for PAR-B1 applied
in admin_items.py and inventory.py with new test file test_par_level_reactivation.py. Test suite
is NOT currently confirmed green — multiple rounds of fixes attempted, most recent pytest run not
yet reviewed. See "SESSION AF — IN PROGRESS" section above for full state and required next steps.
Do not move launch-gate checkmarks or close this session until pytest is verified green.*
*v2.03 — 2026-06-19: Session AE closed and verified. `cd app; pytest` and `cd frontend; npm test` both confirmed green by Jennifer; `_session_AE_removed/` staging folder deleted; app deployed and confirmed live on Azure. Full MERGE-1 write-up moved to backlog_completed.md.*
*v2.02 — 2026-06-19: Session AE closed. MERGE-1 — member management consolidated into Station Administration -> Members (single screen, single API module); fixed the user_id/member_id mismatch that broke removal in Station Administration; Settings narrowed to admin-only station/vehicle configuration. Added TEST-AE1 (no test coverage yet for the consolidated screen) to post-launch engineering backlog.*
*v2.01 — 2026-06-19: Added close-out note for the missing-files incident (quota interruption) and confirmation that all files are now restored and verified present. LAUNCH-OPS5 marked in-progress since Jennifer is actively walking it.*
*v2.00 — 2026-06-19: Session AD closed. BUG-AD1 fixed — retired vehicles (retired_at set) were leaking into VehiclesScreen (Admin), VehicleCard/V&E Status, HomePage's issue-badge check, and (defensively) the check wizard's vehicle picker. All four now filter on `retired_at` in addition to `active`, matching the documented convention. Found by Jennifer in UAT while walking LAUNCH-OPS5/6. 4 new frontend tests added, 4 existing files patched, no backend changes needed (retire_vehicle already set the fields correctly).*
*v1.99 — 2026-06-19: Session AC closed. LAUNCH-OPS9 (email alignment check) implemented as GET /admin/email-alignment-check, Admin only, 12 tests. Moved to backlog_completed.md. Remaining operational items (OPS1-6) are the EMS chief's job, not engineering — walkthrough checklist provided separately.*
*v1.98 — 2026-06-18: Session AB closed. Training station added, security vulnerabilities patched, Settings CSS fixed. All launch gates now met. Moved F-5G3 and ADMIN-F10 to post-launch engineering.*
*v1.97 — 2026-06-14: Help screen added to Session AA as LAUNCH-F1.*
*v1.96 — 2026-06-14: Session Z closed + ruff fixes + published to Azure.*
*v1.95 — 2026-06-14: Session Z. ACC-B6/B7/B8 complete. Migration 0027. Multi-role switching.*
