# EMS ReadyKit — Project Backlog
# Document version: 1.8
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
| B-T1 | Write `TestCheckTypes` class: MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, Jump Bag location | High | ✅ Done | Session 2026-05-22 |
| B-T2 | Update `test_create_daily_check_duplicate_returns_409` → `test_multiple_checks_same_vehicle_same_day_all_succeed` | High | ✅ Done | Session 2026-05-22 |

---

## 2. Backend — Phase 6 Endpoints

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

## 3. Backend — Data Model Changes

| # | Item | Priority | Status |
|---|------|----------|--------|
| B-M0 | Migration 0005: drop `uq_check_vehicle_date`; replace with non-unique `ix_check_vehicle_date` index | High | ✅ Done |
| B-M1 | New table: `repair_requests` | High | 📋 |
| B-M2 | New table: `notifications` | Medium | 📋 |
| B-M3 | New table: `feedback_entries` | Medium | 📋 |
| B-M4 | New table: `user_requests` | Medium | 📋 |
| B-M5 | Alter `vehicles`: add `active`, `inactive_reason`, `inactive_since` | High | 📋 |
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 |
| B-M7 | Alter `daily_inventory_checks`: add `reviewed_by`, `reviewed_at`, `corrective_action` | High | 📋 |
| B-M8 | Alter `daily_inventory_checks`: add `started_by` for check handoff | Medium | 📋 |
| B-M9 | Alter `daily_inventory_checks`: add `deleted_at` (DateTime, nullable), `deleted_by` (String, nullable), `deletion_reason` (String, nullable), `force_deleted` (Boolean) for soft-delete support | High | 📋 |
| B-M10 | Alter `stations`: add `allow_check_modification` (Boolean, default False) — controls whether supervisors can acknowledge/correct submitted checks at this station; Administrator-only to toggle | High | 📋 |
| B-M11 | Alter `stations`: add `primary_color` (String, nullable) — hex color code set by Supervisor; drives station band and vehicle card colors across all users at that station | Medium | 📋 |
| B-M12 | New table: `user_preferences` — stores per-user preferences: `user_oid` (Azure AD OID), `default_station_id` (FK nullable), `display_name` (String nullable). Scoped to the authenticated user; no cross-user access. | Medium | 📋 |

---

## 4. Backend — Code Quality

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| B-Q1 | Add structured `logger` calls to `inventory.py`, `stations.py`, `vehicles.py`, `items.py` | Medium | 📋 | OSI review L7-1 |
| B-Q2 | Standardise `extra={}` logging fields in `core/auth.py` | Low | 📋 | OSI review L7-2 |

---

## 5. Frontend — Phase 5C: Help System

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5C1 | First-run tutorial — 8 steps, auto-shown on first login, replayable, skip button | High | 📋 | Phase 5 plan |
| F-5C2 | Contextual screen help — "?" button on each wizard step, opens as bottom sheet | High | 📋 | Phase 5 plan |
| F-5C3 | Searchable FAQ — client-side filter, crew and supervisor sections, 15 questions | Medium | 📋 | Phase 5 plan |
| F-5C4 | Create `src/modules/help/content.js` as single source of truth for help text | Medium | 📋 | Phase 5 plan |

---

## 6. Frontend — Phase 5D: Item Management

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5D1 | Item catalog search component | Medium | 📋 | Phase 5 plan |
| F-5D2 | Add item form — Responder requests; Supervisor/Administrator adds directly | Medium | 📋 | Phase 5 plan |
| F-5D3 | Remove item with mandatory documented reason | Medium | 📋 | Phase 5 plan |

---

## 7. Frontend — Phase 5E: Vehicle Status

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5E1 | Repair request form (all roles) — severity selector, description, URGENT escalation | High | 📋 | Phase 5 plan |
| F-5E2 | Mark vehicle inactive toggle — Supervisor+ only; requires B-E1 | High | ⛔ Blocked on B-E1 | Phase 5 plan |
| F-5E3 | Repair request status tracking display | Medium | 📋 | Phase 5 UX review |

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
| F-5G1 | Feedback module — floating button, bug/enhancement/general form | Medium | 📋 | Phase 5 plan |
| F-5G2 | User management module — requires B-E14 | Medium | ⛔ Blocked on B-E14 | Phase 5 plan |
| F-5G3 | Data export — CSV download for check history, audit events, repair requests | Medium | 📋 | Phase 5 plan |
| F-5G4 | Role switcher (crew mode for supervisors) — display-only; amber CREW MODE badge | Low | 📋 | Phase 5 plan |

---

## 10. Frontend — Phase 5H: Infrastructure

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-5H1 | Terraform module: Azure Static Web Apps | High | 📋 | Phase 5 plan |
| F-5H2 | GitHub Actions frontend build + deploy job | High | 📋 | Phase 5 plan |
| F-5H3 | Add Static Web App URL to CORS allowed origins (Terraform `app` module) | High | 📋 | Phase 5 plan |
| F-5H4 | Register Static Web App URL as SPA redirect URI in Azure AD | High | 📋 | Phase 5 plan |

---

## 11. Frontend — Check Wizard UX Improvements

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| F-UX1 | Station picker on home screen | High | ✅ Done | Session 2026-05-16 |
| F-UX2 | Left/right chevron navigation between compartments | Medium | 📋 | UX review |
| F-UX3 | "Jump to unvalidated" sticky button | Medium | 📋 | UX review gap #8 |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | UX review gap #9 |
| F-UX5 | Check handoff support — requires B-M8 | Medium | ⛔ Blocked on B-M8 | UX review |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | UX review gap #6 |
| F-UX7 | "Last checked today" indicator on vehicle cards | High | 📋 | UX review gap #2 |
| F-UX8 | Item count on compartment cards | Low | 📋 | UX review gap #13 |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | UX review gap #16 |
| F-UX10 | "Caller/spotter view" large-text mode | Low | 📋 | UX review gap #11 |
| F-UX11 | Discard check button with confirmation modal | Medium | ✅ Done | Session 2026-05-21 |
| F-UX12 | Three-tier item row color (green/yellow/red) | High | ✅ Done | Session 2026-05-21 |
| F-UX13 | Surface short/fail on Step 2 compartment badges | High | ✅ Done | Session 2026-05-21 |
| F-UX14 | Save compartment force-confirms all touched items | High | ✅ Done | Session 2026-05-21 |
| F-UX15 | Jump bag / portable cards on Step 1 | High | ✅ Done | Session 2026-05-21 |
| F-UX16 | One jump bag per ambulance with alpha-sort grouping | Medium | ✅ Done | Session 2026-05-21 |
| F-UX17 | Step 4 Reconcile — interactive shopping list with share/copy | High | ✅ Done | Session 2026-05-22 |
| F-UX18 | Wizard renumbered to 5 steps | High | ✅ Done | Session 2026-05-22 |
| F-UX19 | Step 2 button label: "Reconcile →" vs "Review and Submit →" | Medium | ✅ Done | Session 2026-05-22 |
| F-UX20 | Step 5 back button routes to Reconcile or Compartments intelligently | Medium | ✅ Done | Session 2026-05-22 |
| F-UX21 | Minimal test unit (Unit TEST QRV) — all check types in < 5 min | Medium | ✅ Done | Session 2026-05-22 |
| F-UX22 | Bug fix: Reconcile routing for fail-only checks | High | ✅ Done | Session 2026-05-22 |
| F-UX23 | Bug fix: Check date blank on Step 5 | High | ✅ Done | Session 2026-05-22 |
| F-UX24 | Bug fix: Overall status always showed Pass | High | ✅ Done | Session 2026-05-22 |
| F-UX25 | Bug fix: Repair needed auto-selected and pre-filled from fail items | High | ✅ Done | Session 2026-05-22 |
| F-UX26 | Bug fix: Repair notes showed "Unknown compartment" | High | ✅ Done | Session 2026-05-22 |
| F-UX27 | DATE_RECORD "Today" button — one tap sets date and locks card | Low | ✅ Done | Session 2026-05-22 |
| F-UX28 | Multiple checks per day — draft key uses started_at; home screen groups drafts with picker modal | High | ✅ Done | Session 2026-05-22 |
| F-UX29 | Backend: drop uq_check_vehicle_date; remove 409 guard; allow unlimited checks per day | High | ✅ Done | Session 2026-05-22 |
| F-UX30 | DraftBanner uses selection_label — fixes null label for jump bag checks | Medium | ✅ Done | Session 2026-05-22 |
| F-UX31 | Reconcile "Add N" top-off button — inline with +/− controls, matches Step 3 layout exactly | Medium | ✅ Done | Session 2026-05-22 |

---

## 12. Check History Module (new)

Covers the full lifecycle of a submitted check — viewing, correcting, and managing records.
Requires B-M9 (soft delete fields), B-M10 (allow_check_modification setting), and B-E2 (acknowledge endpoint).

### 12a. Backend — Check History Endpoints

| # | Endpoint | Description | Priority | Status | Notes |
|---|----------|-------------|----------|--------|-------|
| CH-B1 | `GET /api/v1/checks/daily/my-history?from=&to=` | Responder: list checks submitted by the current user, scoped to their station, most recent first. Excludes soft-deleted records. | High | 📋 | All roles |
| CH-B2 | `GET /api/v1/checks/daily/{id}/detail` | All roles: full check detail — header + all line items + lot numbers + computed status. Responders can only access their own checks; Supervisor+ can access any check at their station. | High | 📋 | Extends existing `GET /checks/daily/{id}` RBAC |
| CH-B3 | `DELETE /api/v1/checks/daily/{id}` | Supervisor+: soft-delete a check. Sets `deleted_at`, `deleted_by`, `deletion_reason`. Hidden from all normal views immediately. Preserved in audit log. Hard-deleted automatically after 90 days. Requires B-M9. | High | 📋 | Supervisor+ |
| CH-B4 | `DELETE /api/v1/checks/daily/{id}/force` | Administrator only: force hard-delete bypassing the 90-day window. Required for PII spill response (e.g. a responder accidentally captured a SSN or DL number in a notes field). Writes an audit event containing actor, timestamp, and stated reason — but never the PII itself. Requires explicit confirmation payload. | High | 📋 | Administrator only |
| CH-B5 | `GET /api/v1/checks/daily/deleted?station_id=` | Administrator only: list soft-deleted checks within 90-day window. Shows deletion metadata. Allows force-delete or restore. | Medium | 📋 | Administrator only |
| CH-B6 | `PATCH /api/v1/checks/daily/{id}/restore` | Administrator only: restore a soft-deleted check within the 90-day window (before auto-hard-delete). | Low | 📋 | Administrator only |

### 12b. Backend — Check Modification Setting

| # | Item | Description | Priority | Status |
|---|------|-------------|----------|--------|
| CH-B7 | `PATCH /api/v1/stations/{id}/settings` | Administrator only: update station settings including `allow_check_modification`. Returns updated station settings object. | High | 📋 |
| CH-B8 | `GET /api/v1/stations/{id}/settings` | Supervisor+: read station settings (allow_check_modification, primary_color, etc.). Used by frontend to conditionally show acknowledgement controls. | High | 📋 |

### 12c. Frontend — Responder Check History

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| CH-F1 | "My Checks" screen on home page — list of the current user's submitted checks, grouped by date, most recent first. Shows vehicle/location label, date, time, overall status badge. | High | 📋 | Responder+ |
| CH-F2 | Check detail view (read-only for Responders) — full compartment/item breakdown, lot numbers, expiry dates, overall status. Same layout as the Step 5 summary but read-only. | High | 📋 | Responder+ |
| CH-F3 | Check detail shows acknowledgement if present — if a supervisor has added a corrective note, display it clearly so the responder can see the outcome | Medium | 📋 | Responder+ |

### 12d. Frontend — Supervisor/Administrator Check Management

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| CH-F4 | Check history list for supervisors — all checks at their station, filterable by vehicle/date/status. Soft-deleted checks hidden by default. | High | 📋 | Supervisor+ |
| CH-F5 | Soft-delete check — Supervisor+ can delete a check with a mandatory reason field. Confirmation modal clearly states the 90-day hard-delete policy. Writes to audit log. Requires B-M9, CH-B3. | High | 📋 | Supervisor+ |
| CH-F6 | Acknowledgement / corrective note — when `allow_check_modification` is on for the station, Supervisor can open a submitted check and add an acknowledgement with corrective notes. Same workflow as B-E2. Toggle is hidden when setting is off. | High | ⛔ Blocked on B-M10, CH-B8 | Supervisor+ |
| CH-F7 | Deleted records management screen (Administrator) — list of soft-deleted checks within 90-day window. Options: restore or force hard-delete. Force hard-delete requires a typed confirmation reason (mirrors the "type DELETE to confirm" pattern for irreversible actions). | High | 📋 | Administrator only |
| CH-F8 | Force hard-delete confirmation — two-step modal: (1) show deletion reason field and warn about PII policy, (2) require typing "PERMANENTLY DELETE" to confirm. Writes audit event with reason but never echoes the suspected PII content. | High | 📋 | Administrator only |

---

## 13. Settings Module (new)

A dedicated Settings section providing a clean, predictable home for all configuration —
station settings, user preferences, and asset/user management. Prevents admin actions
from being scattered across the operational UI.

### 13a. Backend — Settings Endpoints

| # | Endpoint | Description | Priority | Status |
|---|----------|-------------|----------|--------|
| S-B1 | `GET /api/v1/settings/station/{id}` | Supervisor+: get all settings for a station (color, allow_check_modification, cadence requirements). Consolidated view for the Settings UI. | High | 📋 |
| S-B2 | `PATCH /api/v1/settings/station/{id}` | Scoped by field: `primary_color` → Supervisor+; `allow_check_modification` → Administrator only. Returns updated settings. Requires B-M10, B-M11. | High | 📋 |
| S-B3 | `GET /api/v1/settings/user` | Any role: get personal preferences for current user (default_station_id, display_name). | Medium | 📋 |
| S-B4 | `PATCH /api/v1/settings/user` | Any role: update personal preferences. Scoped to authenticated user only — cannot modify another user's preferences. Requires B-M12. | Medium | 📋 |

### 13b. Frontend — Settings Navigation

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| S-F1 | Settings entry point in main navigation — accessible from the home screen header or hamburger menu. Shows only the sections relevant to the current role (Responder sees User Preferences only; Supervisor sees Station Settings + User Preferences; Administrator sees all). | High | 📋 | All roles |

### 13c. Frontend — Station Settings (Supervisor+)

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| S-F2 | Station color picker — Supervisor sets the station's primary color. Live preview of the station band and vehicle card. Change applies immediately for all users at that station. Requires B-M11, S-B2. | Medium | 📋 | Supervisor+ |
| S-F3 | Allow check modification toggle — Administrator-only toggle. Shows current state with clear explanation of what enabling it allows. Requires B-M10, S-B2. | High | 📋 | Administrator only |

### 13d. Frontend — User Preferences (all roles)

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| S-F4 | Default station selector — for multi-station users (like Cindy). Sets which station is pre-selected on the home screen. Requires B-M12, S-B4. | Medium | 📋 | All roles |
| S-F5 | Display name / preferred name — overrides the Azure AD display name within the app. Useful when legal name differs from what colleagues use. Requires B-M12, S-B4. | Low | 📋 | All roles |

### 13e. Frontend — Asset Management (Administrator only)

Consolidates admin actions currently scattered across the app into one place.

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| S-F6 | Station management — create, edit, deactivate stations. Deactivation hides from all check workflows but preserves historical records. | High | 📋 | Administrator only |
| S-F7 | Vehicle / portable equipment management — add, edit, deactivate vehicles and jump bags per station. Deactivation prevents new checks but preserves history. | High | 📋 | Administrator only |
| S-F8 | Par level management — view and edit par levels per vehicle/compartment. Currently only possible via seed script. Requires B-E9 for soft-deactivation. | Medium | 📋 | Administrator only |
| S-F9 | User onboarding management — view pending user requests, approve/reject, assign role and station. Consolidates B-E14/B-E15. | Medium | 📋 | Administrator only |

---

## 14. Infrastructure / Security

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| I-1 | Add Azure Firewall to `modules/network` with UDR; FQDN allow-list | Medium | 📋 | OSI review L3-1 |
| I-2 | Re-add route table to subnets once Firewall is in place | Medium | ⛔ Blocked on I-1 | OSI review L3-2 |
| I-3 | Add `HTTPSRedirectMiddleware` to `main.py` (production-gated) | Low | 📋 | OSI review L6-1 |
| I-4 | Add `X-Content-Type-Options` and `X-Frame-Options` headers | Low | 📋 | OSI review L7-3 |
| I-5 | Document Azure AD token lifetime and confirm CAE enabled | Low | 📋 | OSI review L5-1 |
| I-6 | Write `docs/adr/ADR-006-DDoS-Strategy.md` | Low | 📋 | OSI review L4-1 |
| I-7 | Confirm Azure deployment healthy after F1 quota reset | High | 📋 | Handoff 2026-05-15 |

---

## 15. Documentation

| # | Item | Priority | Status | Source |
|---|------|----------|--------|--------|
| D-1 | Update `project_index.md` ADR table (ADR-006 slot) | Low | ✅ Done | Session 2026-05-22 |
| D-2 | Write session handoff document at end of each session | Ongoing | 📋 | Convention |
| D-3 | Update `phase5_frontend_pwa.md` status to "In Progress" | Low | 📋 | Phase 5A+5B complete |
| D-4 | Update `phase5_frontend_pwa.md` to mark 5A and 5B complete | Low | 📋 | Handoff 2026-05-15 |
| D-5 | Write `docs/deployment_flow.md` — end-to-end deployment sequence (infra → DB → backend → frontend) as a single ordered reference | Medium | 📋 | Session 2026-05-22 |
| D-6 | Write `docs/production_strategy.md` — App Service tier upgrade path, VNet integration, PostgreSQL HA, geo-redundancy, scaling triggers, SLA targets, DR | Medium | 📋 | Session 2026-05-22 |
| D-7 | Write `docs/deployment_guide.md` — complete from-scratch guide for a new deployer; deferred until feature-complete | Low | 📋 | Session 2026-05-22 |
| D-8 | Add audience-based "Who should read what" section to `README.md` — maps architects, infra engineers, app devs, security/compliance, ops/SRE to their relevant docs | Medium | 📋 | Session 2026-05-22 |
| D-9 | Write `docs/api_contract.md` — versioning policy, deprecation lifecycle, breaking vs non-breaking change rules | Medium | 📋 | Session 2026-05-22 |
| D-10 | Create visual ERD in `docs/models/erd.md` (Mermaid) — all 11 models, FK relationships, cardinality, key constraints | Low | 📋 | Session 2026-05-22 |
| D-11 | Add README badges: Python version + License (shields.io static badges — no CI changes needed) | Low | 📋 | Session 2026-05-22 |
| D-12 | Add README test coverage badge — requires `pytest-cov` + Codecov wired into CI | Low | 📋 | Session 2026-05-22 |
| D-13 | Write `docs/security.md` — auth model, RBAC, encryption, audit schema, OSI posture, compliance-facing reference | Medium | 📋 | Session 2026-05-22 |
| D-14 | Write `docs/operations.md` — health endpoints, alert thresholds, on-call runbook, log queries, rollback, DB backup/restore | Medium | 📋 | Session 2026-05-22 |
| D-15 | Document PII emergency delete procedure in `docs/operations.md` — step-by-step: identify, force-hard-delete via admin UI, verify audit event, notify relevant parties. What to never put in notes fields. | High | 📋 | Session 2026-05-22 |

---

## 16. Open Questions — Awaiting Decision

| # | Question | Owner | Source |
|---|----------|-------|--------|
| Q-1 | Notification delivery: email (Azure Comms) or in-app only? | Project owner | Phase 6 plan |
| Q-2 | Microsoft Graph user lookup: cache in DB? | Engineering | Phase 6 plan |
| Q-3 | 90-day max range sufficient for compliance calendar? | Project owner | Phase 6 plan |
| Q-4 | BLOCKING feedback bugs auto-create GitHub issue? | Project owner | Phase 6 plan |
| Q-5 | Supply room reorder tracking in Phase 6 or defer to Phase 7? | Project owner | Phase 5 plan |
| Q-6 | Auto-hard-delete after 90 days: run as a scheduled Azure Function, or an Alembic-triggered cleanup job on startup? | Engineering | Session 2026-05-22 |
| Q-7 | Check modification setting default: off (conservative, most stations) or on (permissive)? Currently modeled as default False. | Project owner | Session 2026-05-22 |
| Q-8 | Should restored soft-deleted checks (CH-B6) re-appear in the responder's history view, or only in the admin deleted-records screen? | Project owner | Session 2026-05-22 |

---

## Summary Counts

| Area | Not started | In progress | Blocked | Done |
|------|-------------|-------------|---------|------|
| Backend — Tests | 0 | 0 | 0 | 2 |
| Backend — Phase 6 Endpoints | 17 | 0 | 0 | 1 |
| Backend — Data Models | 12 | 0 | 0 | 1 |
| Backend — Code Quality | 2 | 0 | 0 | 0 |
| Frontend — Phase 5C Help | 4 | 0 | 0 | 0 |
| Frontend — Phase 5D Item Mgmt | 3 | 0 | 0 | 0 |
| Frontend — Phase 5E Vehicle | 2 | 0 | 1 | 0 |
| Frontend — Phase 5F Supervisor | 4 | 0 | 3 | 0 |
| Frontend — Phase 5G Supporting | 2 | 0 | 2 | 0 |
| Frontend — Phase 5H Infra | 4 | 0 | 0 | 0 |
| Frontend — UX Improvements | 7 | 0 | 1 | 23 |
| Check History — Backend | 8 | 0 | 0 | 0 |
| Check History — Frontend | 8 | 0 | 1 | 0 |
| Settings — Backend | 4 | 0 | 0 | 0 |
| Settings — Frontend | 9 | 0 | 0 | 0 |
| Infrastructure / Security | 6 | 0 | 1 | 0 |
| Documentation | 14 | 0 | 0 | 1 |
| **Total** | **106** | **0** | **10** | **28** |
