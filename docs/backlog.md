# EMS ReadyKit — Active Backlog
# v2.00 | Updated: 2026-06-19 | Session AD closed; BUG-AD1 retired vehicle leak fixed
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ Sessions A–AD complete — see backlog_completed.md

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

---

## POST-LAUNCH (not needed for portfolio)

### Operational (EMS chief's job — not engineering)
| # | Task | Notes |
|---|------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 | Admin → Vehicles → Unit 712 → Par Levels. Mark AED Battery, LUCAS Device Ready Check, O2 PSI as priority. |
| LAUNCH-OPS2 | Enter physical stock count for Unit 712 | Seed has par levels (targets) not actual counts. Physical count before first live check. |
| LAUNCH-OPS3 | Enter stock count for Unit 712 Jump Bag | |
| LAUNCH-OPS4 | Add all EMS team members | Use Settings → Team Members CSV import. |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | |

### Post-launch engineering
| # | Item | Pri | Notes |
|---|------|-----|-------|
| F-5G3 | CSV data export | Medium | One download button each in: Check History (supervisor view), Audit Log, Repair Requests. Same streaming CSV pattern as the receive-stock template. |
| ADMIN-F10 | Member list search/filter | Low | Search box in `MemberManagementSection` filtering by name or email. Client-side filter, no new backend endpoint. |
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
| Post-launch operational | 6 |
| Post-launch engineering | 12 (2 ⛔) |
| **Total remaining** | **18** |

*v2.00 — 2026-06-19: Session AD closed. BUG-AD1 fixed — retired vehicles (retired_at set) were leaking into VehiclesScreen (Admin), VehicleCard/V&E Status, HomePage's issue-badge check, and (defensively) the check wizard's vehicle picker. All four now filter on `retired_at` in addition to `active`, matching the documented convention. Found by Jennifer in UAT while walking LAUNCH-OPS5/6. 4 new frontend tests added, 4 existing files patched, no backend changes needed (retire_vehicle already set the fields correctly).*
*v1.99 — 2026-06-19: Session AC closed. LAUNCH-OPS9 (email alignment check) implemented as GET /admin/email-alignment-check, Admin only, 12 tests. Moved to backlog_completed.md. Remaining operational items (OPS1-6) are the EMS chief's job, not engineering — walkthrough checklist provided separately.*
*v1.98 — 2026-06-18: Session AB closed. Training station added, security vulnerabilities patched, Settings CSS fixed. All launch gates now met. Moved F-5G3 and ADMIN-F10 to post-launch engineering.*
*v1.97 — 2026-06-14: Help screen added to Session AA as LAUNCH-F1.*
*v1.96 — 2026-06-14: Session Z closed + ruff fixes + published to Azure.*
*v1.95 — 2026-06-14: Session Z. ACC-B6/B7/B8 complete. Migration 0027. Multi-role switching.*
