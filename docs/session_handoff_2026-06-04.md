# EMS ReadyKit — Session Handoff
# Date: 2026-06-04
# Type: Design & Planning Session (no code written)
# Next session: Pre-H Cleanup → Session H

---

## What this session was

This was a full-day design and planning session — no code was written, but the decisions
made here directly determine the quality of everything built from Session H forward.

The session covered:
- UX/UI sanity check from two real personas (tired responder, 68yo rural EMS chief)
- External feedback list evaluation (13 items — adopted some, deferred most)
- Backlog restructure: major bloat-drop (142 → 136 items), refactoring audit
- CSS and code debt audit — identified dead files and live issues
- Competitive market analysis (PSTrax, First Due, AngelTrack, others)
- Seed data audit against real inventory — confirmed real Unit 712 data is in system
- Launch philosophy established: one launch, one chance, no beta
- Session roadmap revised end-to-end

---

## Decisions made — record these, they won't be in the code

### UX decisions
- "No Change" compartment attestation writes REAL quantities (quantity_found = min_quantity)
  not flags. Audit trail always has real numbers.
- "No Change" is BLOCKED on compartments with: last check FAIL/SHORT, priority items,
  or damaged items. Must open and verify those.
- "No Change" and "fully-tapped" are EQUIVALENT for compliance (Q-14 closed).
  No attestation_method field needed. Simpler write path.
- Priority items are UNCAPPED per vehicle — supervisor judges, no hard ceiling (Q-13 closed).
- RX-M1 adds BOTH priority_check (bool) AND priority_question (VARCHAR 150) to par_levels.
- Step 1 disclosure label must say "Change date or add crew member" — not "More options."
- "Out of service" term KEPT — team uses this operationally.
- After-Call Reset: recents + search, NOT a flat 200-item list. Flat list at scale is worse
  than the wizard it replaces.

### Architecture decisions
- Second crew as free-text field KEPT. DB linkage, structured picker, "checks I helped with"
  tab all DROPPED. Simple is right for this scale.
- Loaned items, notifications, feedback, user-requests, user-preferences table all DROPPED.
  Re-add only if service grows past 30 users or 3 stations.
- AI fields (ai_tags, alternate_names, reference_image_url, barcode) are DORMANT since
  migration 0009 — they exist in the DB. Session H adds the admin UI to populate them.
  Barcode scanning (AI-F2/F3) is post-launch once real reference data exists.

### Inventory/seed decisions
- Real Unit 712 BLS inventory confirmed seeded from actual paper forms. Compartment names
  match physical stencils on the vehicle doors.
- SEED-GAP1: Add "LUCAS Device Ready Check" FUNCTIONAL item to seed.py before Session H.
  Chief cannot mark LUCAS as priority without this item existing.
- SEED-GAP2 (Q-16): Truck Operations must not allow No Change — all 12 FUNCTIONAL items
  require physical verification. Decision: mark all as priority_check = true (Option A).
  Simpler than a new compartment flag.
- SEED-GAP3: AED Battery (FUNCTIONAL) marked priority. The other 3 AED items (date/pads)
  stay in PC 8 for normal check flow.
- Physical stock counts for Unit 712 (LAUNCH-OPS2/3) are the ONE remaining data gap.
  Par levels exist; actual quantities don't. Chief must do a physical count before UAT.

### Competitive analysis finding
- One commercial feature present in every competitor that EMS ReadyKit was missing:
  proactive expiring items alert. Added as SUP-F3. No new migration needed —
  StockLot.expiration_date already exists. Half-session to implement.
- PSTrax's "Check-All" is equivalent to No Change but less sophisticated (no stock preview,
  no block on known problems). Our implementation is already better.

### Launch gate (non-negotiable before any user sees the app)
All of the following must be true simultaneously:
1. Check wizard redesign complete (No Change / Modify / Priority Items)
2. After-call reset flow complete
3. Damaged item marking complete
4. First-run tutorial complete (3-screen minimum)
5. All responder-facing language plain English (no jargon, no technical errors)
6. Open repair count + expiring items visible on compliance dashboard
7. Vehicle + location retirement actions complete
8. Priority items configured in admin for Unit 712 (AED, LUCAS, O2, Truck Ops)
9. UAT executed against live Azure with real Unit 712 inventory
10. Physical stock count entered for Unit 712 (actual counts, not seed par levels)
11. All tests passing (231+ green)
12. Code cleanup complete

---

## Open questions requiring answers BEFORE Session H starts

**Q-15** — Priority item staleness thresholds: 7 days amber / 14 days red — right for your
  check frequency? (Project owner)

**Q-16** — RESOLVED IN THIS SESSION: Truck Operations — mark all FUNCTIONAL items as
  priority_check = true. This is the answer. Update seed.py accordingly in pre-H cleanup.

**Q-17** — LUCAS Device Ready Check: add to seed.py (recommended) or chief adds manually?
  Recommendation: add to seed.py before Session H for consistency.

**Q-18** — Test station suppression: SEED_TEST_DATA env var (recommended) vs admin deactivation.

**Q-19** — Is Marcellus Township (Unit 540 ALS) in scope for initial launch?
  This determines whether LAUNCH-OPS1-OPS6 runs once (Newberg only) or twice.

---

## Pre-Session H checklist — do ALL of these before writing one line of Session H code

### Theme consolidation (TECH-THEME1 through TECH-THEME4) — do first

**Why this is first:** Every component built in Session H will use the new tokens and
utility classes. If you add them after, you're doing the theme pass twice.

1. Open `frontend/src/index.css`. In the :root block, add these tokens after the
   existing --station-primary / --station-text lines:

   ```css
   /* Vehicle color — inherits station color until overridden per-component */
   --vehicle-primary: var(--station-primary);

   /* Semantic state colors — new for H */
   --color-damaged:          #dc2626;
   --color-damaged-bg:       #fef2f2;
   --color-priority:         #185fa5;
   --color-priority-bg:      #e6f1fb;
   --color-no-change:        #3b6d11;
   --color-no-change-bg:     #eaf3de;

   /* Missing type scale token */
   --font-size-xs: 12px;
   ```

   Then add these utility classes to index.css after the .module-card section:

   ```css
   /* ── Shared card pattern ────────────────────────────────────────────────── */
   /* Use .ems-card instead of re-writing surface+border+radius+shadow per module */
   .ems-card {
     background: var(--color-surface);
     border: 1px solid var(--color-border);
     border-radius: var(--radius-lg);
     box-shadow: var(--shadow-sm);
     overflow: hidden;
   }
   .ems-card--pass { border-color: #c0dd97; }
   .ems-card--warn { border-color: var(--color-status-warn); }
   .ems-card--fail { border-color: var(--color-status-fail); }
   .ems-card--priority { border: 1.5px solid var(--color-priority); }
   .ems-card--damaged  { border: 1.5px solid var(--color-damaged); }

   /* ── Section heading pattern ────────────────────────────────────────────── */
   /* Replaces per-module .sup-section-label, .admin-section-head, etc */
   .ems-section-head {
     font-size: var(--font-size-xs);
     font-weight: 500;
     color: var(--color-text-muted);
     letter-spacing: 0.08em;
     text-transform: uppercase;
     margin-bottom: var(--space-sm);
   }

   /* ── Preview row pattern ────────────────────────────────────────────────── */
   /* Stock preview strip inside compartment cards */
   .ems-preview-row {
     display: flex;
     align-items: center;
     justify-content: space-between;
     padding: 2px 0;
     font-size: var(--font-size-sm);
   }
   .ems-preview-row__name  { color: var(--color-text-secondary); }
   .ems-preview-row__stock { color: var(--color-text-muted); }
   .ems-preview-row__stock--short { color: var(--color-status-warn); font-weight: 500; }
   .ems-preview-row__stock--ok    { color: var(--color-no-change); font-weight: 500; }
   ```

2. Open `frontend/src/modules/supervisor/supervisor.css`.
   Replace every raw rem/px value with tokens:
   - `0.75rem` -> `var(--space-sm)` (gaps, small padding)
   - `1rem`    -> `var(--space-md)`
   - `1.5rem`  -> `var(--space-lg)`
   - `0.625rem` -> `var(--radius-md)`
   - `1.25rem` -> `var(--font-size-h2)` (or `var(--font-size-lg)` where used as text)
   - `0.85rem`, `0.9rem` -> `var(--font-size-sm)`
   - `0.6rem`  -> `var(--font-size-xs)` (new token from step 1)
   - `#fef2f2` -> `var(--color-status-fail-bg)`
   - `#fffbeb` -> `var(--color-status-warn-bg)`
   - `#f0fdf4` -> `var(--color-status-pass-bg)`
   - `#7f1d1d` -> `var(--color-status-fail)`
   - `#78350f` -> `var(--color-status-warn)`
   - `#2d7a2d` -> `var(--color-status-pass)`
   Read the full file before editing. Verify the app still renders correctly.

3. Open `frontend/src/modules/supply-room/supply-room.css`.
   Same raw-value replacement pass as step 2.
   Also check `check-history.css` and `vehicles.css` — if they have raw values, fix
   them in the same pass. Refer to index.css :root for the correct token names.

4. Open `CLAUDE.md`. Add a "CSS and Theming" section with these rules:
   - All CSS values use tokens from index.css :root. No hardcoded hex, rem, or px
     except: 0, 1px borders, and media query breakpoints.
   - New components reach for .ems-card, .ems-section-head, .ems-preview-row before
     writing custom CSS. Check index.css first.
   - Station color: always var(--station-primary) / var(--station-text). Set via
     inline style on body from HomePage (already wired).
   - Vehicle color: always var(--vehicle-primary). Falls back to station color.
     Override per-component via inline style when vehicle-specific color is needed.
   - New styles for Session H/I/J go into the relevant module CSS file only.
     wizard.css for check wizard. supervisor.css for supervisor module. Never new files.
   - Before adding any CSS rule: search index.css for an existing utility class.

### Code cleanup (TECH-CSS1a through TECH-CODE1f)
In order:

1. `Delete` frontend/src/module-card-fix.css (empty tombstone)
2. `Delete` frontend/src/submitted-screen-patch.css (empty tombstone)
3. `Delete` frontend/src/wizard-station.css (empty tombstone)
4. `Delete` frontend/src/wizard.css (empty tombstone)
5. `Delete` frontend/src/modules/admin/admin-station-edit.css (empty tombstone)
6. Merge frontend/src/modules/admin/admin-wrap-fix.css INTO admin.css
   - Copy the .admin-station-btn-wrap block into the station button section of admin.css
   - Remove the admin-wrap-fix.css file
   - Remove its import from admin/index.jsx
7. Add to CLAUDE.md: "New Session H styles go into existing module files only.
   styles/wizard.css for check wizard. index.css for home page. Zero new patch files."
8. `Delete` frontend/src/modules/check-wizard/components/Step4Review.jsx (dead file)
9. `Delete` frontend/src/modules/vehicles/_patch_note.txt (stray snippet)
10. Fix frontend/src/shared/hooks/useApi.js: add setData(null) at start of execute()
    before setLoading(true). Prevents stale compartment data flash on vehicle switch.
11. Add cross-reference comment to app/ems_readykit/routers/checks.py near
    _compute_line_item_status: "# Mirror of frontend deriveDraftItemStatus in
    src/shared/utils/statusCalc.js — update both if business rules change"
12. Consolidate adminApi.js vehicle update functions:
    updateVehicle / updateVehicleDetails / updateVehicleColor
    Review whether backend can take a single PATCH — if yes, collapse to one function.
13. Deduplicate stations fetch: checkApi.getStations and adminApi.getMyStations both
    call GET /api/v1/stations/my. Move to shared/api/stationsApi.js, import from both.

### Seed data updates (before Session H)
14. Add "LUCAS Device Ready Check" FUNCTIONAL item to seed.py build_ambulance_inventory():
    - check_type = FUNCTIONAL, unit_of_measure = "N/A"
    - Place after "LUCAS Date of Last Charge" in PC 8
    - The priority_question ("Is the battery charged and the device ready to deploy?")
      will be set by the chief in admin after RX-M1 migration ships
15. Mark all 12 FUNCTIONAL items in Truck Operations as priority_check = true in seed.py
    (Q-16 resolved — Option A, simpler, no new compartment flag needed)
    Note: RX-M1 migration must ship first. Add a seed guard: only set priority_check if
    the column exists (check information_schema or use try/except on the attribute).

### Verify clean state
16. cd app && alembic upgrade head
17. python seed.py (verify LUCAS item and Truck Operations priority flags applied)
18. pytest (verify all 231+ tests still pass)

---

## Session H — what to build, in what order

Session H is the largest session in the project. It rewrites the check wizard's
interaction model and adds the supervisor dashboard enhancements. Build in this order
to avoid rework:

**Phase 1 — Migration first (30 min)**
- RX-M1: Migration 0015, add priority_check bool + priority_question VARCHAR(150)
  to par_levels table. Run alembic, update ParLevel model and schema.

**Phase 2 — Backend (60 min)**
- DMG-B1: PATCH /inventory/items/{id}/status — damaged flag
- B-E8: PUT /inventory/lots/{id} — lot expiry correction
- SUP-F3 backend: GET /inventory/expiring-soon?station_id=&days=30
  (or extend existing compliance endpoint)

**Phase 3 — Home screen and Step 1 (60 min)**
- RX-F1: Home screen — two dominant actions
- RX-F3: Collapse Step 1, specific disclosure label

**Phase 4 — Step 2 compartments — the core redesign (120 min)**
- RX-F8: No Change / Modify interaction (biggest single item in session)
- RX-F9: Priority items section above compartment list
- RX-F9a: Custom question text display
- RX-F9b: Last confirmed display

**Phase 5 — Item row and Step 3 (60 min)**
- RX-F2: Auto-confirm at par (ItemRow.jsx — touch carefully, 16KB)
- DMG-F1: Mark damaged button inline
- DMG-F2: Damaged badge in compartment preview
- RX-F7: Button language fix

**Phase 6 — Submit and submitted screens (45 min)**
- RX-F4: Simplify Step 5 for clean PASS
- RX-F5: Restock list link on SubmittedScreen

**Phase 7 — Supervisor dashboard (60 min)**
- SUP-F1: Open repair count
- SUP-F3: Expiring items alert + ExpiringItemsPanel component
- DMG-F3: Damaged badge in supply room

**Phase 8 — Check history admin (45 min)**
- CH-F7: Deleted records screen
- CH-F8: Force hard-delete confirmation

**Phase 9 — Language pass (60 min)**
- RX-F10: All responder-facing strings + every error message
  Do this last so you're sweeping the final Session H UI, not an intermediate state.

**Phase 10 — Tutorial (60 min)**
- RX-F11: 3-screen first-run overlay

**Phase 11 — Remaining UX items (60 min)**
- F-UX2: Left/right chevron nav between compartments
- F-UX3: Jump to unvalidated sticky button

**End of session**
- Run all tests
- Commit
- Update backlog.md (move completed items, update summary counts)
- Update CODEBASE_INDEX.md (new files, changed sizes, migration count)
- Write Session I handoff

---

## What is NOT in Session H

These are Session I:
- RX-F6: After-Call Reset flow
- RX-B1: POST /checks/usage
- Retirement endpoints and UI
- AI-B1, AI-F1: AI fields admin
- SUP-F2: Repair count drill-down
- Data export CSV
- Settings module

These are post-launch:
- Barcode scanning (AI-F2/F3)
- Per-step contextual help (F-5C2)
- Portable location admin (ADMIN-F7)
- Azure Firewall (I-1)

---

## Files Session H will touch

**Modify (read before touching):**
- frontend/src/pages/HomePage.jsx — RX-F1 home screen
- frontend/src/modules/check-wizard/index.jsx — orchestration changes
- frontend/src/modules/check-wizard/components/Step1Vehicle.jsx — RX-F3
- frontend/src/modules/check-wizard/components/Step2Compartments.jsx — RX-F8/F9 (major rewrite)
- frontend/src/modules/check-wizard/components/Step3Items.jsx — RX-F2, DMG-F1
- frontend/src/modules/check-wizard/components/ItemRow.jsx — RX-F2 (16KB, touch carefully)
- frontend/src/modules/check-wizard/components/Step5Submit.jsx — RX-F4
- frontend/src/modules/check-wizard/components/SubmittedScreen.jsx — RX-F5
- frontend/src/modules/supervisor/index.jsx — SUP-F1, SUP-F3
- frontend/src/modules/supervisor/components/ComplianceSummary.jsx — SUP-F1, SUP-F3
- frontend/src/modules/check-history/index.jsx — CH-F7/F8 entry points
- frontend/src/styles/wizard.css — new styles for No Change, priority items, damaged badges
- frontend/src/index.css — home screen redesign styles
- app/ems_readykit/models/par_level.py — add priority_check, priority_question
- app/ems_readykit/schemas/par_level.py — expose new fields
- app/ems_readykit/routers/inventory.py — DMG-B1 endpoint
- app/alembic/versions/ — migration 0015

**Create new:**
- frontend/src/modules/supervisor/components/ExpiringItemsPanel.jsx — SUP-F3
- frontend/src/modules/check-wizard/components/TutorialOverlay.jsx — RX-F11
- frontend/src/modules/check-history/components/DeletedChecksScreen.jsx — CH-F7
- app/alembic/versions/0015_priority_check_on_par_levels.py — migration

---

## Current system state

- Backend: Azure App Service B1
  https://app-ems-readykit-dev.azurewebsites.net
- Frontend: Azure Static Web Apps
  https://lively-bush-0ed75ca10.7.azurestaticapps.net
- Migrations applied: 0001-0014 (plus 0003a branch) — 14 total
- Tests: 231 passing (verify with `cd app && pytest` at start of pre-H cleanup)
- Session G: Supply room delivered, UAT pending final verification
  FIRST COMMAND of pre-H: `cd app; alembic upgrade head; python seed.py; pytest`

---

## The thing to remember above all else

This app ships once. Earl is 61 years old, runs a combine six months a year, and has
been volunteering for nine years because he cares about his neighbors. The EMS chief
is 68, ex-Detroit PD, not tech-savvy, and has seen what happens when complicated
systems fail first responders under stress.

If Earl can do a truck check without calling the chief for help, and if the chief can
see at a glance that the truck is ready and nothing is expiring — the app succeeded.

Build to that standard. Not to a feature list.

---

## OPSECDEV review — 2026-06-04

Full review conducted against: auth.py, config.py, main.py, deps.py, audit.py,
deploy.yml, requirements.txt, client.js, useAuth.jsx, .gitignore.

### Solid (no action needed)
- Authentication: Azure AD RS256, JWKS, tenant ID check, audience enforcement,
  expiry/nbf required. Test tokens hard-blocked in production. Grade: A
- Authorization: Dual enforcement server+frontend. Single source in deps.py.
  Station membership scoping. Grade: A
- Audit trail: Immutable, centralised, actor JWT-bound, structured logging. Grade: A
- Secrets: Key Vault via Managed Identity. No secrets in code or committed files. Grade: A
- Dependencies: pip-audit gates every merge. All packages current. Grade: A

### Fix before launch — in pre-H order

1. **SEC-PRE1 (Critical)** — Create `frontend/staticwebapp.config.json`
   Referenced in main.py comments but DOES NOT EXIST in the repo.
   Minimum required content:
   ```json
   {
     "globalHeaders": {
       "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://login.microsoftonline.com https://app-ems-readykit-dev.azurewebsites.net; frame-ancestors 'none'",
       "X-Frame-Options": "DENY",
       "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
     },
     "navigationFallback": {
       "rewrite": "/index.html",
       "exclude": ["/api/*", "/assets/*", "/*.{js,css,png,ico,json}"]
     }
   }
   ```
   The navigationFallback also fixes React Router 404s on direct URL navigation
   — users who bookmark a deep link currently get Azure's default 404 page.

2. **SEC-PRE2 (High)** — Add to deploy.yml build-frontend job after `npm ci`:
   ```yaml
   - name: Frontend security audit
     working-directory: ${{ env.FRONTEND_DIR }}
     run: npm audit --audit-level=high
   ```

3. **SEC-PRE3 (High)** — Add to top of seed.py after imports:
   ```python
   import sys
   if os.environ.get("APP_ENV", "").lower() == "production":
       print("[seed] Skipped: APP_ENV=production")
       sys.exit(0)
   ```
   AND add to startup.sh:
   ```bash
   if [ "$APP_ENV" != "production" ]; then
       python seed.py
   fi
   ```

4. **SEC-PRE4 (Medium)** — Add to deploy.yml build-frontend job:
   ```yaml
   - name: Lint
     working-directory: ${{ env.FRONTEND_DIR }}
     run: npm run lint
   ```
   If `lint` script missing from package.json, add:
   `"lint": "eslint src --max-warnings 0"`

5. **SEC-H1 (High)** — In main.py create_app(), after security headers middleware:
   ```python
   from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
   if settings.is_production:
       app.add_middleware(HTTPSRedirectMiddleware)
   ```
   Wrap in is_production — the middleware breaks local dev (HTTP only).
   Order matters: security headers → HTTPSRedirect → CORS.

6. **SEC-H2 (High)** — Check `frontend/src/shared/api/authConfig.js`.
   In the PublicClientApplication config, set:
   ```js
   cache: { cacheLocation: "sessionStorage", storeAuthStateInCookie: false }
   ```
   Tokens cleared on tab close. No functional impact on any user workflow.

7. **SEC-H3 (Medium)** — In main.py health endpoint:
   ```python
   # Change from:
   return {"status": "ok", "env": settings.app_env}
   # To:
   return {"status": "ok"}
   ```

### Post-launch (SEC-OPS1)
Add `.github/workflows/dependency-audit.yml` scheduled monthly.
Runs pip-audit + npm audit, opens GitHub issue on high/critical findings.
