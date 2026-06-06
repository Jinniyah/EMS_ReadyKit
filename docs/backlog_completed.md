# EMS ReadyKit — Completed Items
# Last updated: 2026-06-06

---

## Session K (post-close) — Production Fixes + Supply Room Setup
| # | Item | Completed |
|---|------|-----------|
| FIX-1 | Migration 0018 fix — added `CURRENT_TIMESTAMP` for `created_at`/`updated_at` in raw SQL INSERTs; `TimestampMixin` uses Python-side `default=` only, not `server_default` | 2026-06-06 |
| FIX-2 | `POST /stations/{id}/supply-room` — create supply room on demand (get-or-create + Shelf 1–4); Supervisor+; fixes stations created via admin UI that never ran seed.py | 2026-06-06 |
| FIX-3 | Supply room screen — 404 detected as `roomMissing` state; shows "Set Up Supply Room" button instead of crashing; calls FIX-2 then loads normal UI | 2026-06-06 |
| FIX-4 | `app/initial_stock.csv` — 10 seed stock items (quantities, lot numbers, expiry dates) ready to upload via Receive New Stock → CSV | 2026-06-06 |

---

## Backend — Tests
| # | Item | Completed |
|---|------|-----------|
| B-T1 | Write `TestCheckTypes` class: MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, Jump Bag location | 2026-05-22 |
| B-T2 | Update duplicate check test → `test_multiple_checks_same_vehicle_same_day_all_succeed` | 2026-05-22 |

---

## Backend — Data Models
| # | Item | Completed |
|---|------|-----------|
| B-M0 | Migration 0005: drop `uq_check_vehicle_date`; replace with non-unique `ix_check_vehicle_date` | 2026-05-22 |
| B-M1 | New table: `repair_requests` | 2026-05-23 |
| B-M5 | Alter `vehicles`: add `inactive_reason`, `inactive_since` | 2026-05-23 |
| B-M7 | Alter `daily_inventory_checks`: add `reviewed_by`, `reviewed_at`, `corrective_action` | 2026-05-23 |
| B-M9 | Alter `daily_inventory_checks`: add `deleted_at`, `deleted_by`, `deletion_reason`, `force_deleted` | 2026-05-23 |
| B-M11 | Alter `stations`: add `primary_color` (migration 0011) | 2026-05-30 |
| NEW-M1 | Alter `vehicles`: add `vehicle_color` (migration 0011) | 2026-05-30 |
| NEW-M2 | Alter `stations`: add `call_sign` (migration 0012) | 2026-05-30 |
| — | Migration 0013: `vehicle_id` nullable on `daily_inventory_checks`; adds `location_id` FK | 2026-05-30 |
| — | Migration 0009: `items` table — add `ai_tags`, `alternate_names`, `reference_image_url`, `barcode` | 2026-05-30 |
| — | Migration 0010: `par_levels` table — add `active` flag with index | 2026-05-30 |
| RX-M1 | Migration 0015: `priority_check` + `priority_question` on `par_levels`; `requires_full_check` on `compartments` | 2026-06-05 |
| DMG-B1 | Migration 0016: `is_damaged` on `par_levels` | 2026-06-05 |

---

## Backend — Phase 6 Endpoints
| # | Item | Completed |
|---|------|-----------|
| B-E0 | `GET /api/v1/stations/{id}/locations` — list checkable non-vehicle locations | 2026-05-22 |
| B-E1 | `PATCH /vehicles/{id}` — mark vehicle active/inactive | 2026-05-23 |
| B-E2 | `PATCH /checks/daily/{id}/acknowledge` — supervisor corrective action | 2026-05-23 |
| B-E4 | `POST /vehicles/{id}/repair-requests` — file repair request | 2026-05-23 |
| B-E16 | `PATCH /vehicles/{id}/repair-requests/{rid}` — update repair request status | 2026-05-23 |
| B-E17 | `GET /vehicles/{id}/repair-requests` — list repair requests for vehicle | 2026-05-23 |
| B-E3 | `GET /checks/daily/station/{id}?from=&to=` — date-range compliance query | 2026-05-29 |
| B-E5 | `POST /inventory/transfer` — move stock between locations | 2026-05-30 |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` — stock vs par per item | 2026-05-30 |
| B-E8 | `PUT /inventory/lots/{id}` — correct expiry date on lot (6 new tests; 237 passing) | 2026-06-06 |
| DMG-B2 | `PATCH /inventory/items/{id}/status` — damaged flag on par level (DMG-B1 endpoint) | 2026-06-05 |

---

## Backend — Check History Endpoints
| # | Item | Completed |
|---|------|-----------|
| CH-B1 | `GET /checks/daily/my-history` — current user's submitted checks | 2026-05-23 |
| CH-B2 | `GET /checks/daily/{id}/detail` — full check detail with RBAC scoping | 2026-05-23 |
| CH-B3 | `DELETE /checks/daily/{id}` — soft-delete with mandatory reason | 2026-05-23 |

---

## Frontend — Phase 5E / Vehicle & Equipment Status
| # | Item | Completed |
|---|------|-----------|
| F-5E1 | Repair request form — severity selector, description, URGENT escalation | 2026-05-23 |
| F-5E2 | Mark vehicle inactive toggle (Supervisor+) | 2026-05-23 |
| F-5E3 | Repair request status tracking display | 2026-05-23 |
| VE-F1 | Rename "Vehicle Status" → "Vehicle & Equipment Status" throughout app | 2026-05-23 |
| VE-F5 | Open issue badge on V&E Status home card | 2026-05-29 |
| VE-F5b | Vehicle card badge on mount — repair list fetched eagerly | 2026-05-29 |

---

## Frontend — Check History
| # | Item | Completed |
|---|------|-----------|
| CH-F1 | "My Checks" screen — user's submitted checks grouped by date | 2026-05-23 |
| CH-F2 | Check detail view (read-only for Responders) | 2026-05-23 |
| CH-F3 | Show supervisor acknowledgement on check detail | 2026-05-23 |
| CH-F4 | Supervisor check history list — filterable by status | 2026-05-23 |
| CH-F5 | Soft-delete check (Supervisor+) — mandatory reason, 90-day warning | 2026-05-23 |
| CH-F7 | Deleted records screen — Supervisor+ tab in Check History | 2026-06-05 |
| CH-F8 | Force hard-delete confirmation modal — Administrator only | 2026-06-06 (BUG fixed: canAccess('admin') → 'administrator') |

---

## Frontend — Check Wizard UX
| # | Item | Completed |
|---|------|-----------|
| F-UX1 | Station picker on home screen | 2026-05-16 |
| F-UX11 | Discard check button with confirmation modal | 2026-05-21 |
| F-UX12 | Three-tier item row color (green/yellow/red) | 2026-05-21 |
| F-UX13 | Surface short/fail on Step 2 compartment badges | 2026-05-21 |
| F-UX14 | Save compartment force-confirms all touched items | 2026-05-21 |
| F-UX15 | Jump bag / portable cards on Step 1 | 2026-05-21 |
| F-UX16 | One jump bag per ambulance with alpha-sort grouping | 2026-05-21 |
| F-UX17 | Step 4 Reconcile — interactive shopping list with share/copy | 2026-05-22 |
| F-UX18 | Wizard renumbered to 5 steps | 2026-05-22 |
| F-UX19 | Step 2 button label: "Reconcile →" vs "Review and Submit →" | 2026-05-22 |
| F-UX20 | Step 5 back button routes to Reconcile or Compartments intelligently | 2026-05-22 |
| F-UX21 | Minimal test unit (Unit TEST QRV) — all check types in < 5 min | 2026-05-22 |
| F-UX22–F-UX26 | Bug fixes: routing, check date, status, repair pre-fill, compartment label | 2026-05-22 |
| F-UX27 | DATE_RECORD "Today" button | 2026-05-22 |
| F-UX28 | Multiple checks per day — draft key uses started_at | 2026-05-22 |
| F-UX29 | Backend: allow unlimited checks per day | 2026-05-22 |
| F-UX30 | DraftBanner uses selection_label | 2026-05-22 |
| F-UX31 | Reconcile "Add N" top-off button | 2026-05-22 |
| F-UX33 | FAIL check → repair request prompt on submitted screen | 2026-05-23 |
| F-UX35 | Draft banner station fallback — localStorage cache | 2026-05-25 |
| F-UX7 | Last Check Banner on home screen | 2026-05-30 |
| F-UX2 | Left/right chevron navigation between compartments | 2026-06-06 (confirmed built) |
| F-UX3 | "Jump to unvalidated" sticky button (Step2Compartments.jsx + wizard.css) | 2026-06-06 |

---

## Frontend — Phase 5H: Infrastructure
| # | Item | Completed |
|---|------|-----------|
| F-5H1 | Terraform module: Azure Static Web Apps | 2026-05-24 |
| F-5H2 | GitHub Actions 4-job pipeline | 2026-05-24 |
| F-5H3 | SWA URL added to CORS allowed origins | 2026-05-24 |
| F-5H4 | SWA URL registered as SPA redirect URI in Azure AD | 2026-05-24 |

---

## Infrastructure / Security
| # | Item | Completed |
|---|------|-----------|
| I-7 | Confirm Azure deployment healthy — App Service B1, VNet, CI/CD green | 2026-05-24 |
| SEC-1 | `pip-audit` step added to CI before pytest | 2026-05-26 |
| SEC-2 | Disable OpenAPI `/docs`, `/redoc`, `/openapi.json` in production | 2026-05-26 |
| SEC-3 | Security headers middleware | 2026-05-26 |
| SEC-4 | Startup assertion: fail loud if `SECRET_KEY == "change-me-in-production"` | 2026-05-26 |
| SEC-5a–d | Structured `logger` calls in inventory/stations/vehicles/items routers | 2026-05-26 |
| SEC-6 | Document `secondary_signer` free-text limitation in checks.py | 2026-05-26 |
| SEC-H1 | HTTPSRedirectMiddleware — added then removed (Azure SSL-offloads to HTTP; platform setting enforces HTTPS) | 2026-06-05 |
| SEC-H2 | MSAL `cacheLocation: "sessionStorage"` — confirmed already set, no change | 2026-06-05 |
| SEC-H3 | `/health` now returns `{"status": "ok"}` only — env field removed | 2026-06-05 |
| SEC-PRE1 | `staticwebapp.config.json` (CSP, HSTS, X-Frame-Options, SWA routing) | 2026-06-05 |
| SEC-PRE2 | `npm audit --audit-level=high` added to CI frontend job | 2026-06-05 |
| SEC-PRE3 | `seed.py` production guard + `startup.sh` APP_ENV check | 2026-06-05 |
| SEC-PRE4 | ESLint (eslint@8, react-hooks plugin) + lint script + CI step (0 warnings) | 2026-06-05 |

---

## Workflow Acceleration — Session H/I

| # | Item | Completed |
|---|------|-----------|
| RX-F1 | Home screen — "Check the Truck" hero button + "Log Items Used" secondary | 2026-06-05 |
| RX-F2 | Auto-confirm supply items at par | 2026-06-05 |
| RX-F7 | "Save compartment" → "Done — [Name]" / "Next — [Name]" | 2026-06-05 |
| RX-F8 | No Change / Modify compartment flow — stock preview, No Change attests at par, Undo | 2026-06-05 |
| RX-F8a | No Change — writes all line items with quantity_found = min_quantity | 2026-06-05 |
| RX-F9 | Priority items section — pinned above compartment list in Step 2 | 2026-06-05 |
| RX-F9a | Priority item custom question text from par_level.priority_question | 2026-06-05 |
| RX-F10 | Responder-facing language + error message replacement | 2026-06-05 |
| RX-F11 | First-run tutorial — Tutorial.jsx, 3 screens, ems_tutorial_complete flag | 2026-06-05 |
| RX-F4 | Simplify Step 5 for clean PASS | 2026-06-05 |
| RX-F3 | Collapse Step 1 for single-station users | 2026-06-05 |
| RX-F5 | Restock list persists on SubmittedScreen | 2026-06-05 |

---

## Supervisor Dashboard — Session I

| # | Item | Completed |
|---|------|-----------|
| SUP-F1 | Open repair count on compliance dashboard header | 2026-06-05 |
| SUP-F3 | Expiring items alert on compliance dashboard | 2026-06-05 |

---

## Damaged Item Status — Session I/J

| # | Item | Completed |
|---|------|-----------|
| DMG-F1 | Mark item damaged — inline in check wizard (+ Mark Damaged / Clear Damaged on ItemRow) | 2026-06-06 |
| DMG-F2 | Damaged item badge in compartment preview; No Change blocked | 2026-06-05 |

---

## Seed Data Gaps — Session H/I

| # | Item | Completed |
|---|------|-----------|
| SEED-GAP1 | "LUCAS Device Ready Check" FUNCTIONAL item added to seed.py PC 8 | 2026-06-05 |
| SEED-GAP2 | `requires_full_check=True` for Truck Operations compartment | 2026-06-05 |
| SEED-GAP3 | AED Battery marked priority_check=True, priority_question="AED shows READY?" | 2026-06-05 |

---

## Session A — Security Gate (2026-05-26)
153 tests pass. pip-audit 0 CVEs.

Dependency upgrades: fastapi 0.111→0.136.1, starlette 0.37.2→1.1.0, pydantic 2.7.1→2.13.4, azure-identity 1.16→1.19, PyJWT 2.8→2.12, cryptography 42→46, pytest 8.2→9.0.3. Resolved 12+ CVEs.

Dead code removed: `routers/_patch_cs_message.py`, `routers/_patch_get_check.py`, `tests/test_rbac_block.py`. Added `ems_readykit_dev.db` and `deploy.zip` to `.gitignore`.

---

## Session B — Refactor Sprint (2026-05-27)
153 tests pass, 0 deprecation warnings.

| # | Item | Completed |
|---|------|-----------|
| REF-1 | `write_audit_event()` extracted to `core/audit.py` | 2026-05-27 |
| REF-2 | `get_vehicle_or_404()` moved to `deps.py` | 2026-05-27 |
| REF-3 | `ALL_ROLES`, `SUPERVISOR_PLUS`, `ADMIN_ONLY` moved to `deps.py` | 2026-05-27 |
| REF-4 / ACC-B10 | `require_station_membership()` moved to `deps.py` | 2026-05-27 |
| REF-5 | `wizard.css`, `wizard-station.css`, `submitted-screen-patch.css` merged into `src/styles/wizard.css` | 2026-05-27 |
| REF-6 | All `logger.warning()` calls in `auth.py` include `extra={}` | 2026-05-27 |
| REF-7 | `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT` | 2026-05-27 |

Bug fixes: MSAL popup→redirect flow, `msalInstance.initialize()` awaited, `handleRedirectPromise()` removed from `useAuth.jsx`.

---

## Session C — Access Control Enforcement (2026-05-29)
179 tests pass. OWASP A01 enforcement complete.

ACC-B7: Station membership enforced on all `/checks` endpoints.
ACC-B8: Station membership enforced on all `/vehicles` and `/inventory` endpoints.
ACC-B9: Supervisor dashboard endpoints enforced via ACC-B7/B8.
Human-readable error messages on 401/403 throughout.
26 new tests in `test_station_membership.py`.

---

## Session D — Features (2026-05-29)
200+ tests pass.

| # | Item | Completed |
|---|------|-----------|
| B-E3 | `GET /checks/daily/station/{id}?from=&to=` | 2026-05-29 |
| VE-F5/F5b | Open issue badge on V&E Status | 2026-05-29 |
| CH-UX1-F1–F5 | Unified Check Resolution (IFixedThisPanel, ResolutionTag) — later removed | 2026-05-29 |
| B-R1/B-R2/F-R1 | Repair request bug fixes + InProgressModal | 2026-05-29 |
| D-R1 | Documentation audit — README + project_index.md rewritten; 14 stale files archived | 2026-05-29 |

---

## Session E — Admin Redesign, Item Catalog & Vehicle Management (2026-05-30)
200+ tests pass. 0 CVEs.

ADMIN-UX1-F1–F8: Admin redesigned — station header + 3 nav cards (Members, Item Catalog, Vehicles).
ADMIN-B1–B10, B17–B18: Full item catalog endpoints including typeahead search + CSV bulk import.
ADMIN-F1–F5, F11: Item catalog frontend including par level assignment UI.
ADMIN-UX1-B1: `PATCH /inventory/compartments/{id}`.
Multiple bug fixes: Check wizard 403, sort order input, station selection, OOS form, repair list for Responders, Check History read-only enforcement.

---

## Session F — Station Setup, Compliance Calendar & Par Levels (2026-05-30 → 2026-06-01)
217 tests pass. 0 CVEs. All Block 5 UAT test cases pass.

Block 1 — Color System: `primary_color` on stations, `vehicle_color` on vehicles, `ColorPickerWidget`.
Block 2 — Add Station: `call_sign` on stations, `POST /admin/stations`, "+ Add Station" form.
Block 3 — Compliance Calendar: `ComplianceCalendar.jsx`, 90-day rolling, per-vehicle color rows.
Block 4 — Last Check Banner: `LastCheckBanner.jsx` on home screen.
Block 5 — Par Level Assignment UI: vehicle-centric view, `CompartmentParLevels.jsx`, add/edit/remove inline.
Block 6 — UAT Document: `docs/uat_test_cases.md`.

---

## Session G — Supply Room & Restocking (2026-06-03)
All tests passing.

| # | Item | Completed |
|---|------|-----------|
| SUPPLY-M1 | `STATION_SUPPLY_ROOM` auto-created per station | 2026-06-03 |
| SUPPLY-B1 | `POST /inventory/transfer` | 2026-06-03 |
| SUPPLY-B2 | `GET /inventory/locations/{id}/stock-summary` | 2026-06-03 |
| SUPPLY-B3 | `GET /stations/{id}/supply-room` | 2026-06-03 |
| SUPPLY-F1 | Supply room stock view | 2026-06-03 |
| SUPPLY-F2 | Restock vehicle flow | 2026-06-03 |
| SUPPLY-F3 | Receive stock into supply room | 2026-06-03 |
| SUPPLY-F4 | Transfer history | 2026-06-03 |

---

## Session H — Published to Production (2026-06-05)
231 backend tests passing. 63/63 frontend tests passing. 0 npm vulnerabilities.

PRE-H: Code cleanup, CSS theme consolidation (TECH-THEME1–4), security hardening (SEC-PRE1–4), dead file deletion (TECH-CSS1a/b, TECH-CODE1a–f).
RX-F1/F2/F7/F8/F8a/F9/F9a: Check wizard interaction redesign.
SEC-H1/H2/H3: HTTPS strategy confirmed, MSAL verified, /health locked down.
SEED-GAP1/GAP2/GAP3: Unit 712 priority/functional items configured in seed.py.
FIX: npm audit — upgraded vite 5→7, vitest 1→4, @vitejs/plugin-react 4→5. Resolved GHSA-5xrq-8626-4rwp (CVSS 9.8).
FIX: Migration 0014 boolean 0/1 → True/False for PostgreSQL.
FIX: Station bleed — my-history now scoped by station_id.
FIX: Vehicle on-hand computed from last check quantity_found, not stock lots.
FIX: No Change 422 + FAIL — compartment_id stored on draft; MEASUREMENT excluded from No Change line items.

---

## Session I — Features (2026-06-05)
231 backend tests passing.

RX-F3/F4/F5/F10/F11: Step 1 collapse, Step 5 simplify, restock list persistence, language pass, first-run tutorial.
SUP-F1: Open repair count on compliance dashboard.
SUP-F3: Expiring items alert on compliance dashboard.
DMG-B1/B2/F2: Migration 0016, damaged flag endpoint, compartment badge, No Change blocked.
CH-F7/F8 backend + frontend logic: Deleted records screen (CSS deferred to Session J).

---

## Session J — UX Polish + Bug Fixes (2026-06-06)
237 backend tests passing.

| # | Item | Completed |
|---|------|-----------|
| CH-F7/F8 CSS | Deleted records list styling in check-history.css | 2026-06-06 |
| F-UX2 | Left/right chevron nav — confirmed already built | 2026-06-06 |
| F-UX3 | Sticky jump-to-next-unvalidated button | 2026-06-06 |
| B-E8 | `PUT /inventory/lots/{id}` — correct expiry date (6 new tests) | 2026-06-06 |
| Cleanup | `_damagedOverrides` comment artifact removed from Step3Items.jsx | 2026-06-06 |
| BUG | `canAccess(user, 'admin')` silently returned false — fixed to 'administrator'; added 'admin' alias to roleGuard.js | 2026-06-06 |
| DMG-F1 | + Mark Damaged / Clear Damaged on ItemRow actions bar (all roles, any item) | 2026-06-06 |
| BUG | `patch_item_status` used wrong `write_audit_event` kwargs (performed_by/detail → actor/metadata) — 500 on mark/clear damaged resolved | 2026-06-06 |
| DOCS | Session handoff files retired; backlog.md is single source of truth; 3 architectural decisions added to CLAUDE.md | 2026-06-06 |
| DOCS | Backlog cleaned — all ✅ Done items moved to backlog_completed.md; 164 → 106 open items | 2026-06-06 |

---

## Session K — Supply Room Redesign (2026-06-06)
250 backend tests passing.

| # | Item | Completed |
|---|------|-----------|
| SR-M1 | Migration 0017: `station_supply` BOOL NOT NULL DEFAULT TRUE on `items` table (Alembic batch mode) | 2026-06-06 |
| SR-SEED1 | Set `station_supply=False` for 29 items (AED, LUCAS, drugs, date checks) in seed.py | 2026-06-06 |
| SR-B1 | `GET /inventory/supply-catalog?station_id=` — supply catalog with on-hand counts; Responder+; 10 tests | 2026-06-06 |
| SR-B2 | `PATCH /inventory/supply-catalog/items/{id}/count` — FIFO lot adjustment; audit event; best-effort; 10 tests | 2026-06-06 |
| SR-B3 | `GET /stations/{id}/supply-alerts` — items below par min; Supervisor+; 4 tests | 2026-06-06 |
| SR-B4 | `_auto_decrement_supply_room` wired into `create_daily_check`; best-effort; never blocks submit; 2 tests | 2026-06-06 |
| SR-B5 | `POST /inventory/transfer` removed from inventory.py; `TransferRequest` schema removed | 2026-06-06 |
| SR-F1 | "Station Supplies" home screen card — Responder+ visible (removed supervisor gate); renamed from "Supply Room" | 2026-06-06 |
| SR-F2 | Supply room landing redesigned: 2 large nav cards (View Supplies, Count Supplies) + secondary text links | 2026-06-06 |
| SR-F3 | `SupplyCatalogView.jsx` — SR-B1 data, on-hand/par display, inline count correction (Supervisor+ only) | 2026-06-06 |
| SR-F4 | `Step1Vehicle.jsx` — auto-advance for supply room checks (`draft._supplyRoom=true`), skips vehicle selection | 2026-06-06 |
| SR-F5 | `SupplyLowStockPanel.jsx` on supervisor dashboard — calls SR-B3; red if out, amber if low; hidden if nothing low | 2026-06-06 |
| SR-F6 | `RestockVehiclePanel` removed from supply room routing; vehicle CSS classes removed from supply-room.css | 2026-06-06 |
| SR-F7 | Inline lot expiry editor in `SupplyCatalogView` — uses `PUT /inventory/lots/{id}` (B-E8); Supervisor+ only | 2026-06-06 |
