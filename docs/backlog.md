# EMS ReadyKit — Active Backlog
# v1.25 | Updated: 2026-05-26
# Completed items → backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ SESSION COMPLETE 2026-05-24
 See backlog_completed.md for full list.
 Key items completed this session:
   - Phase 5H: Azure Static Web Apps live, CI/CD 4-job pipeline, CORS, Azure AD redirect URIs
   - App Service upgraded F1 → B1 (VNet integration, always-on)
   - Azure AD: guest user auth working (Gmail via External Identities)
   - Supervisor Dashboard (F-5F1, F-5F3, F-5F4, F-5F5) complete
   - MEASUREMENT item LOW status — item row yellow, reconcile shows reading vs minimum
   - Draft banner: station-scoped (any responder at station can resume — shift handoff)
   - Bug fix: VITE_API_BASE_URL set in deploy.yml (stations were not loading in production)

# ✅ SESSION COMPLETE 2026-05-25
 Key items completed this session:
   - F-UX35: Draft banner station fallback — localStorage cache of last known station_id
   - Draft flow overhaul: fixed same-tab storage event (EventTarget bus), key-null race
     on first saveDraft call, type-coercion bug in station_id comparison
   - Draft resume: blank compartment screen fixed (Spinner while locationId resolves)
   - React "setState during render" warning fixed (removed functional updaters from
     saveDraft/saveLineItem, replaced with draftRef mirror)
   - Timestamp UTC fix: backend @field_serializer emits Z-suffixed datetimes;
     frontend normalizeUtc() guard added to all formatTime/formatDateTime calls
   - Azure AD auth: audience mismatch fixed (bare GUID vs api:// URI — now accepts both)
   - Production database: seed.py added to deployment zip; startup.sh auto-seeds
     when stations table is empty
   - B-ADMIN1, B-ACCESS1, UAT section added to backlog
   - Crew mode bug fixed: Compliance Dashboard now hidden in crew mode

# ✅ SESSION COMPLETE 2026-05-26
 Key items completed this session:
   - Full sanity check: dead code audit, OWASP Top 10 review, maintainability review
   - Deleted _patch_cs_message.py and _patch_get_check.py (dead code)
   - ems_readykit_dev.db added to .gitignore
   - deploy.zip added to .gitignore
   - Backlog updated: new Security section, OWASP references, session plan, refactor plan

# NEXT SESSION priority order:
   1. B-E3 (date-range compliance query) → unblocks F-5F2 calendar + F-UX7 banner
   2. CH-UX1 (unified check resolution workflow — frontend only)
   3. D-R1 documentation audit

---

## ──────────────────────────────────────────────────────────────────────────────
## SESSION PLAN
## ──────────────────────────────────────────────────────────────────────────────
##
## Sessions are ordered by dependency and risk. Complete Critical items before
## inviting any real users. Items within a session can run in parallel where noted.
##
## Session A — Security Gate (1–2 hrs) — MUST COMPLETE BEFORE REAL USERS
##   SEC-1   pip-audit in CI (A06)                             ~20 min
##   SEC-2   Disable OpenAPI docs in production (A05)          ~15 min
##   SEC-3   Security headers middleware (A05, I-4)            ~15 min
##   SEC-4   Production startup assertion: secret_key (A02)    ~10 min
##   SEC-5   B-Q1 structured logging — inventory/stations/
##           vehicles/items (A09)                              ~45 min
##   SEC-6   Document secondary_signer limitation (A04)        ~10 min
##
## Session B — Refactor Sprint (2–3 hrs) — DO BEFORE PHASE 6 BACKEND WORK
##   REF-1   Extract _write_audit_event() to core/audit.py     ~30 min
##   REF-2   Move _get_vehicle_or_404() to deps.py             ~20 min
##   REF-3   Move _ALL_ROLES / _SUPERVISOR_PLUS to deps.py     ~20 min
##   REF-4   Move require_station_membership() to deps.py      ~20 min
##   REF-5   Consolidate frontend CSS patch files              ~30 min
##   REF-6   B-Q2 standardise extra={} logging in auth.py      ~15 min
##
## Session C — Access Control Enforcement (3–4 hrs) — MUST COMPLETE BEFORE REAL USERS
##   ACC-B7  Station membership check on /checks endpoints     ~60 min
##   ACC-B8  Station membership check on /vehicles + /inventory~60 min
##   ACC-B9  Station membership check on supervisor endpoints  ~30 min
##   (depends on Session B / REF-4 being done first)
##
## Session D — Today's Features (2–3 hrs)
##   B-E3    Date-range compliance query endpoint              ~60 min
##   CH-UX1  Unified check resolution workflow (frontend)      ~90 min
##   D-R1    Documentation audit                               ~60 min
##
## Session E — Core Features (3–4 hrs per session, multiple sessions)
##   B-E5, B-E6, ADMIN-B1–B10, ADMIN-F1–F5, RET-* items
##
## Session F — UAT (1–2 hrs)
##   UAT-1 through UAT-8 (after Session C completes)
##
## ──────────────────────────────────────────────────────────────────────────────

---

## 0. Security — Pre-User Gate [CRITICAL — Do Before Any Real Users]

These items address OWASP Top 10 vulnerabilities found in the 2026-05-26 code review.
None require architectural changes. All are small, targeted fixes.

### 0a. OWASP A01 — Broken Access Control
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-B7 | Enforce station membership in `GET /checks/daily` and check submission | **Critical** | 📋 | 403 if user not member of station. Move `require_station_membership()` to `deps.py` first (REF-4). |
| ACC-B8 | Enforce station membership in all `/vehicles` and `/inventory` endpoints | **Critical** | 📋 | A Responder at Newberg must not be able to query Marcellus vehicles. |
| ACC-B9 | Enforce station membership in supervisor dashboard endpoints | **Critical** | 📋 | |
| ACC-B10 | `deps.py`: add `require_station_membership(station_id)` dependency | **Critical** | 📋 | Reusable FastAPI dep; replaces inline copy in `stations.py`. REF-4. |

### 0b. OWASP A02 — Cryptographic Failures
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-4 | Add startup assertion: `assert settings.secret_key != "change-me-in-production"` when `is_production` | High | 📋 | Add to `create_app()` in `main.py`. Prevents accidental dev-key deployment. |

### 0c. OWASP A04 — Insecure Design
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-6 | Document `secondary_signer` free-text limitation in `checks.py` and `runbook.md` | High | 📋 | The dual-signature check compares names as strings — a determined user could spoof. This is a known architectural gap; the real fix is F-UX34 (structured user picker). Until then, document it. |
| F-UX34 | Second crew picker — structured user lookup replacing free-text `secondary_signer` | Medium | ⛔ | OWASP A04. Needs B-M15, B-E7. This is the real fix for SEC-6. |

### 0d. OWASP A05 — Security Misconfiguration
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-2 | Disable OpenAPI `/docs` and `/redoc` in production | High | 📋 | OWASP A05. In `main.py`: `docs_url=None if settings.is_production else "/docs"`. One-line change. |
| SEC-3 | Add security headers middleware to `main.py` | High | 📋 | OWASP A05. Set `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` via a response middleware. Supersedes I-4. |
| I-3 | `HTTPSRedirectMiddleware` in `main.py` (production-gated) | Low | 📋 | OWASP A05. Defense-in-depth if ever moved behind a different proxy. |

### 0e. OWASP A06 — Vulnerable and Outdated Components
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-1 | Add `pip-audit` as a CI step in `.github/workflows/deploy.yml` test job | High | 📋 | OWASP A06. Runs before tests. Fails the build on known CVEs. Command: `pip install pip-audit && pip-audit -r requirements.txt`. |

### 0f. OWASP A09 — Security Logging and Monitoring Failures
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-5a | Add structured `logger` calls to `inventory.py` — POST/PATCH mutations | **Critical** | 📋 | OWASP A09. Supervisor creating/editing stock lots currently leaves no log line. Include `entity_type`, `entity_id`, actor in `extra={}`. |
| SEC-5b | Add structured `logger` calls to `stations.py` — POST mutations | **Critical** | 📋 | OWASP A09. |
| SEC-5c | Add structured `logger` calls to `vehicles.py` — POST mutations | **Critical** | 📋 | OWASP A09. `repair_requests.py` already has logging; `vehicles.py` GET/POST do not. |
| SEC-5d | Add structured `logger` calls to `items.py` — POST mutations | **Critical** | 📋 | OWASP A09. |

---

## 1. Code — Refactoring Sprint [HIGH — Do Before Phase 6 Backend Work]

These items fix the maintainability issues found in the 2026-05-26 review.
Each is a safe, mechanical change. The full change map is in Section 25 (Refactor Plan).

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| REF-1 | Extract `_write_audit_event()` to `app/ems_readykit/core/audit.py` | High | 📋 | Currently defined in `checks.py`, called inline-differently in 3 other routers. See Section 25. |
| REF-2 | Move `_get_vehicle_or_404()` to `deps.py` | High | 📋 | Duplicated identically in `checks.py` and `repair_requests.py`. |
| REF-3 | Move `_ALL_ROLES` and `_SUPERVISOR_PLUS` constants to `deps.py` | High | 📋 | Redefined in every router (9 files). Single source of truth. |
| REF-4 | Move `require_station_membership()` from `stations.py` to `deps.py` | High | 📋 | Must be in `deps.py` before ACC-B7/B8/B9 can use it without circular imports. |
| REF-5 | Consolidate frontend CSS patch files into module or `src/styles/` | Medium | 📋 | `submitted-screen-patch.css`, `module-card-fix.css`, `wizard-station.css`, `wizard.css` all imported from root in `main.jsx`. |
| REF-6 | Standardise `extra={}` logging shape in `core/auth.py` | Low | 📋 | Supersedes B-Q2. JWKS failure log lines are missing `extra={}` fields that the rest of the codebase uses. |

---

## 2. Backend — Phase 6 Endpoints
| # | Endpoint | Description | Pri | Status | Needs |
|---|----------|-------------|-----|--------|-------|
| B-E3 | `GET /checks/daily/station/{id}?from=&to=` | Date-range compliance query | High | 📋 | |
| B-E5 | `POST /inventory/transfer` | Move stock between supply room and vehicle | High | 📋 | |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` | Stock vs par per item | High | 📋 | |
| B-E7 | `GET /stations/{id}/users` | Active users at station via MS Graph | Medium | 📋 | |
| B-E8 | `PUT /inventory/lots/{id}` | Supervisor corrects expiry date on lot | Medium | 📋 | |
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 | |
| B-E10 | `POST /feedback` | Submit bug/enhancement/general feedback | Medium | 📋 | |
| B-E11 | `GET /feedback` | List feedback (Administrator only) | Medium | 📋 | |
| B-E12 | `GET /notifications` | Unread notifications scoped by role | Medium | 📋 | |
| B-E13 | `PATCH /notifications/{id}/read` | Mark notification read | Medium | 📋 | |
| B-E14 | `POST /admin/user-requests` | Supervisor submits user onboarding request | Medium | 📋 | |
| B-E15 | `GET /admin/user-requests` | List user requests (Administrator only) | Medium | 📋 | |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 | |

*All paths prefixed `/api/v1/`*

---

## 3. Backend — Data Models
| # | Item | Pri | Status |
|---|------|-----|--------|
| B-M2 | New table: `notifications` | Medium | 📋 |
| B-M3 | New table: `feedback_entries` | Medium | 📋 |
| B-M4 | New table: `user_requests` | Medium | 📋 |
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 |
| B-M8 | Alter `daily_inventory_checks`: add `started_by` (check handoff) | Medium | 📋 |
| B-M10 | Alter `stations`: add `allow_check_modification` (Boolean, default False) | High | 📋 |
| B-M11 | Alter `stations`: add `primary_color` (String, nullable) | Medium | 📋 |
| B-M12 | New table: `user_preferences` | Medium | 📋 |
| B-M13 | Alter `inventory_lots`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| B-M14 | New table: `loaned_items` | Medium | 📋 |
| B-M15 | Alter `daily_inventory_checks`: add `second_crew_id` (String, nullable) | Medium | 📋 |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M4 | Scheduled nightly job: hard-delete retired objects where `retired_at` > 5 yrs | High | 📋 |

---

## 4. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Administrator force hard-delete (PII spill) | High | 📋 | Admin only |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks within 90-day window | Medium | 📋 | Admin only |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted check within 90-day window | Low | 📋 | Admin only |
| CH-B7 | `PATCH /stations/{id}/settings` | Update station settings incl. `allow_check_modification` | High | 📋 | Admin only |
| CH-B8 | `GET /stations/{id}/settings` | Read station settings | High | 📋 | Supervisor+ |
| CH-B9 | `GET /checks/daily/crew-history` | Checks where current user is second crew | Medium | ⛔ | B-M15 |

---

## 5. Backend — Retirement Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | Retire vehicle | High | 📋 | Supervisor+ |
| RET-B2 | `PATCH /locations/{id}/retire` | Retire jump bag / portable location | High | 📋 | Supervisor+ |
| RET-B3 | `PATCH /stations/{id}/retire` | Retire station | High | 📋 | Admin only |
| RET-B4 | `GET /admin/retired?type=&station_id=` | List retired objects | Medium | 📋 | Admin only |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | Retire a specific lot | High | 📋 | Supervisor+; needs B-M13 |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | List retired lots | Medium | 📋 | Supervisor+ |

---

## 6. Backend — Loaned Item Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| LOAN-B1 | `POST /equipment/loans` | Record a loan | Medium | 📋 | All roles; needs B-M14 |
| LOAN-B2 | `PATCH /equipment/loans/{id}/resolve` | Mark loan resolved | Medium | 📋 | All roles |
| LOAN-B3 | `GET /equipment/loans?vehicle_id=&resolved=false` | Open loans for a vehicle | Medium | 📋 | Supervisor+ |
| LOAN-B4 | `GET /equipment/loans/my?resolved=false` | Current user's open loans | Medium | 📋 | All roles |

---

## 7. Frontend — Phase 5C: Help System
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5C1 | First-run tutorial — 8 steps, auto-shown on first login, replayable, skip button | High | 📋 |
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | High | 📋 |
| F-5C3 | Searchable FAQ — client-side filter, crew + supervisor sections, 15 questions | Medium | 📋 |
| F-5C4 | `src/modules/help/content.js` — single source of truth for all help text | Medium | 📋 |

---

## 8. Frontend — Phase 5D: Item Management
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5D1 | Item catalog search component | Medium | 📋 |
| F-5D2 | Add item form — Responder requests; Supervisor/Admin adds directly | Medium | 📋 |
| F-5D3 | Remove item with mandatory documented reason | Medium | 📋 |

---

## 9. Frontend — V&E Status (remaining)
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| VE-F2 | Open loans panel — unresolved loans per vehicle; Resolve button per row | Medium | 📋 | LOAN-B3 |
| VE-F3 | Log a loan form — lot picker + destination note field | Medium | 📋 | LOAN-B1 |
| VE-F4 | Resolve loan modal — optional note, calls LOAN-B2 | Medium | 📋 | LOAN-B2 |

---

## 10. Frontend — Phase 5F: Supervisor Dashboard
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-5F2 | Monthly compliance calendar — color-coded per vehicle per day | High | ⛔ | B-E3 |
| F-5F6 | Notification bell with unread badge | Medium | ⛔ | B-E12 |
| F-5F7 | Supply room stock view (stock vs par, color coded, reorder form) | Medium | 📋 | B-E6 |

---

## 11. Frontend — Phase 5G: Supporting Modules
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-5G1 | Feedback module — floating button, bug/enhancement/general form | Medium | 📋 | |
| F-5G2 | User management module | Medium | ⛔ | B-E14 |
| F-5G3 | Data export — CSV for check history, audit events, repair requests | Medium | 📋 | |
| F-5G4 | Role switcher (crew mode for supervisors) — amber CREW MODE badge | Low | 📋 | |

---

## 12. Frontend — Check Wizard UX
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-UX2 | Left/right chevron navigation between compartments | Medium | 📋 | |
| F-UX3 | "Jump to unvalidated" sticky button | Medium | 📋 | |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | |
| F-UX7 | **Last check banner** — on the home screen, show when the most recent daily check was completed for the selected station and by whom (e.g. "Unit 712 checked today at 6:21 AM by Cindy"). Auto-visible on login so incoming shift knows immediately if the check is done. Shown per vehicle; color-coded green (checked today) / amber (checked yesterday) / red (not checked). | High | 📋 | Needs B-E3 for date-range query |
| F-UX8 | Item count on compartment cards | Low | 📋 | |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | |
| F-UX10 | "Caller/spotter view" large-text mode | Low | 📋 | |
| F-UX32 | BORROWED badge on loaned items during check; shortcut to V&E Status | Medium | 📋 | B-M14 |
| F-UX34 | Second crew picker — structured user lookup replacing free-text field | Medium | ⛔ | OWASP A04 (real fix for SEC-6). Needs B-M15, B-E7. |
| F-UX35 | Draft banner visible while station API loading — cache last known station_id in localStorage as fallback | High | 📋 | |

---

## 13. Frontend — Check History (remaining)
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note on submitted check | High | ⛔ | B-M10, CH-B8 |
| CH-F7 | Deleted records screen (Admin) — restore or force hard-delete | High | 📋 | |
| CH-F8 | Force hard-delete confirmation — type "PERMANENTLY DELETE" to confirm | High | 📋 | |
| CH-F9 | "Checks I helped with" tab in Check History | Medium | ⛔ | B-M15, CH-B9 |

---

## 14. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F1 | Settings nav entry — role-scoped visibility | High | 📋 | |
| S-F2 | Station color picker (Supervisor+) — live preview | Medium | 📋 | B-M11 |
| S-F3 | Allow check modification toggle (Admin only) | High | 📋 | B-M10 |
| S-F4 | Default station selector (all roles) | Medium | 📋 | B-M12 |
| S-F5 | Display name / preferred name override (all roles) | Low | 📋 | B-M12 |
| S-F6 | Station management — create, edit, retire | High | 📋 | RET-B3/B4 |
| S-F7 | Vehicle / portable equipment management — add, edit, retire | High | 📋 | RET-B1/B2 |
| S-F8 | Par level management — view and edit per vehicle/compartment | Medium | 📋 | B-E9 |
| S-F9 | User onboarding management — approve/reject, assign role + station | Medium | 📋 | B-E14/15 |

---

## 15. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle (Supervisor+) | High | 📋 | RET-B1 |
| RET-F2 | Retire jump bag / portable location (Supervisor+) | High | 📋 | RET-B2 |
| RET-F3 | Retire inventory lot (Supervisor+) | High | 📋 | RET-B5, B-M13 |
| RET-F4 | Retire station (Admin only) | High | 📋 | RET-B3 |
| RET-F5 | Retired objects list (Admin) — filterable by type, read-only | Medium | 📋 | RET-B4 |

---

## 16. Infrastructure / Security
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall in `modules/network` with UDR + FQDN allow-list | Medium | 📋 | |
| I-2 | Re-add route table to subnets | Medium | ⛔ | I-1 |
| I-3 | `HTTPSRedirectMiddleware` in `main.py` (production-gated) | Low | 📋 | OWASP A05. Defense-in-depth. See SEC-3. |
| I-4 | `X-Content-Type-Options` and `X-Frame-Options` headers | Low | 📋 | Superseded by SEC-3 — do SEC-3 first. |
| I-5 | Document Azure AD token lifetime; confirm CAE enabled | Low | 📋 | |
| I-6 | Write `docs/adr/ADR-006-DDoS-Strategy.md` | Low | 📋 | |

---

## 17. Equipment & Station Administration (B-ADMIN1)

Access: Administrator + Supervisor
Entry point: "Admin" card on home page, visible to Administrator + Supervisor roles only.

### Phase 1 — Item & Par Management (next sprint)
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B1 | `GET /admin/items` | List global item catalog with filters (category, check_type, active) | High | 📋 | |
| ADMIN-B2 | `POST /admin/items` | Add item to global catalog | High | 📋 | Admin + Supervisor |
| ADMIN-B3 | `PATCH /admin/items/{id}` | Edit item (name, category, UOM, flags) | High | 📋 | Admin + Supervisor |
| ADMIN-B4 | `PATCH /admin/items/{id}/deactivate` | Soft-deactivate item (removes from future checks, keeps history) | High | 📋 | Admin only |
| ADMIN-B5 | `GET /admin/locations/{id}/par-levels` | List par levels for a location/compartment | High | 📋 | |
| ADMIN-B6 | `POST /admin/par-levels` | Add item to compartment with min/max qty | High | 📋 | Admin + Supervisor |
| ADMIN-B7 | `PATCH /admin/par-levels/{id}` | Edit min/max qty on a par level | High | 📋 | Admin + Supervisor |
| ADMIN-B8 | `PATCH /admin/par-levels/{id}/deactivate` | Remove item from compartment (soft) | High | 📋 | Admin only |
| ADMIN-B9 | `POST /admin/compartments` | Add compartment to a location | High | 📋 | Admin + Supervisor |
| ADMIN-B10 | `PATCH /admin/compartments/{id}` | Edit compartment (name, sort order, descriptor, restriction note) | High | 📋 | Admin + Supervisor |
| ADMIN-F1 | Admin home card — visible to Administrator + Supervisor | High | 📋 | |
| ADMIN-F2 | Item catalog list view — search, filter by category/check type, active toggle | High | 📋 | |
| ADMIN-F3 | Add/edit item form | High | 📋 | |
| ADMIN-F4 | Par level editor — select location → compartment → add/edit/remove items | High | 📋 | |
| ADMIN-F5 | Compartment editor — add/edit compartments within a location | High | 📋 | |
| ADMIN-F10 | Member list search — client-side filter by name or email; sort by name or role already implemented | Low | 📋 | Needed once stations have 20+ members |

### Phase 2 — Vehicle & Location Management
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B11 | `POST /admin/vehicles` | Add vehicle to a station | High | 📋 | Admin + Supervisor |
| ADMIN-B12 | `PATCH /admin/vehicles/{id}` | Edit vehicle (number, type, active) | High | 📋 | Admin + Supervisor |
| ADMIN-B13 | `POST /admin/locations` | Add portable location (jump bag, supply room) to a station | High | 📋 | Admin + Supervisor |
| ADMIN-B14 | `PATCH /admin/locations/{id}` | Edit location label/type | High | 📋 | Admin + Supervisor |
| ADMIN-F6 | Vehicle list view per station — add, edit, retire | High | 📋 | |
| ADMIN-F7 | Portable location list view per station — add, edit, retire | High | 📋 | |

### Phase 3 — Station Onboarding
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B15 | `POST /admin/stations` | Create new station | Medium | 📋 | Admin only |
| ADMIN-B16 | `POST /admin/stations/{id}/clone-layout` | Copy compartment + par layout from an existing station | Medium | 📋 | Admin only; big time saver for new units |
| ADMIN-F8 | New station wizard — name, address, region, seed from template or blank | Medium | 📋 | |
| ADMIN-F9 | Layout clone picker — choose source station/vehicle, preview before applying | Medium | 📋 | |

---

## 18. Station Membership & Access Control (B-ACCESS1)

**Problem:** Currently `GET /api/v1/stations` returns all active stations to any
authenticated user. Stations, vehicles, equipment, and check history should only
be visible to users assigned to that station. Administrators assign Supervisors;
Supervisors and Administrators assign Responders.

**Access rules:**
- Administrator — can see all stations; assigns Supervisors to stations
- Supervisor — sees only their assigned stations; assigns Responders to their stations
- Responder — sees only their assigned stations; no assignment permissions

**Downstream impact:** Once this is live, every station-scoped endpoint
(`/checks`, `/vehicles`, `/inventory`, `/stations`) must filter by membership.
The data model (station_members table) and GET /stations/my are already implemented.
Phase 4 enforcement (ACC-B7–B10) is the remaining work. See Section 0a (OWASP A01).

### Backend — Data Model [COMPLETE]
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-M1 | New table: `station_members` | ✅ Done | — | Implemented 2026-05-25 |
| ACC-M2 | Migration: add `station_members` table | ✅ Done | — | Implemented 2026-05-25 |

### Backend — Endpoints [COMPLETE]
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| ACC-B1 | `GET /stations/{id}/members` | List members of a station | ✅ Done | — | Implemented 2026-05-25 |
| ACC-B2 | `POST /stations/{id}/members` | Add user to station with role | ✅ Done | — | Implemented 2026-05-25 |
| ACC-B3 | `PATCH /stations/{id}/members/{user_id}` | Change member role | ✅ Done | — | Implemented 2026-05-25 |
| ACC-B4 | `DELETE /stations/{id}/members/{user_id}` | Remove user from station | ✅ Done | — | Implemented 2026-05-25 |
| ACC-B5 | `GET /stations/my` | Return only stations the current user is assigned to | ✅ Done | — | Implemented 2026-05-25 |
| ACC-B6 | `GET /stations` | Return all stations (Administrator only) | ✅ Done | — | Implemented 2026-05-25 |

### Backend — Access Enforcement [CRITICAL — see Section 0a]
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-B7 | Enforce station membership in `/checks` | **Critical** | 📋 | Listed in Section 0a |
| ACC-B8 | Enforce station membership in `/vehicles` + `/inventory` | **Critical** | 📋 | Listed in Section 0a |
| ACC-B9 | Enforce station membership in supervisor dashboard | **Critical** | 📋 | Listed in Section 0a |
| ACC-B10 | `deps.py`: `require_station_membership()` dependency | **Critical** | 📋 | Listed in Section 0a |

### Frontend
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-F1 | Station picker uses `GET /stations/my` instead of `GET /stations` | High | 📋 | Single-line change once ACC-B5 exists (it does) |
| ACC-F2 | Member list view — per station, shows name + role + assigned date | High | 📋 | Supervisor+ |
| ACC-F3 | Add member form — name/email + role picker; Admin sees Supervisor option | High | 📋 | |
| ACC-F4 | Remove member confirmation — with role-based guard on who can remove whom | High | 📋 | |
| ACC-F5 | "Pending assignment" screen — warm holding page for unassigned authenticated users | High | 📋 | |

### Open Questions
| # | Question | Owner |
|---|----------|-------|
| Q-11 | User lookup when adding a member: MS Graph search or free-text name+email entry? | Engineering |
| Q-12 | Users can be assigned to multiple stations simultaneously (confirmed). | ✅ Resolved |
| Q-13 | Seed data: auto-assign seeded admin to all stations on first deploy? Dowagiac is a real third station — add to seed.py when details available. | Engineering |
| Q-14 | Grace period for unassigned users: confirmed — friendly pending assignment screen. | ✅ Resolved |

---

## 19. Documentation
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| D-R1 | **Documentation audit** — full review of all existing and planned docs | High | 📋 | See criteria below |

### D-R1 Criteria
Review every file in `docs/` plus `README.md`:
- **Value:** Does it need to exist? App value? Portfolio value? Can docs be merged?
- **Security:** Auth model, RBAC matrix, token lifecycle, encryption, secrets, audit schema, threat model, incident response, PII procedure, data retention
- **Portfolio signal:** Problem-first README, decision-oriented ADRs, full lifecycle coverage, clear current vs planned separation
- **Quality:** Precise, concise, no filler, correct commands, professional tone

**Output:** Keep / rewrite / merge / drop / create list.

---

## 20. User Acceptance Testing (UAT)

Before releasing to real users, provide structured test cases covering all roles and workflows.

### Scope
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-1 | Write test case document — one sheet per role (Responder, Supervisor, Administrator) | High | 📋 | See criteria below |
| UAT-2 | Responder test cases — daily check happy path, draft resume, check history | High | 📋 | |
| UAT-3 | Supervisor test cases — crew mode hides dashboard, compliance dashboard, acknowledge check, check history all tab | High | 📋 | |
| UAT-4 | Administrator test cases — all supervisor cases plus station management, user assignment | High | 📋 | |
| UAT-5 | Cross-role test cases — draft visible to other responder at same station, Supervisor can see all checks at station | Medium | 📋 | |
| UAT-6 | Edge case test cases — resume after browser close, two drafts at same station, submit with failed items | Medium | 📋 | |
| UAT-7 | Pending assignment test case — new user sees friendly holding screen, not a 403 | High | ⛔ | Needs ACC-F5 |
| UAT-8 | Multi-station test case — user assigned to two stations can switch between them | Medium | ⛔ | Needs B-ACCESS1 |

### Test Case Document Criteria
Each test case should include:
- **Role** being tested
- **Preconditions** (e.g. "logged in as Responder, TEST STATION selected")
- **Steps** numbered, specific, non-technical (written for a crew member, not a developer)
- **Expected result** — what the user should see
- **Pass / Fail** checkbox
- **Notes** field for the tester to record what actually happened

Format: Google Doc or PDF shared with testers. Not a GitHub issue or markdown file — needs to be printable and fillable by non-technical users.

---

## 21. Check Resolution Workflow (CH-UX1)

**Problem:** The FAIL resolution workflow is split across two screens with no connection
between them. Supervisors must visit Check History to acknowledge, then the Compliance
Dashboard to record a fix — and even after doing both, the check still visually shows
as FAIL with no resolved state.

**Proposed solution — unified resolution in Check History:**
  1. FAIL check detail shows failed items callout (already exists)
  2. Single "✓ Acknowledge & Record Resolution" button opens one panel
  3. Panel captures: what was fixed (free text) + resolved? (Yes / Still pending)
  4. On submit: saves corrective_action, sets reviewed_at/reviewed_by,
     visually marks check as "Acknowledged — Resolved" or "Acknowledged — Pending"
  5. Compliance Dashboard "I Fixed This" remains for supervisors who prefer that workflow

**Backend impact:** No new endpoints needed. Uses existing `PATCH /checks/daily/{id}/acknowledge`.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| CH-UX1-F1 | Bring `IFixedThisForm` into `CheckDetail.jsx` — supervisor can acknowledge + resolve from Check History | High | 📋 | No backend change needed |
| CH-UX1-F2 | Unified resolution panel — single form captures corrective action + resolved/pending toggle | High | 📋 | |
| CH-UX1-F3 | Resolved/Pending visual state on check detail — clear badge showing outcome | High | 📋 | |
| CH-UX1-F4 | Compliance Dashboard "I Fixed This" updated to use same unified panel | Medium | 📋 | |
| CH-UX1-F5 | After resolution, check card in history list shows "Resolved" indicator | Medium | 📋 | |

---

## 25. Refactor Plan [Complete change map — no application breakage]

This section is the authoritative implementation guide for the refactoring items
in Section 1 (REF-1 through REF-6). Each change is backward-compatible.
Do these in order — later items depend on earlier ones.

### REF-1 — Extract `_write_audit_event()` to `core/audit.py`

**Why:** The helper is defined in `checks.py` but three other routers write
`AuditEvent(...)` objects inline without the accompanying `logger.info()` call.
Centralising ensures every audit write also emits a structured log line.

**New file: `app/ems_readykit/core/audit.py`**
```python
# core/audit.py
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from ems_readykit.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)

def write_audit_event(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    severity: str = "INFO",
) -> None:
    event = AuditEvent(
        actor=actor, action=action, entity_type=entity_type,
        entity_id=entity_id, station_id=station_id, vehicle_id=vehicle_id,
        metadata_json=metadata, severity=severity,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    logger.info(
        "Audit event written",
        extra={"action": action, "entity_type": entity_type,
               "entity_id": entity_id, "severity": severity},
    )
```

**Files to update:**
- `checks.py` — remove `_write_audit_event()` definition; add `from ems_readykit.core.audit import write_audit_event`; rename call sites.
- `check_history.py` — replace inline `db.add(AuditEvent(...)) / db.commit()` blocks with `write_audit_event(...)`. Note: `check_history.py` does NOT call `db.commit()` after adding the AuditEvent inline — it relies on a subsequent commit. `write_audit_event()` commits internally; adjust the surrounding code to not double-commit.
- `repair_requests.py` — same pattern as `check_history.py`. Already has `logger.info()` calls; these stay as-is alongside `write_audit_event()`.
- `vehicles.py` (repair_requests router) — the `update_vehicle_status` handler writes AuditEvent inline; replace.

**Risk:** Low. The function signature is the same as the existing `_write_audit_event()`. The only behavioral change is that `check_history.py` and `repair_requests.py` now also get the `logger.info("Audit event written")` call.

**Test:** Run `pytest tests/ -v` after this change. Audit event tests should pass unchanged.

---

### REF-2 — Move `_get_vehicle_or_404()` to `deps.py`

**Why:** Defined identically in both `checks.py` and `repair_requests.py`.

**Change in `deps.py`:** Add after the existing `require_role()` function:
```python
from ems_readykit.models.vehicle import Vehicle

def get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found.",
        )
    return vehicle
```

**Files to update:**
- `checks.py` — remove `_get_vehicle_or_404()`; add `from ems_readykit.routers.deps import get_vehicle_or_404`; update call sites (drop the underscore).
- `repair_requests.py` — same.

**Risk:** None. Pure extraction — identical logic.

---

### REF-3 — Move `_ALL_ROLES` / `_SUPERVISOR_PLUS` to `deps.py`

**Why:** Redefined in 9 router files. Will drift when a new role is added.

**Change in `deps.py`:** Add after the imports:
```python
from ems_readykit.core.auth import ROLE_ADMINISTRATOR, ROLE_SUPERVISOR, ROLE_RESPONDER

ALL_ROLES       = (ROLE_RESPONDER, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
SUPERVISOR_PLUS = (ROLE_SUPERVISOR, ROLE_ADMINISTRATOR)
ADMIN_ONLY      = (ROLE_ADMINISTRATOR,)
```

**Files to update (remove local definitions, add import):**
- `checks.py`, `check_history.py`, `station_members.py`, `stations.py`,
  `vehicles.py`, `inventory.py`, `repair_requests.py`, `items.py`, `audit.py`
- Each file: remove the 2–3 lines defining `_ALL_ROLES` / `_SUPERVISOR_PLUS` / `_ADMIN_ONLY`.
- Add to import: `from ems_readykit.routers.deps import ALL_ROLES, SUPERVISOR_PLUS, ADMIN_ONLY`
- Update all usage sites (remove leading underscore from names).

**Risk:** Low. Purely a rename + import change. No logic changes.

**Important:** `_ADMIN_ONLY` is only defined in `station_members.py` and `stations.py`. Include it in `deps.py` so all three are in one place even if not yet used everywhere.

---

### REF-4 — Move `require_station_membership()` from `stations.py` to `deps.py`

**Why:** This function will be needed by `checks.py`, `vehicles.py`, and `inventory.py`
for ACC-B7/B8/B9. If it stays in `stations.py`, those routers must import from `stations.py`,
creating a semantic mismatch. `stations.py` already imports from `deps.py` — moving this
function there eliminates any risk of circular imports.

**Change in `deps.py`:** Add after `require_role()`:
```python
from ems_readykit.models.station_member import StationMember

def require_station_membership(station_id: int, current_user: CurrentUser, db: Session) -> None:
    """
    Raises HTTP 403 if the current user is not an active member of the station.
    Administrators bypass this check — they have access to all stations.
    """
    if current_user.has_role(ROLE_ADMINISTRATOR):
        return
    member = db.query(StationMember).filter(
        StationMember.station_id == station_id,
        StationMember.user_id    == current_user.email,
        StationMember.active     == True,
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this station.",
        )
```

**Files to update:**
- `stations.py` — remove `require_station_membership()` definition; add
  `from ems_readykit.routers.deps import require_station_membership`; all call sites unchanged.

**Risk:** None. Pure move, no logic change.

---

### REF-5 — Consolidate frontend CSS patch files

**Why:** `submitted-screen-patch.css`, `module-card-fix.css`, `wizard-station.css`,
and `wizard.css` are all imported from `src/` root in `main.jsx`. They are patch files
from rapid iteration that should be merged into the relevant module CSS.

**Approach:**
1. Create `src/styles/` directory.
2. Move `wizard.css` and `wizard-station.css` into `src/styles/` (wizard-wide scope).
3. Review `submitted-screen-patch.css` and `module-card-fix.css` — move each rule into
   the CSS file of the component it fixes.
4. Update imports in `main.jsx`.

**Risk:** Low. CSS rules are additive; no JS logic changes. Test visually on the check
wizard, submitted screen, and module cards after moving.

---

### REF-6 — Standardise `extra={}` logging in `core/auth.py`

**Why:** JWKS failure and token rejection log lines in `auth.py` use plain string
interpolation without `extra={}`, so they don't appear in Log Analytics structured queries.

**Files to update:**
- `core/auth.py` — update the three `logger.warning(...)` calls to include `extra={}`:
  - JWKS failure: `extra={"action": "JWKS_LOOKUP_FAILED", "error": str(exc)}`
  - Token validation failure: `extra={"action": "TOKEN_REJECTED", "token_aud": token_aud, "accepted_audiences": accepted_audiences}`
  - Tenant mismatch: `extra={"action": "TENANT_MISMATCH", "token_tid": token_tid, "expected_tid": settings.azure_ad_tenant_id}`

**Risk:** None. Log format change only. Tests do not assert on log output.

---

## 26. Open Questions
| # | Question | Owner |
|---|----------|-------|
| Q-1 | Notification delivery: email (Azure Comms) or in-app only? | Project owner |
| Q-2 | MS Graph user lookup: cache in DB? | Engineering |
| Q-3 | 90-day max range sufficient for compliance calendar? | Project owner |
| Q-4 | BLOCKING feedback bugs auto-create GitHub issue? | Project owner |
| Q-5 | Supply room reorder tracking: Phase 6 or defer to Phase 7? | Project owner |
| Q-6 | Auto-hard-delete scheduler: Azure Function or startup cleanup job? | Engineering |
| Q-7 | Check modification setting default: False (conservative) or True (permissive)? | Project owner |
| Q-8 | Restored soft-deleted checks: responder history or admin screen only? | Project owner |
| Q-9 | 5-year hard-delete job: share with Q-6 or separate process? | Engineering |
| Q-10 | Second crew lookup: MS Graph or local user list? Affects B-E7 and F-UX34. | Engineering |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Security — Pre-User Gate (Section 0) | 12 | 0 | 12 |
| Code — Refactoring Sprint (Section 1) | 6 | 0 | 6 |
| Backend — Phase 6 Endpoints | 13 | 0 | 13 |
| Backend — Data Models | 15 | 0 | 15 |
| Backend — Check History | 5 | 1 | 6 |
| Backend — Retirement | 6 | 0 | 6 |
| Backend — Loaned Items | 4 | 0 | 4 |
| Frontend — Phase 5C Help | 4 | 0 | 4 |
| Frontend — Phase 5D Item Mgmt | 3 | 0 | 3 |
| Frontend — V&E Status (remaining) | 3 | 0 | 3 |
| Frontend — Phase 5F Supervisor | 1 | 2 | 3 |
| Frontend — Phase 5G Supporting | 3 | 1 | 4 |
| Frontend — Check Wizard UX | 11 | 2 | 13 |
| Frontend — Check History (remaining) | 3 | 1 | 4 |
| Frontend — Settings | 9 | 0 | 9 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Infrastructure / Security | 5 | 1 | 6 |
| Equipment & Station Admin (B-ADMIN1) | 19 | 0 | 19 |
| Station Membership (B-ACCESS1) | 5 | 0 | 5 |
| Documentation | 1 | 0 | 1 |
| User Acceptance Testing (UAT) | 6 | 2 | 8 |
| Check Resolution Workflow (CH-UX1) | 5 | 0 | 5 |
| **Total** | **163** | **10** | **173** |
