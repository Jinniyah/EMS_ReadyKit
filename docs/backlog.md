# EMS ReadyKit — Active Backlog
# v1.56 | Updated: 2026-06-04
# Completed items -> backlog_completed.md
# Priority: Critical / High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ SESSION COMPLETE 2026-05-24 — Phase 5H Infrastructure
# ✅ SESSION COMPLETE 2026-05-25 — Draft flow, UTC fix, Azure AD, station membership endpoints
# ✅ SESSION COMPLETE 2026-05-26 — Session A: Security Gate (OWASP A02/A04/A05/A06/A09, 0 CVEs)
# ✅ SESSION COMPLETE 2026-05-27 — Session B: Refactor Sprint (REF-1 through REF-7)
# ✅ SESSION COMPLETE 2026-05-29 — Session C: Access Control Enforcement (OWASP A01)
# ✅ SESSION COMPLETE 2026-05-29 — Session D: Features
# ✅ SESSION COMPLETE 2026-05-30 — Session E: Admin updates and bug fixes
# ✅ SESSION COMPLETE 2026-05-30 — Session F: Station Setup + Compliance Calendar + Par Levels
# ✅ SESSION COMPLETE 2026-06-01 — Session F UAT + Vehicle-Centric Par Level View
# ✅ SESSION COMPLETE 2026-06-02 — UAT Bug Fixes + Security Patch
# ✅ SESSION COMPLETE 2026-06-03 — Session G: Supply Room & Restocking (all tests passing)
# 🔄 SESSION H IN PROGRESS 2026-06-05 — Workflow Acceleration + Check Wizard Redesign
#    ✅ SEC-H1: HTTPSRedirectMiddleware added to main.py (production-only, outermost)
#    ✅ SEC-H2: MSAL cacheLocation already sessionStorage — no change needed
#    ✅ SEC-H3: Removed env field from /health response
# ✅ PRE-SESSION H COMPLETE 2026-06-05 — Code cleanup + Theme consolidation + Security
#    ✅ SEC-PRE1: staticwebapp.config.json (CSP, HSTS, X-Frame-Options, SWA routing)
#    ✅ SEC-PRE2: npm audit --audit-level=high added to CI frontend job
#    ✅ SEC-PRE3: seed.py production guard + startup.sh APP_ENV check
#    ✅ SEC-PRE4: ESLint (eslint@8, react-hooks plugin) + lint script + CI step (0 warnings)
#    ✅ TECH-THEME1: index.css extended (--vehicle-primary, --color-damaged/priority/no-change, --font-size-xs, utility classes)
#    ✅ TECH-THEME2: supervisor.css fully converted to tokens
#    ✅ TECH-THEME3: supply-room.css fixed (--color-background → --color-surface-raised, font-size-xs)
#    ✅ TECH-THEME4: CSS/theming rules added to CLAUDE.md (5 mandatory rules)
#    ✅ TECH-CSS1a: Deleted 5 tombstone CSS files + admin-station-edit.css + admin-wrap-fix.css
#    ✅ TECH-CSS1b: admin-wrap-fix.css deleted (content already in admin.css)
#    ✅ TECH-CODE1a: Deleted Step4Review.jsx (dead — replaced by Step5Submit.jsx)
#    ✅ TECH-CODE1b: Deleted vehicles/_patch_note.txt
#    ✅ TECH-CODE1c: useApi.js — setData(null) added at start of execute()
#    ✅ TECH-CODE1d: Cross-ref comments: _compute_line_item_status ↔ deriveDraftItemStatus
#    ✅ TECH-CODE1e: adminApi.js — renamed updateVehicle→patchVehicleStatus; added JSDoc to all 3 vehicle fns
#    ✅ TECH-CODE1f: getStations/getMyStations deduplicated via shared/api/stationsApi.js

---

## ──────────────────────────────────────────────────────────────────────────────
## LAUNCH PHILOSOPHY (established 2026-06-04)
## ──────────────────────────────────────────────────────────────────────────────
##
## This app ships ONCE to a real EMS team. There is no beta, no soft launch,
## no "we'll fix it after they try it." The first time Earl sees it, it must:
##   1. Work without explanation
##   2. Match how the team actually operates (real truck names, real item names)
##   3. Feel faster than paper for a clean check
##   4. Handle the hard cases (damaged AED, short O2, post-call restock) cleanly
##
## Launch gate criteria — ALL must be met before any user sees the app:
##   ✓ Check wizard redesign complete (No Change / Modify / Priority Items)
##   ✓ After-call reset flow complete
##   ✓ Damaged item marking complete
##   ✓ First-run tutorial complete (3-screen minimum)
##   ✓ All responder-facing language plain English (no jargon, no technical errors)
##   ✓ Open repair count visible on compliance dashboard
##   ✓ Vehicle + location retirement actions complete
##   ✓ Priority items configured in admin for Unit 712 (AED, LUCAS, O2, Truck Ops)
##   ✓ UAT executed against live Azure deployment with real Unit 712 inventory
##   ✓ Physical stock count entered for Unit 712 (not seed quantities — actual counts)
##   ✓ All tests passing (231+ tests green)
##   ✓ Code cleanup complete (dead files deleted, CSS consolidated)
##
## ──────────────────────────────────────────────────────────────────────────────
## UPCOMING SESSIONS
## ──────────────────────────────────────────────────────────────────────────────
##
## PRE-SESSION H — Code cleanup + Theme consolidation (90 min, do first, no exceptions)
##   ✅ TECH-THEME1  Extend index.css token system
##   ✅ TECH-THEME2  Fix supervisor.css — replace raw values with tokens
##   ✅ TECH-THEME3  Fix supply-room.css — replace raw values with tokens
##   ✅ TECH-THEME4  Add theme rules to CLAUDE.md
##   ✅ SEC-PRE1     Create staticwebapp.config.json (CSP, HSTS, routing)
##   ✅ SEC-PRE2     Add npm audit to CI pipeline
##   ✅ SEC-PRE3     Add seed.py production guard
##   ✅ SEC-PRE4     Add ESLint to CI pipeline
##   ✅ TECH-CSS1a   Delete 5 empty tombstone CSS files
##   ✅ TECH-CSS1b   Merge admin-wrap-fix.css into admin.css
##   ✅ TECH-CSS1c   Enforce CSS placement rule in CLAUDE.md
##   ✅ TECH-CODE1a  Delete Step4Review.jsx (dead — replaced by Step5Submit.jsx)
##   ✅ TECH-CODE1b  Delete vehicles/_patch_note.txt
##   ✅ TECH-CODE1c  Fix useApi.js stale-data reset (data=null at start of execute)
##   ✅ TECH-CODE1d  Cross-reference comments: _compute_line_item_status <-> deriveDraftItemStatus
##   ✅ TECH-CODE1e  Consolidate 3 vehicle-update functions in adminApi.js
##   ✅ TECH-CODE1f  Deduplicate getStations / getMyStations between checkApi + adminApi
##
## Session H — Workflow Acceleration + Check Wizard Redesign (5-6 hrs)
##   RX-F1        Home screen — two dominant actions                  ~30 min
##   RX-F2        Auto-confirm supply items at par                    ~45 min
##   RX-F3        Collapse Step 1 (label fix: "Change date or add crew member")  ~30 min
##   RX-F4        Simplify Step 5 for clean PASS                      ~30 min
##   RX-F5        Restock list link on SubmittedScreen                ~20 min
##   RX-F7        "Save compartment" -> "Done — [Name]"               ~15 min
##   RX-F8        No Change / Modify compartment flow                 ~90 min
##   RX-F9        Priority items pinned above compartments            ~75 min
##   RX-M1        Migration 0015: priority_check on par_levels        ~20 min
##   RX-F10       Language pass: responder strings + error messages   ~60 min
##   RX-F11       First-run tutorial — 3 screens on first login       ~60 min
##   DMG-F1       Mark item damaged — inline in check wizard          ~45 min
##   DMG-B1       PATCH /inventory/items/{id}/status                  ~30 min
##   SUP-F1       Open repair count on compliance dashboard           ~30 min
##   SUP-F3       Expiring items alert on dashboard                    ~45 min
##   SEC-H1       HTTPSRedirectMiddleware (moved from Session J)       ~15 min
##   SEC-H2       MSAL cacheLocation: sessionStorage                   ~10 min
##   SEC-H3       Remove env field from /health response               ~10 min
##   F-UX2        Left/right chevron nav between compartments         ~30 min
##   F-UX3        Jump to unvalidated sticky button                   ~30 min
##   B-E8         PUT /inventory/lots/{id} — correct expiry           ~30 min
##   CH-F7/F8     Deleted records screen + force hard-delete          ~45 min
##
## Session I — After-Call Reset + Retirement + Settings + Data Export (4-5 hrs)
##   RX-F6        After-Call Reset — recents + search                 ~90 min
##   RX-B1        POST /checks/usage — lightweight usage record       ~45 min
##   RET-M1-M3    Migrations: retired_at/by/reason                    ~30 min
##   RET-B1-B4    Retire vehicle/location/station endpoints           ~45 min
##   RET-F1-F5    Retire actions in UI                                ~60 min
##   SUP-F2       Repair count drill-down to V&E Status               ~20 min
##   F-5G3        Data export — CSV for history/audit/repairs         ~45 min
##   B-E18        GET /audit?from=&to= — date-range audit             ~30 min
##   S-F3         Allow check modification toggle (Admin)             ~20 min
##   S-F6         Station management in Settings                      ~30 min
##   AI-B1        PATCH /admin/items/{id}/ai-fields                   ~30 min
##   AI-F1        AI fields editor in Item admin screen               ~45 min
##
## Session J — UAT Dress Rehearsal + Final Polish (3-4 hrs)
##   LAUNCH-OPS1  Supervisor configures priority items in production  ~60 min
##   LAUNCH-OPS2  Physical stock count entered for Unit 712           ~45 min
##   LAUNCH-OPS3  Unit 712 Jump Bag stock count entered               ~20 min
##   UAT-2-6      Execute all UAT test cases (live Azure, real data)  ~90 min
##   F-5C1        First-run tutorial review + polish                  ~30 min
##   F-5C2        Contextual ? help — bottom sheet per step           ~30 min
##   I-3          HTTPSRedirectMiddleware                              ~10 min
##   LAUNCH-OPS4  Add all EMS team members in admin                   ~20 min
##   LAUNCH-OPS5  Chief walkthrough: full check on Unit 712           ~30 min
##   LAUNCH-OPS6  Volunteer walkthrough: Earl or equivalent           ~30 min
##
## Post-launch (add when the team asks for it):
##   AI-F2/F3     Barcode scan in after-call log + supply receive
##   F-5G3        Data export CSV (when first compliance report is due)
##   F-5C2        Contextual per-step help (based on what questions team actually asks)
##   I-1          Azure Firewall (before scaling to second service)
##
## ──────────────────────────────────────────────────────────────────────────────

---

## 0. Security — Pre-User Gate

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-3 | `HTTPSRedirectMiddleware` in `main.py` | High | 📋 | Moved from Session J to Session H. Azure App Service provides platform-level redirect but application-layer enforcement is defence-in-depth. Three lines in main.py. |

---

## 0A. Security — Pre-Session H (OPSECDEV findings 2026-06-04)
##
## Full OPSECDEV review conducted 2026-06-04. Authentication (A), authorization (A),
## audit trail (A), secrets management (A), dependency security (A) all solid.
## The following gaps are in the deployment pipeline and configuration layer only.
## Fix all four SEC-PRE items before writing any Session H code.

### Pre-H security items
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-PRE1 | Create `staticwebapp.config.json` | Critical | 📋 | Missing from repo entirely. Referenced in main.py comments but never created. Must include: (1) Content Security Policy header — `"Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://login.microsoftonline.com https://app-ems-readykit-dev.azurewebsites.net; frame-ancestors 'none'"`. (2) `"X-Frame-Options": "DENY"`. (3) `"Strict-Transport-Security": "max-age=31536000; includeSubDomains"`. (4) SWA routing: all routes fallback to `/index.html` so React Router handles navigation without Azure 404s. Place at `frontend/staticwebapp.config.json` (SWA picks it up from the app root). |
| SEC-PRE2 | Add `npm audit` to CI frontend job | High | 📋 | Add `npm audit --audit-level=high` after `npm ci` and before `npm run build` in the build-frontend job of deploy.yml. Fails build on high/critical severity only — moderate is reported but non-blocking. Mirrors the existing pip-audit pattern on the backend. One line in the workflow. |
| SEC-PRE3 | Seed.py production guard | High | 📋 | Add at the very top of seed.py, after imports: `if os.environ.get("APP_ENV", "").lower() == "production": print("Seed skipped in production."); sys.exit(0)`. Also add to startup.sh: only call `python seed.py` when `APP_ENV != production`. Both guards must exist independently (defence in depth). Resolves the risk of test stations/vehicles/users appearing in the live environment if SEED_TEST_DATA env var is misconfigured at launch. |
| SEC-PRE4 | Add ESLint to CI frontend job | Medium | 📋 | Add `npm run lint` as a step in build-frontend job, after `npm ci` and before `npm run build`. If `lint` script isn't in package.json, add it: `"lint": "eslint src --max-warnings 0"`. Catches undefined variables, React hook violations, and accessibility issues before they deploy. Backend equivalent: ruff already runs in CI. |

### Session H security items
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-H1 | `HTTPSRedirectMiddleware` in `main.py` | High | ✅ Done | Added production-only, outermost (added last so outermost). main.py:117-122. |
| SEC-H2 | MSAL `cacheLocation: "sessionStorage"` | High | ✅ Done | Already set correctly in authConfig.js — no change needed. |
| SEC-H3 | Remove `env` field from `/health` response | Medium | ✅ Done | /health now returns `{"status": "ok"}` only. main.py:136. |

### Post-launch security (operational)
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEC-OPS1 | Scheduled monthly dependency audit workflow | Low | 📋 | Add `.github/workflows/dependency-audit.yml` with `on: schedule: - cron: "0 9 1 * *"` (first of each month). Runs pip-audit and npm audit, opens a GitHub issue if findings above moderate severity. Keeps audit cadence from depending on manual intervention. |

---

## 1. Workflow Acceleration — Responder UX (Session H/I)
##
## Context: Dual sanity-check reviews 2026-06-04.
##   Persona 1: Responder — hour 11 of a 12-hour shift, just cleared a call,
##              truck needs to go back in service. App must be faster than paper.
##   Persona 2: Rural EMS chief — 68yo ex-Detroit PD, 10 volunteers including
##              farmers and retirees, 2 BLS trucks, 5 calls/week, not tech-savvy.
##              "If Earl can do a truck check without calling me for help, you got it right."
## Design principle: match the speed of a paper checkmark on a clean truck.
## Never add time on top of the physical work.
## One launch. One chance. Get it right first.

### Check wizard — interaction redesign
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F1 | Home screen — two dominant actions | Critical | 📋 | "Check the Truck" (full-width, station-colored, top) + "Log Items Used" (prominent secondary). All other module cards visually subordinate. Supervisor-only cards must not compete with the primary responder action. Single-station users never see a station picker. |
| RX-F2 | Auto-confirm supply items at par | Critical | 📋 | When quantity_found === quantity_needed after +/- tap, auto-confirm with green checkmark — no "Submit count" button. Only show explicit confirm when count does NOT match par. Eliminates ~170 redundant taps on a clean 200-item truck. ItemRow.jsx only. |
| RX-F3 | Collapse Step 1 for single-station users | High | 📋 | Single-station: vehicle picker + "Continue" only. Date and second crew collapse into a disclosure — label must say "Change date or add crew member" not "More options." Open by default only if date != today or draft has second crew pre-filled. |
| RX-F4 | Simplify Step 5 for clean PASS checks | High | 📋 | PASS: status badge + single "Submit — Unit 712" button. No compartment re-review, no repair toggle, no notes field, no confirmation modal. Repair toggle and notes appear only on NEEDS_RESTOCK or FAIL. |
| RX-F5 | Restock list persists on SubmittedScreen | High | 📋 | On NEEDS_RESTOCK: "View restock list" button on SubmittedScreen opens read-only reconcile summary. Currently the list disappears after submission. |
| RX-F7 | "Save compartment" language fix | Low | 📋 | Rename to "Done — [Compartment Name]". When next compartment exists: "Next — [Name]". Step3Items.jsx only. |

### No Change / Modify compartment flow
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F8 | No Change / Modify compartment interaction | Critical | 📋 | Redesign Step2Compartments. Each compartment card shows: (1) 3-item stock preview with "Stock: N / N" real quantities, (2) "No Change" button — attests all items at par, writes all line items with quantity_found = min_quantity (real numbers, not flags), records user + timestamp, (3) "Modify" button — expands inline, responder adjusts only what changed. No Change BLOCKED if: last check had FAIL or SHORT in this compartment, compartment contains a priority item, or compartment contains items flagged as damaged. Modify button relabels to "N item short" in amber when preview shows shortage. Undo available until check submitted. |
| RX-F8a | No Change — audit record specification | High | 📋 | On No Change: write all par_level line items as CheckLineItem rows with quantity_found = min_quantity (real number from par level), status = PASS, confirmed = true. Real quantities always recorded. No new fields required on CheckLineItem. Equivalent to fully-tapped for compliance purposes (Q-14 resolved). |

### Priority items — critical equipment pinned above compartments
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-M1 | Alter `par_levels`: add `priority_check` boolean | High | 📋 | Nullable boolean, default false. Supervisor marks per vehicle. No ceiling — supervisor judges per vehicle. Migration 0015. Admin UI toggle on par level assignment screen. Also add `priority_question` VARCHAR(150) nullable — supervisor sets the plain-English question shown to responder (e.g. "Is the ready light solid green?"). |
| RX-F9 | Priority items section — pinned above compartment list | Critical | 📋 | Items where priority_check = true pulled OUT of compartment and rendered in "Check these first" section at top of Step 2. Each item expands inline on tap — no navigation. Functional: custom question + Yes/No. FAIL auto-routes to repair request + damaged flag. Measurement: enter reading inline, threshold check immediate. Priority items cannot be skipped via No Change on parent compartment. See SEED-GAP1/GAP2/GAP3 for Unit 712 specific configuration decisions needed. |
| RX-F9a | Priority item custom question text | High | 📋 | Stored in par_level.priority_question (from RX-M1). Displayed verbatim to responder. Falls back to item name if unset. Max 150 chars. |
| RX-F9b | Priority item "last confirmed" display | Medium | 📋 | "Last confirmed ready: [date] · [N] days ago" below each priority item. Pulls from most recent PASS line item for that item on that vehicle. Amber if > threshold days (Q-15). |

### After-Call Reset
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F6 | After-Call Reset flow — recents + search | Critical | 📋 | Home screen second button: "Log Items Used." Auto-selects truck if only one. Shows: (1) last 8-10 items used on that vehicle ranked by frequency — falls back to common BLS consumables (gloves, gauze, tourniquets — drawn from Unit 712 actual inventory) on first use, (2) search bar for anything not in recents. Each item: +/- controls starting at 0. Restock delta updates live. "Done" commits. Target: ≤3 taps for 2-3 item case. No compartment walk required. |
| RX-B1 | `POST /checks/usage` — lightweight usage record | Critical | 📋 | Accepts: vehicle_id, station_id, timestamp, [{item_id, compartment_id, quantity_used}]. Decrements stock lots FIFO. Creates audit record. Does NOT create a DailyInventoryCheck. ADR needed (Q-11) before implementation. Returns updated restock delta. |

### Responder language + error message pass
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F10 | Responder-facing language + error message replacement | Critical | 📋 | Display strings only — no backend changes. Applies to ALL responder-facing screens including every error state. Jargon replacements: "Par level" -> "Stock: N / N", "Reconcile" -> "Restock list", "Functional check" -> custom question text, "Date record" -> "Expiration date", "Submit count" -> removed (auto-confirm), "NEEDS_RESTOCK" -> "Restock needed", "FAIL" -> "Problem found", "Measurement" -> "Reading", "Repair request" -> "Report a problem". "Out of service" KEPT — team uses this term. Error message replacements: "Could not load vehicles — is the backend running?" -> "Can't reach the server. Check your connection and try again.", "Could not load compartments" -> "Having trouble loading the truck layout. Try again.", all 401 errors -> "Your session expired. Sign out and sign back in.", all 403 errors -> "You don't have permission to do that. Ask your supervisor if something seems wrong." No technical HTTP status codes or server terminology visible to responders ever. |

### First-run tutorial
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| RX-F11 | First-run tutorial — 3 screens on first login | Critical | 📋 | Shown exactly once on first authenticated login, never again. localStorage flag `ems_tutorial_complete` prevents repeat. Three screens: (1) Home screen overlay — "Check the Truck starts your shift check. Log Items Used records what you used on a call." (2) Check flow overlay — "Tap No Change on compartments that look right. Tap Modify to update anything that changed. Check these first items need individual confirmation every time." (3) After-call overlay — "After a call, tap Log Items Used. Pick what you used. The restock list updates automatically." Each screen: large text, one illustration, "Got it" button. Skip button on screen 1 only. Must work on a cracked screen in poor lighting — minimum 60px tap targets throughout. |

---

## 2. Damaged Item Status (Session H)
##
## Rationale: EMS chief confirmed this will be commonly used. A responder who
## finds a damaged AED during a check needs a fast, in-context path to flag it.
## The repair request workflow handles supervisor notification and resolution.
## Inline — not a separate screen, not a navigation away from the check.

### Backend
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| DMG-B1 | `PATCH /inventory/items/{id}/status` — damaged flag | High | 📋 | Sets item as damaged/unavailable at a specific location. Responder+ role. Creates audit event. Does not delete or retire — marks unavailable at that location until resolved. Supervisor resolves via repair request workflow. |
| DMG-B2 | Include damaged flag in stock summary response | High | 📋 | Extend existing stock summary response: add `is_damaged: bool` per item. Damaged items shown with visual indicator in check wizard compartment preview and supply room. |

### Frontend
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| DMG-F1 | Mark item damaged — inline in check wizard | High | 📋 | In ItemRow (Step 3) and priority item cards (Step 2): after a FAIL or zero-count, "Mark as damaged" button appears. One tap: small inline form with reason (free text, max 100 chars) + confirm. Writes damaged flag, auto-creates repair request. Item immediately shows DAMAGED badge in subsequent checks until resolved. |
| DMG-F2 | Damaged item badge in compartment preview | High | 📋 | Compartment preview strip shows damaged items with a distinct red "⚠ Damaged" badge. No Change is blocked on compartments with damaged items — must open and verify. |
| DMG-F3 | Damaged item visibility in supply room | Medium | 📋 | StockSummaryView shows damaged items with badge. Damaged items excluded from restock transfer suggestions — don't restock a damaged item, repair it first. |

---

## 3. Supervisor Dashboard Enhancements (Session I)
##
## Rationale: The chief needs to see open repair requests without navigating.
## V&E Status is three taps from the home screen. A broken AED on Unit 712
## must be visible the moment he opens the dashboard — not buried.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SUP-F1 | Open repair count on compliance dashboard header | Critical | 📋 | Add to ComplianceSummary: "N open repair requests" count line. Data already available — reuse vehicle list that's already loaded. Tapping the count navigates to V&E Status. If zero open requests, line is hidden. No new API call required. |
| SUP-F2 | Repair count drill-down to V&E Status | High | 📋 | Tap on the repair count in SUP-F1 navigates directly to V&E Status screen filtered to open/in-progress requests, then back to compliance dashboard. Uses existing onNavigateToVehicles prop already wired through the module. |
| SUP-F3 | Expiring items alert on compliance dashboard | High | 📋 | Query stock_lots where expiration_date is within 30 days, grouped by vehicle/location. Display count in dashboard header alongside repair count: "N items expiring within 30 days." Tap opens a list grouped by vehicle showing item name, lot number, expiry date, and compartment. Amber at 30 days, red at 7 days. Backend: extend GET /stations/{id}/compliance or add GET /inventory/locations/{id}/expiring-soon?days=30. Frontend: new ExpiringItemsPanel component in supervisor module. No new migration required — expiration_date already on StockLot. This is the one commercial feature (present in every competitor) that EMS ReadyKit was missing at launch. A supervisor who doesn't know AED pads expire next month finds out during a check — or worse, during a call. |

---

## 4. AI Item Identification — Groundwork (Session I)
##
## Rationale: The dormant AI fields (ai_tags, alternate_names, reference_image_url,
## barcode) already exist on the Item model (migration 0009). Build the admin
## interface now so the chief can populate reference data. Barcode scanning drops
## in cleanly on top once the data is there.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| AI-B1 | `PATCH /admin/items/{id}/ai-fields` — activate AI identification fields | High | 📋 | Admin-only endpoint to set ai_tags, alternate_names, reference_image_url, barcode on an item. Fields exist in DB since migration 0009. This activates them for use. |
| AI-F1 | AI fields editor in Item admin screen | High | 📋 | Extend ItemForm.jsx: collapsible "AI Identification" section (collapsed by default, admin only). Fields: barcode (text), alternate names (comma-separated), reference image URL (text), AI tags (comma-separated). Save via AI-B1. |
| AI-F2 | Barcode search in After-Call Reset | Medium | 📋 | Post-launch. In RX-F6 after-call search: if device has camera, show barcode scan button. Scan -> look up item.barcode -> auto-populate item. Graceful text search fallback. |
| AI-F3 | Barcode search in supply room receive | Medium | 📋 | Post-launch. In ReceiveStockPanel: scan barcode to identify item being received rather than typing name. Same lookup as AI-F2. |

---

## 5. Seed Data Gaps — Unit 712 Specific (resolve before Session H)
##
## Context: The real Unit 712 BLS inventory is already seeded from the actual
## paper inventory sheets. Compartment names match what is stenciled on the
## physical compartment doors. Item names match the paper forms exactly.
## These gaps are configuration decisions the chief must make, not code bugs.

| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| SEED-GAP1 | LUCAS needs a FUNCTIONAL check item | High | 📋 | Currently seeded as SUPPLY (qty 1) + DATE_RECORD "LUCAS Date of Last Charge". Missing: FUNCTIONAL item "LUCAS Device Ready Check" with priority_question "Is the battery charged and the device ready to deploy?" Chief should add this item in admin Item Catalog and assign it to PC 8. Then mark it priority. Alternatively, add to seed.py alongside existing LUCAS items before Session H. Decision: add to seed.py so it's consistent across all environments. |
| SEED-GAP2 | Truck Operations compartment — No Change policy | High | 📋 | Truck Operations (sort_order=40) contains 12 FUNCTIONAL checks (Runs and Starts, Lights & Sirens, Medcom, etc.) and 3 SUPPLY items (cab gloves). These require physical verification — you cannot tap No Change without starting the truck and testing the systems. Two options: (A) Mark all Truck Operations FUNCTIONAL items as priority_check = true, forcing individual confirmation. (B) Add a compartment-level flag `requires_full_check` that blocks No Change entirely for that compartment. Option A is simpler and uses existing infrastructure. Decision needed from chief before RX-F8 is built. |
| SEED-GAP3 | AED priority item configuration | High | 📋 | AED is modeled as 4 items in PC 8: "AED Battery" (FUNCTIONAL), "AED Date of Last Charge" (DATE_RECORD), "AED Pads Adult" (DATE_RECORD), "AED Pads Pediatric" (DATE_RECORD). For priority items, "AED Battery" should be marked priority_check = true with priority_question "Is the ready light solid green with no error indicators showing?" The date and pad checks remain inside PC 8 for normal check flow. Chief sets this in admin after RX-M1 migration ships. Document in setup guide (LAUNCH-OPS1). |
| SEED-GAP4 | O2 PSI items need priority consideration | Medium | 📋 | Two O2 PSI MEASUREMENT items exist: "On-Board O2 PSI" (DS EC 1) and "Stretcher O2 PSI" (Stretcher compartment). Both have measurement_minimum=500.0 PSI. Chief should decide whether to mark these as priority items surfacing above the compartment list, or leave them in their compartments for normal check flow. Stretcher O2 is likely priority; on-board O2 may be as well. |
| SEED-GAP5 | Jump bag O2 PSI priority consideration | Low | 📋 | Jump Bag Main Pocket contains "Jump Bag O2 PSI" MEASUREMENT item with same 500 PSI minimum. Same decision as SEED-GAP4 for jump bag context. |

---

## 6. Launch Readiness — Operational Checklist (Session J)
##
## These are not development tasks. They are operational tasks the EMS chief
## and project owner must complete before any team member sees the app.
## Tracked here so nothing falls through the cracks at launch time.

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| LAUNCH-OPS1 | Configure priority items for Unit 712 in production admin | EMS chief | 📋 | After RX-M1 ships: open Admin -> Vehicles -> Unit 712 -> Par Levels. Mark AED Battery, LUCAS Device Ready Check, On-Board O2 PSI (and Stretcher O2 PSI if desired) as priority. Set custom question text for each. See SEED-GAP1/GAP2/GAP3/GAP4. |
| LAUNCH-OPS2 | Enter actual physical stock count for Unit 712 | EMS chief / responder | 📋 | Seed data has par levels (target quantities) but NOT actual current stock counts. Before UAT, do a physical count of Unit 712 and enter actual lot quantities via the supply room receive flow or direct stock entry. This is what makes the restock list meaningful from day one. |
| LAUNCH-OPS3 | Enter actual stock count for Unit 712 Jump Bag and Unit 710 Jump Bag | EMS chief / responder | 📋 | Same as LAUNCH-OPS2 for both jump bags. |
| LAUNCH-OPS4 | Add all EMS team members in admin | EMS chief | 📋 | Each of the ~10 team members (EMTs and MFRs) needs to be added to Newberg Township Station 1 with the correct role (Responder or Supervisor). They will receive Azure AD login credentials and need to be on the station member list before their first login. |
| LAUNCH-OPS5 | Chief full walkthrough — shift-start check on Unit 712 | EMS chief | 📋 | Before any volunteer sees the app, the chief should run a complete shift-start check on Unit 712 in the production environment. Every compartment. Priority items. Truck Operations. Submit. Verify the compliance dashboard reflects it. This is his acceptance test. |
| LAUNCH-OPS6 | Volunteer walkthrough — Earl or equivalent | Volunteer responder | 📋 | One volunteer (ideally less tech-comfortable, not the chief) runs a complete check cold, with the 3-screen tutorial as their only guidance. Observe without helping. If they need to ask a question, that's a UX issue to fix before broader launch. |
| LAUNCH-OPS7 | Marcellus Township Station 1 configuration | EMS chief | 📋 | If Ambulance 540 (ALS) is also being launched, repeat LAUNCH-OPS1 through OPS3 for Unit 540. The ALS drug cabinet and controlled substance check configuration needs supervisor review — the ALS drug bag and dual-signature workflow are already seeded but need validation against actual Marcellus Township protocols. |
| LAUNCH-OPS8 | Remove or hide TEST STATION from production | Engineering | 📋 | The "⚠ TEST STATION — Dev Only" and "Unit TEST QRV" must not appear in the production environment. Options: (A) Don't seed test data in production (seed.py already structured to skip it if a flag is set). (B) Deactivate the test station via admin before launch. Option A is cleaner — add a `SEED_TEST_DATA=false` env var check to seed.py. |
| LAUNCH-OPS9 | Verify Azure AD users match station member emails | Engineering | 📋 | StationMember.user_id is keyed on email (preferred_username from JWT). Every team member's Azure AD email must exactly match what the chief enters in the station member list. A mismatch means the member gets the "you're not listed" error on first login. Verify before launch day. |

---

## 7. Backend — Endpoints
| # | Endpoint | Description | Pri | Status |
|---|----------|-------------|-----|--------|
| B-E5 | `POST /inventory/transfer` | Move stock between supply room and vehicle | High | ✅ Done |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` | Stock vs par per item | High | ✅ Done |
| B-E8 | `PUT /inventory/lots/{id}` | Supervisor corrects expiry date on lot | Medium | 📋 |
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 |

---

## 8. Backend — Data Models
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 | |
| B-M10 | Alter `stations`: add `allow_check_modification` | High | 📋 | |
| B-M11 | Alter `stations`: add `primary_color` | High | ✅ Done | |
| NEW-M1 | Alter `vehicles`: add `vehicle_color` | High | ✅ Done | |
| NEW-M2 | Alter `stations`: add `call_sign` | High | ✅ Done | |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 | |

---

## 9. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Force hard-delete | High | 📋 | Admin only |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks | Medium | 📋 | Admin only |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted check | Low | 📋 | Admin only |
| CH-B7 | `PATCH /stations/{id}/settings` | Update station settings | High | 📋 | Admin only |
| CH-B8 | `GET /stations/{id}/settings` | Read station settings | High | 📋 | Supervisor+ |

---

## 10. Backend — Retirement Endpoints
| # | Endpoint | Pri | Status |
|---|----------|-----|--------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | High | 📋 |
| RET-B2 | `PATCH /locations/{id}/retire` | High | 📋 |
| RET-B3 | `PATCH /stations/{id}/retire` | High | 📋 |
| RET-B4 | `GET /admin/retired?type=&station_id=` | Medium | 📋 |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | High | 📋 |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | Medium | 📋 |

---

## 11. Frontend — Help System
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5C1 | First-run tutorial — 3 screens (see RX-F11) | Critical | ➡ RX-F11 | Moved to Section 1 as RX-F11. Session H. |
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | Medium | 📋 | Session J / post-launch. Based on what questions the team actually asks after first month. |

---

## 12. Frontend — Supervisor Dashboard
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5F2 | Compliance calendar | High | ✅ Done | Session F Block 3 |
| SUP-F1 | Open repair count on dashboard header | Critical | ➡ Section 3 | |
| SUP-F2 | Repair count drill-down to V&E Status | High | ➡ Section 3 | |
| F-5F7 | Supply room stock view | Medium | 📋 | Post-launch enhancement |

---

## 13. Frontend — Supporting Modules
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-5G3 | Data export — CSV for history, audit, repairs | Medium | 📋 | Session I. Chief will need this for first compliance reporting cycle. |

---

## 14. Frontend — Check Wizard UX
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| F-UX2 | Left/right chevron navigation between compartments | Medium | 📋 | Session H |
| F-UX3 | "Jump to unvalidated" sticky button | Medium | 📋 | Session H |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | Session H — important for lot expiry management |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 (started_by field) — post-launch |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | Session H — already in seed data, just needs display |
| F-UX7 | Last check banner | High | ✅ Done | Session F Block 4 |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | Post-launch |

---

## 15. Frontend — Check History
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note | High | ⛔ | B-M10, CH-B8 |
| CH-F7 | Deleted records screen | High | 📋 | Session H |
| CH-F8 | Force hard-delete confirmation | High | 📋 | Session H |

---

## 16. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F1 | Settings nav entry | High | 📋 | Session I |
| S-F2 | Shared `ColorPickerWidget` | High | ✅ Done | |
| S-F3 | Allow check modification toggle | High | 📋 | B-M10 — Session I |
| S-F6 | Station management | High | 📋 | RET-B3/B4 — Session I |
| S-F7 | Vehicle management | High | 📋 | RET-B1/B2 — Session I |
| S-F8 | Par level management | Medium | 📋 | B-E9 |

---

## 17. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle | High | 📋 | RET-B1 — Session I |
| RET-F2 | Retire jump bag / portable location | High | 📋 | RET-B2 — Session I |
| RET-F3 | Retire inventory lot | High | 📋 | RET-B5 |
| RET-F4 | Retire station | High | 📋 | RET-B3 |
| RET-F5 | Retired objects list | Medium | 📋 | RET-B4 |

---

## 18. Infrastructure / Security
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall | Medium | 📋 | Before scaling to second service |
| I-2 | Re-add route table | Medium | ⛔ | |
| I-3 | `HTTPSRedirectMiddleware` | Low | 📋 | Session J |
| I-5 | Document Azure AD token lifetime | Low | 📋 | |

---

## 19. Equipment & Station Administration

### Vehicle & Location Management
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B11 | `POST /admin/vehicles` | High | ✅ Done | |
| ADMIN-B12 | `PATCH /admin/vehicles/{id}` | High | ✅ Done | |
| ADMIN-B13 | `POST /admin/locations` | High | ✅ Done | |
| ADMIN-B14 | `PATCH /admin/locations/{id}` | High | 📋 | Label rename for portable locations |
| ADMIN-F6 | Vehicle list view per station | High | ✅ Done | |
| ADMIN-F7 | Portable location list view (Jump Bags) | High | 📋 | PortableLocationsScreen — Session I |
| ADMIN-F10 | Member list search | Low | 📋 | Post-launch |

### Station Management
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ADMIN-B15 | `POST /admin/stations` | Medium | ✅ Done | |
| ADMIN-UX1-F9 | "+ Add Station" form | Medium | ✅ Done | |

---

## 20. Station Membership & Access Control
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| ACC-F1 | Station picker uses `GET /stations/my` | High | 📋 | |
| ACC-F2 | Member list view | High | 📋 | |
| ACC-F3 | Add member form | High | 📋 | |
| ACC-F4 | Remove member confirmation | High | 📋 | |
| ACC-F5 | "Pending assignment" screen | High | 📋 | |

---

## 21. Supply Room & Restocking
*All items complete — Session G.*

| # | Item | Pri | Status |
|---|------|-----|--------|
| SUPPLY-M1 | `STATION_SUPPLY_ROOM` auto-created per station | High | ✅ Done |
| SUPPLY-B1 | `POST /inventory/transfer` | High | ✅ Done |
| SUPPLY-B2 | `GET /inventory/locations/{id}/stock-summary` | High | ✅ Done |
| SUPPLY-B3 | `GET /stations/{id}/supply-room` | High | ✅ Done |
| SUPPLY-F1 | Supply room stock view | High | ✅ Done |
| SUPPLY-F2 | Restock vehicle flow | High | ✅ Done |
| SUPPLY-F3 | Receive stock into supply room | Medium | ✅ Done |
| SUPPLY-F4 | Transfer history | Medium | ✅ Done |

---

## 22. Par Level Assignment UI
*All items complete — Session F Block 5.*

| # | Item | Pri | Status |
|---|------|-----|--------|
| ADMIN-F4a | Par level list on item card | High | ✅ Done |
| ADMIN-F4b | "Assign to Vehicle" flow | High | ✅ Done |
| ADMIN-F4c | Edit/remove par level | High | ✅ Done |
| ADMIN-B6 | `POST /admin/items/{id}/assign` | High | ✅ Done |
| ADMIN-B7 | `PATCH /admin/par-levels/{id}` | High | ✅ Done |
| ADMIN-B8 | `PATCH /admin/par-levels/{id}/deactivate` | High | ✅ Done |

---

## 23. User Acceptance Testing
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| UAT-1 | Test case document | High | ✅ Done | `docs/uat_test_cases.md` |
| UAT-2 | Execute Responder test cases | High | 📋 | Session J — against live Azure, real Unit 712 data |
| UAT-3 | Execute Supervisor test cases | High | 📋 | Session J — chief logged in as Supervisor |
| UAT-4 | Execute Administrator test cases | High | 📋 | Session J |
| UAT-5 | Execute cross-role test cases | Medium | 📋 | Session J |
| UAT-6 | Execute edge case test cases | Medium | 📋 | Session J |
| UAT-7 | Pending assignment test case | High | ⛔ | Needs ACC-F5 |
| UAT-8 | Multi-station test case | Medium | ⛔ | Needs ACC-F1-F5 |
| UAT-9 | Unit 712 full shift-start check — cold run | Critical | 📋 | LAUNCH-OPS5/OPS6. Chief + one volunteer, no coaching, production environment. Pass criterion: zero calls for help, check submitted correctly, compliance dashboard reflects it. |
| UAT-10 | After-call usage log — cold run | Critical | 📋 | Same volunteers, same session. Simulate returning from a call. Log 2-3 items used. Verify restock list updates. Pass criterion: completed in under 60 seconds without explanation. |
| UAT-11 | Damaged item scenario — cold run | High | 📋 | During UAT-9 or UAT-10: simulate discovering a damaged item (e.g. AED battery light not green). Verify the in-context path works, repair request is created, chief sees it on compliance dashboard. |

---

## 24. Code Cleanup + Theme Consolidation — Pre-Session H
##
## Theme diagnosis: index.css already has a solid token system (:root variables for
## color, spacing, radius, shadow, typography). The problem is the module CSS files
## don't consistently use it. supervisor.css uses raw rem values (0.75rem, 0.625rem,
## 1.25rem) instead of --space-md, --radius-lg, --font-size-sm. Every new module
## author re-invents values that already exist as tokens. The fix is:
##   (1) Add missing tokens to index.css (vehicle color, component-level patterns)
##   (2) Fix the two offending module files to use tokens
##   (3) Make it a rule in CLAUDE.md so it never drifts again
## This is NOT a full CSS refactor. It is a targeted fix of known violations.

### Theme items
| # | Action | Status | Notes |
|---|--------|--------|-------|
| TECH-THEME1 | Extend index.css :root token system | ✅ Done | Add missing tokens to the existing :root block in index.css. Do NOT create a new file. Additions: `--vehicle-primary: var(--station-primary)` (vehicle color falls back to station color until vehicle-specific color is set — set via inline style on the component root, same pattern as --station-primary); `--color-damaged: #dc2626` + `--color-damaged-bg: #fef2f2`; `--color-priority: #185fa5` + `--color-priority-bg: #e6f1fb`; `--color-no-change: #3b6d11` + `--color-no-change-bg: #eaf3de`. Also add shared component utility classes to index.css (after the module-card section): `.ems-card` (white surface, border, radius-lg, shadow-sm — the pattern repeated in every module), `.ems-card--warn` (amber border), `.ems-card--fail` (red border), `.ems-card--pass` (green border), `.ems-section-head` (section label: 11px, uppercase, letter-spacing, muted color), `.ems-preview-row` (flex, space-between, font-size-sm). These replace the per-module reinventions of the same patterns. |
| TECH-THEME2 | Fix supervisor.css — replace raw values with tokens | ✅ Done | Search for every raw rem/px value in supervisor.css and replace with the matching token. Key replacements: `0.75rem` -> `var(--space-sm)` (for gaps and small padding), `1rem` -> `var(--space-md)`, `1.5rem` -> `var(--space-lg)`, `0.625rem` -> `var(--radius-md)`, `1.25rem` -> `var(--font-size-h2)`, `0.85rem` -> `var(--font-size-sm)`, `0.9rem` -> `var(--font-size-sm)`, `0.6rem` -> a new `--font-size-xs: 12px` token added in TECH-THEME1, hardcoded `#fef2f2`/`#fffbeb`/`#f0fdf4` -> `var(--color-status-fail-bg)` / `var(--color-status-warn-bg)` / `var(--color-status-pass-bg)`. Read the full file before editing. |
| TECH-THEME3 | Fix supply-room.css — replace raw values with tokens | ✅ Done | Same pass as TECH-THEME2 for supply-room.css. Also verify check-history.css and vehicles.css for the same issue — if they have raw values, fix them in the same pass. |
| TECH-THEME4 | Add theme enforcement rules to CLAUDE.md | ✅ Done | Add a "CSS and Theming" section to CLAUDE.md with these mandatory rules: (1) All CSS values must use tokens from index.css :root — no hardcoded hex colors, rem values, or px sizes except for 0, 1px borders, and media query breakpoints. (2) New components use `.ems-card`, `.ems-section-head`, `.ems-preview-row` utility classes from index.css before writing custom CSS. (3) Station color is always `var(--station-primary)` / `var(--station-text)`. Vehicle color is always `var(--vehicle-primary)` which inherits from station color by default. (4) New Session H/I/J styles go into the relevant module CSS file — never a new patch file. (5) Before adding a CSS rule, check if index.css already has a utility class that does the job. |

### CSS cleanup items
| # | Action | Status | Notes |
|---|--------|--------|-------|
| TECH-CSS1a | Delete 5 empty tombstone CSS files | ✅ Done | `src/module-card-fix.css`, `src/submitted-screen-patch.css`, `src/wizard-station.css`, `src/wizard.css`, `admin/admin-station-edit.css` |
| TECH-CSS1b | Merge `admin-wrap-fix.css` into `admin.css` | ✅ Done | Move `.admin-station-btn-wrap` styles, remove file and import. Note: admin.css already contains the btn-wrap block — it was partially merged. Verify the file contents match before deleting. |
| TECH-CSS1c | CSS placement rule in CLAUDE.md | ✅ Done | Covered by TECH-THEME4. No separate action needed. |

### Code cleanup items
| # | Action | Status | Notes |
|---|--------|--------|-------|
| TECH-CODE1a | Delete `Step4Review.jsx` | ✅ Done | Dead — replaced by Step5Submit.jsx |
| TECH-CODE1b | Delete `vehicles/_patch_note.txt` | ✅ Done | Stray code snippet |
| TECH-CODE1c | Fix `useApi.js` stale-data reset | ✅ Done | `setData(null)` at start of execute() |
| TECH-CODE1d | Cross-reference comments: status computation | ✅ Done | Server `_compute_line_item_status` <-> frontend `deriveDraftItemStatus` |
| TECH-CODE1e | Consolidate vehicle update functions in `adminApi.js` | ✅ Done | `updateVehicle` / `updateVehicleDetails` / `updateVehicleColor` |
| TECH-CODE1f | Deduplicate stations fetch | ✅ Done | `checkApi.getStations` and `adminApi.getMyStations` — same endpoint |

---

## 25. Open Questions
| # | Question | Owner | Notes |
|---|----------|-------|-------|
| Q-3 | 90-day max range sufficient for compliance calendar? | Project owner | |
| Q-6 | Auto-hard-delete scheduler: Azure Function or startup cleanup job? | Engineering | |
| Q-7 | Check modification setting default: False or True? | Project owner | |
| Q-8 | Restored soft-deleted checks: responder history or admin screen only? | Project owner | |
| Q-11 | After-Call Reset: lightweight standalone usage record vs DailyInventoryCheck with check_type='USAGE'? ADR needed before RX-B1. | Engineering | Resolve before Session I |
| Q-12 | After-Call Reset: auto-decrement stock lots on log, or record-only until supervisor confirms? | Project owner | Resolve before Session I |
| Q-13 | ~~Priority items ceiling?~~ **RESOLVED: uncapped, supervisor-controlled.** | ✅ Closed | |
| Q-14 | ~~No Change attestation equivalence?~~ **RESOLVED: equivalent to fully-tapped. Simpler write path.** | ✅ Closed | |
| Q-15 | Priority item staleness thresholds: 7 days amber / 14 days red — right for your check frequency? | Project owner | Resolve before Session H |
| Q-16 | SEED-GAP2: Truck Operations compartment — should all FUNCTIONAL items be marked priority_check (forcing individual confirmation), or add a compartment-level `requires_full_check` flag? | Project owner + Engineering | Resolve before RX-F8 is built |
| Q-17 | SEED-GAP1: Add "LUCAS Device Ready Check" FUNCTIONAL item to seed.py before Session H, or have chief add it manually in production admin? | Engineering | Recommendation: add to seed.py for consistency |
| Q-18 | LAUNCH-OPS8: Suppress test station in production via SEED_TEST_DATA env var, or deactivate via admin before launch? | Engineering | Recommendation: env var — cleaner, no admin action needed |
| Q-19 | LAUNCH-OPS7: Is Marcellus Township Station 1 (Unit 540 ALS) in scope for initial launch, or Newberg Township only? | Project owner | Determines scope of LAUNCH-OPS1-OPS6 |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Workflow Acceleration — Check Wizard | 6 | 0 | 6 |
| Workflow Acceleration — No Change / Modify | 2 | 0 | 2 |
| Workflow Acceleration — Priority Items | 4 | 0 | 4 |
| Workflow Acceleration — After-Call Reset | 2 | 0 | 2 |
| Workflow Acceleration — Language + Errors | 1 | 0 | 1 |
| Workflow Acceleration — Tutorial | 1 | 0 | 1 |
| Damaged Item Status | 5 | 0 | 5 |
| Supervisor Dashboard Enhancements | 3 | 0 | 3 |
| AI Item Identification — Groundwork | 4 | 0 | 4 |
| Seed Data Gaps — Unit 712 | 5 | 0 | 5 |
| Launch Readiness — Operational Checklist | 9 | 0 | 9 |
| Security — Pre-H + Session H + Operational | 8 | 0 | 8 |
| Security — Pre-User Gate | 1 | 0 | 1 |
| Backend — Endpoints | 5 | 0 | 5 |
| Backend — Data Models | 6 | 0 | 6 |
| Backend — Check History | 5 | 1 | 6 |
| Backend — Retirement | 6 | 0 | 6 |
| Frontend — Help System | 1 | 0 | 1 |
| Frontend — Supervisor Dashboard | 1 | 0 | 1 |
| Frontend — Supporting Modules | 1 | 0 | 1 |
| Frontend — Check Wizard UX | 5 | 1 | 6 |
| Frontend — Check History | 3 | 1 | 4 |
| Frontend — Settings | 5 | 0 | 5 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Infrastructure / Security | 3 | 1 | 4 |
| Equipment & Station Admin | 4 | 0 | 4 |
| Station Membership Frontend | 5 | 0 | 5 |
| Supply Room & Restocking | 8 | 0 | 8 |
| Par Level Assignment | 6 | 0 | 6 |
| User Acceptance Testing | 9 | 2 | 11 |
| Code Cleanup + Theme Pre-Session H | 13 | 0 | 13 |
| **Total open** | **142** | **6** | **148** |

*Session G in progress — Supply Room delivered, tests pending final verification.*
*Completed items — Sessions A-F — are in backlog_completed.md.*
*v1.52 — 2026-06-04: Major bloat-drop (142 -> 115). Promoted damaged items. Added AI groundwork.*
*v1.56 — 2026-06-04: OPSECDEV review complete. Scores: Auth A, AuthZ A, Audit A, Secrets A,*
*  Dependency security A. Gaps: staticwebapp.config.json missing (Critical), no npm audit in CI,*
*  seed.py no production guard, no ESLint in CI, HTTPSRedirectMiddleware deferred too long,*
*  MSAL tokens in localStorage, /health leaks env. Added Section 0A (8 security items).*
*  I-3 upgraded from Low to High, moved from Session J to Session H.*
*v1.55 — 2026-06-04: CSS theme consolidation (TECH-THEME1 through TECH-THEME4).*
*  Diagnosis: index.css token system is sound. supervisor.css and supply-room.css use raw rem values*
*  instead of tokens. Fix: extend tokens (vehicle color, damaged, priority, no-change, xs font size,*
*  shared .ems-card/.ems-section-head/.ems-preview-row utility classes), fix the two offending files,*
*  enforce via CLAUDE.md. Not a full refactor — targeted token enforcement.*
*  Pre-H now 13 items across theme (4) + CSS cleanup (3) + code cleanup (6). Est. 90 min.*
*v1.54 — 2026-06-04: Added SUP-F3 (expiring items alert).*
*  SEED-GAP1 through GAP5 documenting Unit 712 specific configuration decisions needed before Session H).*
*  Added Section 6 (Launch Readiness Operational Checklist — LAUNCH-OPS1 through OPS9).*
*  Added RX-F11 (first-run tutorial — moved from F-5C1, elevated to Critical, Session H not J).*
*  Added SUP-F1/F2 (repair count on compliance dashboard — new Section 3).*
*  Extended RX-F10 to explicitly cover all error messages in plain English.*
*  Added UAT-9/10/11 (cold-run dress rehearsals with real users on real data).*
*  Added Q-16/17/18/19 (Truck Operations policy, LUCAS seed gap, test station suppression, Marcellus scope).*
*  RX-M1 updated: also add priority_question VARCHAR(150) alongside priority_check boolean.*
*  Real inventory confirmed: Unit 712 BLS, Unit 712 Jump Bag, Unit 710 Jump Bag all seeded from*
*  actual paper inventory sheets. Compartment names match physical stencils on the vehicle.*
*  Physical stock counts (LAUNCH-OPS2/3) are the one remaining data gap before UAT is meaningful.*
