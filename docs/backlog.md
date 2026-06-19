# EMS ReadyKit — Active Backlog
# v2.02 | Updated: 2026-06-19 | Session AE closed; MERGE-1 (member management consolidation) complete
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AE complete — see backlog_completed.md

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
##   ✓ All tests passing (468 tests, 0 warnings)
##   ✓ Code cleanup complete (CQ-B4/B5/B6/B7/F1; admin split; schemas clean)
##   ✓ Published to Azure
##   ✓ Help screen built and tutorial updated for current feature set (LAUNCH-F1) -- Session AA
##   ✓ PII/sensitive data disclaimer banner on login screen (LAUNCH-F2) -- Session AA
##   ✓ Training station seeded and auto-restored on deploy (LAUNCH-OPS8 replacement) -- Session AB
##   ✓ Security vulnerabilities resolved (6 CVEs + starlette deprecation warning) -- Session AB
##   ✓ Settings screen CSS consistent with app-wide patterns -- Session AB
##   ✓ Email alignment diagnostic available to admins (LAUNCH-OPS9) -- Session AC
##   ✓ Retired vehicles no longer leak into active screens (BUG-AD1) -- Session AD, found in UAT
##   ✓ Member management consolidated into one screen, removal bug fixed (MERGE-1) -- Session AE, found by Jennifer in UAT

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device Ready Check, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter physical stock count for Unit 712 | Seed has par levels (targets) not actual counts. Physical count before first live check. |
| LAUNCH-OPS3 | Enter stock count for Unit 712 Jump Bag | |
| LAUNCH-OPS4 | Add all EMS team members | Use Station Administration → Members → Import CSV. (Path corrected — was "Settings → Team Members" before MERGE-1 moved member management.) |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | 🔄 In progress — Jennifer is walking this now; BUG-AD1 and MERGE-1 both surfaced from it. |
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
| Post-launch operational | 6 (1 🔄 in progress) |
| Post-launch engineering | 13 (2 ⛔) |
| **Total remaining** | **19** |

---

## ⚠ Session AE close-out note: member management merge (MERGE-1)

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

**Fix (MERGE-1):** consolidated to one screen and one API module:
- `MemberManagementSection.jsx`, `EmailAlignmentSection.jsx`, and `membersApi.js`
  moved from `modules/settings/` to `modules/admin/`.
- `modules/admin/components/MembersScreen.jsx` rewritten to wrap them (replacing the
  old `MemberList.jsx` + `AddMemberForm.jsx` pair, which are now retired).
- The broken `getStationMembers`/`addMember`/`updateMember`/`removeMember` functions
  removed from `adminApi.js`.
- `modules/settings/index.jsx` no longer renders any member UI — Settings is now
  exclusively admin-only station/vehicle configuration (check workflow toggle,
  station/vehicle/location retirement).
- CSS: `.settings-section`, `.settings-row`, `.badge`, `.member-*`, and
  `.email-alignment__*` classes moved from `settings.css` to `index.css` since they
  became genuinely cross-module (per the existing CLAUDE.md rule 6 pattern already
  used for `.item-combobox` and `.csv-import`).
- Supervisors can now manage their own station's members (add, edit name, add
  additional roles, CSV import) without Administrator access, exactly as requested
  — this was already true of the underlying SUPERVISOR_PLUS-gated endpoints; only
  the split UI was obscuring it. The Email Alignment Check stays Admin-only within
  the same screen.

**Answering Jennifer's second question directly:** removing a member in the (working)
Settings screen only deactivated that one role row (`member.active = False` on that
`member_id`) — it never deleted the person. If they held other roles, those were
untouched; if it was their only role, they lost station access but the row persisted,
soft-deleted, for audit history.

**Files moved to `_session_AE_removed/` at repo root** (filesystem MCP has no delete,
only move — see CLAUDE.md "Deleting files"): old `MemberList.jsx`, `AddMemberForm.jsx`,
and the pre-move copies of `MemberManagementSection.jsx`, `EmailAlignmentSection.jsx`,
`membersApi.js`, and `EmailAlignmentSection.test.jsx` from `settings/`.

**Action before next session:** run `git status`, confirm the moves/deletes look
right, then `git rm -r _session_AE_removed` (or delete the folder + `git add -A`),
commit, and run `cd frontend; npm test` to confirm nothing broke (no test files
referenced the deleted admin components, and `EmailAlignmentSection.test.jsx` was
moved alongside its component, so this should be a clean pass). No backend tests
are affected — `pytest` baseline is unchanged at 468+.

| # | Item | Completed |
|---|------|-----------|
| MERGE-1 | Member management consolidated from two screens into Station Administration -> Members; fixed broken member_id/user_id mismatch in adminApi.js; Settings narrowed to admin-only config | 2026-06-19 |

---

*v2.02 — 2026-06-19: Session AE closed. MERGE-1 — member management consolidated into Station Administration -> Members (single screen, single API module); fixed the user_id/member_id mismatch that broke removal in Station Administration; Settings narrowed to admin-only station/vehicle configuration. Added TEST-AE1 (no test coverage yet for the consolidated screen) to post-launch engineering backlog.*
*v2.01 — 2026-06-19: Added close-out note for the missing-files incident (quota interruption) and confirmation that all files are now restored and verified present. LAUNCH-OPS5 marked in-progress since Jennifer is actively walking it.*
*v2.00 — 2026-06-19: Session AD closed. BUG-AD1 fixed — retired vehicles (retired_at set) were leaking into VehiclesScreen (Admin), VehicleCard/V&E Status, HomePage's issue-badge check, and (defensively) the check wizard's vehicle picker. All four now filter on `retired_at` in addition to `active`, matching the documented convention. Found by Jennifer in UAT while walking LAUNCH-OPS5/6. 4 new frontend tests added, 4 existing files patched, no backend changes needed (retire_vehicle already set the fields correctly).*
*v1.99 — 2026-06-19: Session AC closed. LAUNCH-OPS9 (email alignment check) implemented as GET /admin/email-alignment-check, Admin only, 12 tests. Moved to backlog_completed.md. Remaining operational items (OPS1-6) are the EMS chief's job, not engineering — walkthrough checklist provided separately.*
*v1.98 — 2026-06-18: Session AB closed. Training station added, security vulnerabilities patched, Settings CSS fixed. All launch gates now met. Moved F-5G3 and ADMIN-F10 to post-launch engineering.*
*v1.97 — 2026-06-14: Help screen added to Session AA as LAUNCH-F1.*
*v1.96 — 2026-06-14: Session Z closed + ruff fixes + published to Azure.*
*v1.95 — 2026-06-14: Session Z. ACC-B6/B7/B8 complete. Migration 0027. Multi-role switching.*
