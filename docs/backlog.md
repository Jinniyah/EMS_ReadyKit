# EMS ReadyKit — Project Backlog
# Document version: 1.4
# Last updated: 2026-05-22
# Source: Consolidated from phase docs, session handoffs, chat history, OSI review

---

## How to use this file

Items are grouped by area and tagged with priority and source.
Priority levels: **High** (blocks something), **Medium** (important, not blocking), **Low** (quality / polish).
Status: 📋 Not started | 🔄 In progress | ✅ Done | ⛔ Blocked

Update status here whenever an item is completed or started.
Update `docs/project_index.md` when a phase changes overall status.

---

## 1. Backend — Tests

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| B-T1 | Write `TestCheckTypes` class: MEASUREMENT (O2 PSI above/below minimum), FUNCTIONAL (battery OK/fail), DATE_RECORD (AED charge date recent/overdue), DOCUMENT (present/missing), Jump Bag location creation | High | 📋 | Handoff 2026-05-15 |
| B-T2 | Verify total test count reaches 90+ and all pass after check type tests are added | High | 📋 | Handoff 2026-05-15 |

---

## 2. Backend — Phase 6 Endpoints

All endpoints below are planned in `docs/phase6_backend_extensions.md` and required by Phase 5 frontend modules.

| # | Endpoint | Description | Priority | Status | Required by |
|---|----------|-------------|----------|--------|-------------|
| B-E0 | `GET /api/v1/stations/{id}/locations` | List checkable non-vehicle locations (JUMP_BAG, EQUIPMENT) at a station | High | ✅ Done | Step 1 portable card display |
| B-E1 | `PATCH /api/v1/vehicles/{id}` | Mark vehicle active/inactive with reason and timestamp | High | 📋 | Phase 5E (vehicle status) |
| B-E2 | `PATCH /api/v1/checks/daily/{id}/acknowledge` | Supervisor acknowledges FAIL check with corrective action | High | 📋 | Phase 5F (supervisor dashboard) |
| B-E3 | `GET /api/v1/checks/daily/station/{id}?from=&to=` | Date-range compliance query for calendar view | High | 📋 | Phase 5F (compliance calendar) |
| B-E4 | `POST /api/v1/vehicles/{id}/repair-requests` | File a repair request (all roles); URGENT triggers supervisor notification | High | 📋 | Phase 5E (vehicle status) |
| B-E5 | `POST /api/v1/inventory/transfer` | Move stock between supply room and vehicle during a check | High | 📋 | Phase 5 (supply room restock) |
| B-E6 | `GET /api/v1/inventory/locations/{id}/stock-summary` | Stock vs par per item for supply room view | High | 📋 | Phase 5 (supply room view) |
| B-E7 | `GET /api/v1/stations/{id}/users` | Active users at a station (via Microsoft Graph); feeds second crew picker | Medium | 📋 | Phase 5B (second crew) |
| B-E8 | `PUT /api/v1/inventory/lots/{id}` | Supervisor corrects expiry date on a stock lot | Medium | 📋 | Phase 5F (expiry correction) |
| B-E9 | `PATCH /api/v1/inventory/par-levels/{id}` | Soft-deactivate a par level when item removed from compartment | Medium | 📋 | Phase 5D (item management) |
| B-E10 | `POST /api/v1/feedback` | Submit bug report / enhancement / general feedback | Medium | 📋 | Phase 5G (feedback) |
| B-E11 | `GET /api/v1/feedback` | List feedback entries (Administrator only) | Medium | 📋 | Phase 5G (feedback admin) |
| B-E12 | `GET /api/v1/notifications` | Unread notifications for current user (scoped by role) | Medium | 📋 | Phase 5F (notification bell) |
| B-E13 | `PATCH /api/v1/notifications/{id}/read` | Mark a notification as read | Medium | 📋 | Phase 5F (notification bell) |
| B-E14 | `POST /api/v1/admin/user-requests` | Supervisor submits new user onboarding request | Medium | 📋 | Phase 5G (user management) |
| B-E15 | `GET /api/v1/admin/user-requests` | List user requests with status filter (Administrator only) | Medium | 📋 | Phase 5G (user management) |
| B-E16 | `PATCH /api/v1/vehicles/{id}/repair-requests/{request_id}` | Update repair request status lifecycle | Medium | 📋 | Phase 5E (repair tracking) |
| B-E17 | `GET /api/v1/vehicles/{id}/repair-requests` | List repair requests for a vehicle | Medium | 📋 | Phase 5E / CSV export |
| B-E18 | `GET /api/v1/audit?from=&to=` | Date-range audit event query for export | Medium | 📋 | Phase 5 (data export) |

---

## 3. Backend — Data Model Changes (Phase 6 Migration)

New migration needed: `0005_phase6_extensions` (or next available number).

| # | Item | Priority | Status |
|---|------|----------|--------|
| B-M1 | New table: `repair_requests` (vehicle_id FK, severity, status lifecycle, description, resolution_notes, filed_by, acknowledged_by, resolved_by, timestamps) | High | 📋 |
| B-M2 | New table: `notifications` (type, recipient_role, title, body, linked_entity_type, linked_entity_id, created_at, read, read_at) | Medium | 📋 |
| B-M3 | New table: `feedback_entries` (type, severity, description, current_screen, allow_followup, submitted_by, submitted_at) | Medium | 📋 |
| B-M4 | New table: `user_requests` (name, email, requested_role, station_id, start_date, notes, requested_by, requested_at, status, completed_at) | Medium | 📋 |
| B-M5 | Alter `vehicles`: add `active` (Boolean), `inactive_reason` (String), `inactive_since` (DateTime) | High | 📋 |
| B-M6 | Alter `par_levels`: add `active` (Boolean), `deactivated_at` (DateTime), `deactivation_reason` (String) | Medium | 📋 |
| B-M7 | Alter `daily_inventory_checks`: add `reviewed_by` (String), `reviewed_at` (DateTime), `corrective_action` (String) | High | 📋 |
| B-M8 | Alter `daily_inventory_checks`: add `started_by` (String) for check handoff between crew members mid-shift | Medium | 📋 |

---

## 4. Backend — Code Quality

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| B-Q1 | Add structured `logger` calls (with `extra={}` fields) to `inventory.py`, `stations.py`, `vehicles.py`, `items.py` on all mutating operations | Medium | 📋 | OSI review L7-1 |
| B-Q2 | Standardise `extra={}` logging fields in `core/auth.py` to match the shape used in `checks.py` | Low | 📋 | OSI review L7-2 |

---

## 5. Frontend — Phase 5C: Help System

Phase 5A (foundation) and 5B (check wizard) are complete.

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5C1 | First-run tutorial — 8 steps, auto-shown on first login, replayable from Help menu, skip button | High | 📋 | Phase 5 plan |
| F-5C2 | Contextual screen help — "?" button on each wizard step, opens as bottom sheet | High | 📋 | Phase 5 plan |
| F-5C3 | Searchable FAQ — client-side filter, crew and supervisor sections, 15 questions | Medium | 📋 | Phase 5 plan |
| F-5C4 | Create `src/modules/help/content.js` as single source of truth for all help text | Medium | 📋 | Phase 5 plan |

---

## 6. Frontend — Phase 5D: Item Management

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5D1 | Item catalog search component | Medium | 📋 | Phase 5 plan |
| F-5D2 | Add item form — Responder sends request to supervisor; Supervisor/Administrator adds directly | Medium | 📋 | Phase 5 plan |
| F-5D3 | Remove item with mandatory documented reason | Medium | 📋 | Phase 5 plan |

---

## 7. Frontend — Phase 5E: Vehicle Status

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5E1 | Repair request form (all roles) — severity selector, description, URGENT escalation | High | 📋 | Phase 5 plan |
| F-5E2 | Mark vehicle inactive toggle — Supervisor+ only; requires B-E1 | High | ⛔ Blocked on B-E1 | Phase 5 plan |
| F-5E3 | Repair request status tracking display (FILED → ACKNOWLEDGED → IN_PROGRESS → RESOLVED) | Medium | 📋 | Phase 5 UX review |

---

## 8. Frontend — Phase 5F: Supervisor Dashboard

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5F1 | Supervisor landing page — today's compliance summary and active alerts | High | 📋 | Phase 5 plan |
| F-5F2 | Monthly compliance calendar — color-coded per vehicle per day; requires B-E3 | High | ⛔ Blocked on B-E3 | Phase 5 plan |
| F-5F3 | Check detail view — all line items, lot numbers, expiry dates | High | 📋 | Phase 5 plan |
| F-5F4 | Print layout — legally defensible record with chain of custody header, signature lines | High | 📋 | Phase 5 plan |
| F-5F5 | Supervisor acknowledgement + corrective action on FAIL checks; requires B-E2 | High | ⛔ Blocked on B-E2 | Phase 5 plan |
| F-5F6 | Notification bell with unread badge; requires B-E12 | Medium | ⛔ Blocked on B-E12 | Phase 5 plan |
| F-5F7 | Supply room stock view (stock vs par per item, color coded, reorder form) | Medium | 📋 | Phase 5 supply room plan |

---

## 9. Frontend — Phase 5G: Supporting Modules

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5G1 | Feedback module — floating button (hidden during active check), bug/enhancement/general form | Medium | 📋 | Phase 5 plan |
| F-5G2 | User management module — supervisor submits onboarding request; requires B-E14 | Medium | ⛔ Blocked on B-E14 | Phase 5 plan |
| F-5G3 | Data export — CSV download for check history, audit events, repair requests (role-scoped) | Medium | 📋 | Phase 5 plan |
| F-5G4 | Role switcher (crew mode for supervisors) — display-only; hides supervisor tools; amber CREW MODE badge | Low | 📋 | Phase 5 plan |

---

## 10. Frontend — Phase 5H: Infrastructure

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5H1 | Terraform module: Azure Static Web Apps (`iac/Terraform/modules/frontend/`) | High | 📋 | Phase 5 plan |
| F-5H2 | GitHub Actions frontend build + deploy job | High | 📋 | Phase 5 plan |
| F-5H3 | Add Static Web App URL to `WEBSITES_CORS_ALLOWED_ORIGINS` in App Service app settings (Terraform `app` module) | High | 📋 | Phase 5 plan |
| F-5H4 | Register Static Web App URL as SPA redirect URI in Azure AD App Registration | High | 📋 | Phase 5 plan |

---

## 11. Frontend — Check Wizard UX Improvements

Identified during field UX review and ongoing feedback sessions.

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-UX1 | Station picker on home screen — Cindy (multi-station supervisor) needs to set station before anything else; color-coded station cards | High | ✅ Done | Session 2026-05-16 |
| F-UX2 | Left/right chevron navigation between compartments inside the item counting screen — eliminates 3-tap navigation between compartments | Medium | 📋 | UX review |
| F-UX3 | "Jump to unvalidated" sticky button — scrolls to first unchecked item when compartment has 10+ items | Medium | 📋 | UX review gap #8 |
| F-UX4 | Expired item replacement prompt — after EXPIRED validation: "Was it replaced?" flow with new lot entry or reason | Medium | 📋 | UX review gap #9 |
| F-UX5 | Check handoff support — when second user opens an in-progress draft, show handoff screen; both names on record; requires B-M8 | Medium | ⛔ Blocked on B-M8 | UX review |
| F-UX6 | Compartment location descriptor visible on cards ("Left rear · driver side"); supervisor configures during setup | Medium | 📋 | UX review gap #6 |
| F-UX7 | "Last checked today" indicator on vehicle cards — show check time and status from today's completed check if any | High | 📋 | UX review gap #2 |
| F-UX8 | Item count on compartment cards ("Compartment #7 · 14 items") | Low | 📋 | UX review gap #13 |
| F-UX9 | Two-state submit: "Saved to device" → "Submitted to server ✓"; queue locally when offline and auto-submit on reconnect | Low | 📋 | UX review gap #16 |
| F-UX10 | "Caller/spotter view" — large-text display mode for two-person checks | Low | 📋 | UX review gap #11 |
| F-UX11 | Discard check button inside wizard (Steps 2–4) with confirmation modal — clears draft and returns to home | Medium | ✅ Done | Session 2026-05-21 |
| F-UX12 | Three-tier item row color: green (meets need), yellow (short but non-zero), red (zero / fail) | High | ✅ Done | Session 2026-05-21 |
| F-UX13 | Surface short/fail status on Step 2 compartment list — badge reflects worst-case item status, not just done/in-progress | High | ✅ Done | Session 2026-05-21 |
| F-UX14 | Save compartment force-confirms all touched items — same locked display whether medic used + or Submit count | High | ✅ Done | Session 2026-05-21 |
| F-UX15 | Jump bag and portable equipment as selectable cards on Step 1 alongside vehicles — dashed border, 🎒 icon, separate check submission | High | ✅ Done | Session 2026-05-21 |
| F-UX16 | One jump bag per ambulance — Unit 710 Jump Bag and Unit 712 Jump Bag; sort by label for natural grouping | Medium | ✅ Done | Session 2026-05-21 |
| F-UX17 | Step 4 Reconcile (shopping list) — interactive restock list between compartments and final submit; inline +/− counters write to draft; fail items read-only; share/copy button for texting partner; skipped automatically when nothing is short | High | ✅ Done | Session 2026-05-22 |
| F-UX18 | Wizard renumbered to 5 steps: Vehicle → Compartments → Items → Reconcile → Submit | High | ✅ Done | Session 2026-05-22 |
| F-UX19 | Step 2 button label adapts: "Reconcile →" when short or fail items exist, "Review and Submit →" when all clear | Medium | ✅ Done | Session 2026-05-22 |
| F-UX20 | Step 5 back button routes to Reconcile if items need attention, or directly to Compartments if all clear | Medium | ✅ Done | Session 2026-05-22 |
| F-UX21 | Minimal test unit (Unit TEST QRV) — 2 compartments, 7 items, covers all 5 check types, forces Reconcile step, completes in under 5 min | Medium | ✅ Done | Session 2026-05-22 |
| F-UX22 | Bug fix: Reconcile skipped when only fail (no short) items — now routes to Reconcile for warn OR fail severity | High | ✅ Done | Session 2026-05-22 |
| F-UX23 | Bug fix: Check date blank on Step 5 — now passed as direct prop from orchestrator state, not read from draft | High | ✅ Done | Session 2026-05-22 |
| F-UX24 | Bug fix: Overall status always showed Pass — now uses deriveDraftItemStatus() fallback for draft items without API status field | High | ✅ Done | Session 2026-05-22 |
| F-UX25 | Bug fix: Repair needed auto-selected and pre-filled with failing item list when fail-severity items exist in draft | High | ✅ Done | Session 2026-05-22 |
| F-UX26 | Bug fix: Repair notes showed "Unknown compartment" — handleUpdateItem now reads compartment name from activeCompartment state | High | ✅ Done | Session 2026-05-22 |

---

## 12. Infrastructure / Security

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| I-1 | Add Azure Firewall (or Azure Firewall Basic) to `modules/network` with UDR forcing `0.0.0.0/0` through it; FQDN allow-list for Azure AD, SQL, Key Vault | Medium | 📋 | OSI review L3-1 |
| I-2 | Re-add route table to all three subnets once Firewall is in place | Medium | ⛔ Blocked on I-1 | OSI review L3-2 |
| I-3 | Add `HTTPSRedirectMiddleware` to `main.py`, gated to `settings.is_production` | Low | 📋 | OSI review L6-1 |
| I-4 | Add `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` response headers to `main.py` | Low | 📋 | OSI review L7-3 |
| I-5 | Document Azure AD token lifetime and confirm Continuous Access Evaluation (CAE) is enabled; add to `docs/runbook.md` | Low | 📋 | OSI review L5-1 |
| I-6 | Write `docs/adr/ADR-006-DDoS-Strategy.md` documenting the DDoS Protection Standard cost/benefit tradeoff | Low | 📋 | OSI review L4-1 |
| I-7 | Confirm Azure deployment healthy after F1 quota reset — health endpoint should return 200 consistently | High | 📋 | Handoff 2026-05-15 |

---

## 13. Documentation

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| D-1 | Update `project_index.md` ADR table: rename ADR-005 slot to `ADR-006-DDoS-Strategy.md` (ADR-005 is already `ADR-005-Frontend-Architecture.md`) | Low | ✅ Done | This session |
| D-2 | Write a session handoff document at the end of each development session | Ongoing | 📋 | Convention |
| D-3 | Update `docs/phase5_frontend_pwa.md` status from "Planned" to "In Progress" | Low | 📋 | Phase 5A+5B complete |
| D-4 | Update `docs/phase5_frontend_pwa.md` to mark 5A and 5B as complete | Low | 📋 | Handoff 2026-05-15 |

---

## 14. Open Questions — Awaiting Decision

These were flagged in phase docs and have not yet been answered.

| # | Question | Owner | Source |
|---|----------|-------|--------|
| Q-1 | Should notification delivery include email via Azure Communication Services, or in-app only? | Project owner | Phase 6 plan |
| Q-2 | Should the Microsoft Graph API user lookup (station users list) be cached locally in the database? | Engineering | Phase 6 plan |
| Q-3 | Is a 90-day maximum range sufficient for the compliance calendar date query? | Project owner | Phase 6 plan |
| Q-4 | Should BLOCKING severity feedback bugs auto-create a GitHub issue? | Project owner | Phase 6 plan |
| Q-5 | Should the supply room reorder tracking (mark ordered, mark received) be included in Phase 6 or deferred to Phase 7? | Project owner | Phase 5 supply room plan |

---

## Summary Counts

| Area | Not started | In progress | Blocked | Done |
|------|-------------|-------------|---------|------|
| Backend — Tests | 2 | 0 | 0 | 0 |
| Backend — Phase 6 Endpoints | 17 | 0 | 0 | 1 |
| Backend — Data Models | 8 | 0 | 0 | 0 |
| Backend — Code Quality | 2 | 0 | 0 | 0 |
| Frontend — Phase 5C Help | 4 | 0 | 0 | 0 |
| Frontend — Phase 5D Item Mgmt | 3 | 0 | 0 | 0 |
| Frontend — Phase 5E Vehicle | 2 | 0 | 1 | 0 |
| Frontend — Phase 5F Supervisor | 4 | 0 | 3 | 0 |
| Frontend — Phase 5G Supporting | 2 | 0 | 2 | 0 |
| Frontend — Phase 5H Infra | 4 | 0 | 0 | 0 |
| Frontend — UX Improvements | 7 | 0 | 1 | 18 |
| Infrastructure / Security | 6 | 0 | 1 | 0 |
| Documentation | 3 | 0 | 0 | 1 |
| **Total** | **64** | **0** | **9** | **20** |
