# EMS ReadyKit — Active Backlog
# v2.06 | Updated: 2026-06-19 | Session AF closed — PAR-B1, calendar fixes, audit timezone test fix; pytest/ruff/black/npm test all green; deployed to Azure
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AF complete — see backlog_completed.md

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
##   ✓ All tests passing — confirmed by Jennifer at Session AF close: `cd app; pytest` (484/484),
##     `cd app; ruff check .`, `cd app; black --check .` all green; `cd frontend; npm test` green
##     (re-verified after Session AF's ComplianceCalendar.jsx/supervisorApi.js/supervisor/index.jsx
##     changes)
##   ✓ Code cleanup complete (CQ-B4/B5/B6/B7/F1; admin split; schemas clean)
##   ✓ Published to Azure — Session AF changes confirmed live
##   ✓ Help screen built and tutorial updated for current feature set (LAUNCH-F1) -- Session AA
##   ✓ PII/sensitive data disclaimer banner on login screen (LAUNCH-F2) -- Session AA
##   ✓ Training station seeded and auto-restored on deploy (LAUNCH-OPS8 replacement) -- Session AB
##   ✓ Security vulnerabilities resolved (6 CVEs + starlette deprecation warning) -- Session AB
##   ✓ Settings screen CSS consistent with app-wide patterns -- Session AB
##   ✓ Email alignment diagnostic available to admins (LAUNCH-OPS9) -- Session AC
##   ✓ Retired vehicles no longer leak into active screens (BUG-AD1) -- Session AD, found in UAT
##   ✓ Member management consolidated into one screen, removal bug fixed (MERGE-1) -- Session AE,
##     found by Jennifer in UAT; pytest + npm test green; deployed and confirmed live on Azure
##   ✓ Compliance Calendar shows jump bags + Station Supplies Count reminder; retired vehicles
##     filtered from Compliance Dashboard; par-level reactivation bug fixed (PAR-B1) -- Session AF,
##     found by Jennifer in UAT; pytest/ruff/black/npm test all green; deployed and confirmed live

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device Ready Check, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter physical stock count for Unit 712 | Seed has par levels (targets) not actual counts. Physical count before first live check. |
| LAUNCH-OPS3 | Enter stock count for Unit 712 Jump Bag | |
| LAUNCH-OPS4 | Add all EMS team members | Use Station Administration → Members → Import CSV. (Path corrected — was "Settings → Team Members" before MERGE-1 moved member management.) |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | 🔄 In progress — Jennifer is walking this now; BUG-AD1, MERGE-1, and the Session AF items all surfaced from it. |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | |

### Post-launch engineering
| # | Item | Pri | Notes |
|---|------|-----|-------|
| F-5G3 | CSV data export | Medium | One download button each in: Check History (supervisor view), Audit Log, Repair Requests. Same streaming CSV pattern as the receive-stock template. |
| ADMIN-F10 | Member list search/filter | Low | Search box in `MemberManagementSection` (now in `modules/admin/`) filtering by name or email. Client-side filter, no new backend endpoint. |
| TEST-AE1 | Test coverage for MembersScreen / MemberManagementSection | Medium | Neither the old admin flat-list nor the old settings version had any tests. Good candidates: multi-role grouping/display, CSV import happy path + errors, name edit, member_id-based role removal, Supervisor-vs-Admin role-gating (Administrator option hidden for Supervisors). |
| TEST-AF1 | Test coverage for the rewritten ComplianceCalendar.jsx | Medium | No test file exists yet for the Session AF rewrite (jump bags in month view, Station Supplies Count reminder strip, EntityPicker). Good candidate to pair with TEST-AE1 in the same session. |
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
| Post-launch operational | 6 (1 🔄 in progress) |
| Post-launch engineering | 14 (2 ⛔) |
| **Total remaining** | **20** |

---

*v2.06 — 2026-06-19: Session AF closed. Jennifer confirmed `cd app; pytest` (484/484),
`cd app; ruff check .`, and `cd app; black --check .` all green, plus the dependency fix
below; app deployed and confirmed live on Azure. Full Session AF write-up (Compliance
Calendar/Dashboard fixes, PAR-B1 par-level reactivation, and the two-pass audit date-range
test fix — global-table pollution, then a local/UTC day-boundary mismatch) moved to
backlog_completed.md. Separately (treated as a quick fix, not part of Session AF proper):
GitHub Actions' pip-audit CI gate flagged pydantic-settings==2.14.1 (GHSA-4xgf-cpjx-pc3j);
bumped to 2.14.2 in app/requirements.txt, pushed, and confirmed deployed alongside the
Session AF changes. Added TEST-AF1 (no test coverage yet for the rewritten
ComplianceCalendar.jsx) to post-launch engineering backlog, pairing with TEST-AE1.*
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
untouched.*
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
