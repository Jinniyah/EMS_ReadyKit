# EMS ReadyKit — Completed Items (Portfolio Changelog)
# Last updated: 2026-07-11
# This is a condensed, portfolio-ready version of the project's session history.
# Each entry summarizes the goal, root cause, and resolution for a completed
# session. Bug/item tracking-ID tables and step-by-step debugging narratives have
# been removed in favor of prose summaries suitable for external review.
# Sessions completed: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, AA, AB, AC, AD, AE, AF, AG, AH, AI, AJ, AK, AL, AM, AN, AO, AP, AQ, AR
# Active backlog -> docs/backlog.md

---

## Session AR — SEC-03: OpenAPI Docs Gating Fix and Key Vault Firewall Outage (2026-07-11)

Goal: fix SEC-03 from the Portfolio Evidence Checklist — `/docs`, `/redoc`, and `/openapi.json` were reachable on the live UAT App Service instead of returning 404.

Root cause: `main.py` gated the OpenAPI docs on `settings.is_production`, which is derived from `APP_ENV`. This project's single deployed App Service deliberately runs with `APP_ENV=development` for resource-naming and cost purposes (an intentional, pre-existing decision, not a misconfiguration) — so `is_production` was always `False` there, and the docs were never actually disabled on the public UAT app. This is the same class of bug as the 2026-07 `REQUIRE_REAL_AUTH` incident: a security-relevant setting was implicitly tied to `APP_ENV` instead of being its own explicit, secure-by-default flag.

Fix: added a new `enable_api_docs` setting to `core/config.py`, defaulting to `False` and fully decoupled from `APP_ENV`/`is_production`, mirroring the existing `require_real_auth` pattern (including a belt-and-suspenders explicit `"false"` entry in the Terraform `app_settings` map, alongside `REQUIRE_REAL_AUTH`). `main.py`'s `docs_url`/`redoc_url`/`openapi_url` now key off `settings.enable_api_docs` directly. `.env.example` was updated so local development still gets docs by default (`ENABLE_API_DOCS=true` locally). While rewriting the Terraform `app_settings` map, an unrelated copy error was caught and fixed before it shipped: a rewrite of `modules/app/main.tf` had accidentally dropped the `AppServiceAppLogs` diagnostic log category from the App Service's diagnostic settings resource.

**Same-session incident:** applying this fix (`terraform apply` followed by the GitHub Actions code deploy) surfaced a separate, pre-existing infrastructure gap as a full outage. The App Service's managed identity calls to Key Vault began failing with `(Forbidden) ... ForbiddenByFirewall` — `bypass="AzureServices"` on the Key Vault's `network_acls` does not cover a generic App Service reading its own secrets, and the App Service's own VNet-integrated subnet (`snet-app`) had never been allowlisted via `virtual_network_subnet_ids`, nor did it have the `Microsoft.KeyVault` service endpoint that `snet-data` already had for Postgres/Storage. When the Key Vault call failed, `resolve_database_url()`'s fallback to the raw `DATABASE_URL` app setting also failed, because that setting is itself an unresolved App Service Key Vault reference (`@Microsoft.KeyVault(...)`) resolved through the identical firewall path — producing a `sqlalchemy.exc.ArgumentError` trying to parse the literal reference string as a connection URL, and the app never came up (`503`/"Application Error").

Root-cause isolation ruled out the SEC-03 change itself: `test-backend` (full pytest suite, exercising `Settings()` and `create_app()`) gates the deploy job, and the `terraform apply` plan output was independently confirmed to touch only the two expected `app_settings` keys, a diagnostic log category, and unrelated pre-existing drift (a manually-deleted action group/alert, a storage diagnostic metric reshape) — nothing touching `network_acls`, subnets, or service endpoints. Diagnosed via Azure Portal Log Stream, which showed the `ForbiddenByFirewall` error and full traceback from `startup.sh`'s pre-flight database connectivity check.

Fixed by adding the `Microsoft.KeyVault` service endpoint to `snet-app` (`modules/network/main.tf`) and `virtual_network_subnet_ids = [var.subnet_app_id]` (conditional on VNet integration being enabled) to the Key Vault's `network_acls` (`modules/app/main.tf`), mirroring the existing `snet-data` pattern used for Postgres and Storage. Confirmed via `terraform apply` (clean plan: only the Key Vault ACL and subnet service-endpoint changes, plus the same pre-existing drift as before) followed by an App Service restart and a live `/health` check returning `200`.

This was diagnosed and fixed same-day, ahead of a live demo to the Marcellus Township supervisor.

---

## Session AQ — F-5C2: Help & Tutorial Screen (2026-06-23)

Goal: replace the greyed-out "Help & Tutorial" placeholder card on the home screen with a fully working Help screen.

`modules/help/index.jsx` and `modules/help/help.css` were created as a new self-contained module. The screen is a single scrollable page with role-aware sections: "For Every Crew Member" (seven accordion items covering the shift-start check flow, after-call logging, status colors, missed checks, missing/expired items, reporting repairs, and auto-save draft behavior) and "For Supervisors" (four accordion items — compliance dashboard overview, FAIL check triage, adding crew members, and supply room stock review — shown only when `canAccess(user, 'supervisor')` is true). A static Quick Reference grid lists every home screen button with its icon and one-sentence description, also role-filtered for supervisor-only cards. A "Show me the basics again" button and a matching header button launch the existing `Tutorial` component as a full-screen overlay; when dismissed, the user stays on the Help screen (the `onDone` callback just closes the overlay, does not navigate away, and does not clear `ems_tutorial_complete` from localStorage).

In `HomePage.jsx`: a lazy import for `HelpScreen` was added; a new `if (activeModule === 'help')` render block passes `onBack` and `user` props; the Help card was changed from a disabled placeholder (no button, "Coming in Phase 5C" badge) to a live card with a standard Open button and no `disabled={!selectedStation}` guard since help content is station-independent. The contextual per-wizard-step bottom sheet variant remains deferred (F-5C2 was delivering this full screen as its first-delivery scope).

No backend changes. No new tests required (static content, no logic paths). Backlog count: 14 post-launch engineering items, 16 total remaining.

---

## Session AP — LAUNCH-OPS1–4 Closure and Item-Edit 422 Fix (2026-06-23)

Goal: complete the first four operational launch tasks (priority-item configuration, physical stock counts for Unit 712 and its jump bag, and EMS team member onboarding) and resolve a bug surfaced while doing so.

While entering Unit 712's stock count, changing an item's check type from Functional (pass/fail) to Supply Count returned a 422 "Field required" error. Root cause: `PATCH /admin/items/{id}` validated its request body against `ItemCreate`, the same schema used for item creation, which requires `station_id` — a field that's set once at creation and never sent by the frontend on edit, since the item's station doesn't change. Every edit request was therefore failing Pydantic validation before the route handler ever ran. The fix introduces a dedicated `ItemUpdate` schema that omits `station_id` entirely; the item's station continues to be read from the existing database row server-side, never accepted from the client, consistent with the same client-trust boundary already established elsewhere in the codebase for server-derived identity fields. No frontend changes and no migration were required — this was a request-validation contract fix only. `pytest`, `ruff check`, and `black --check` were all confirmed green, the fix was deployed to Azure, and the edit (Functional → Supply Count) was re-tested live and confirmed working.

LAUNCH-OPS1 (priority-item configuration for Unit 712 — AED Battery, LUCAS Device, and on-board O2 PSI marked priority), LAUNCH-OPS3 (Unit 712 Jump Bag stock count), and LAUNCH-OPS4 (EMS team member roster added via Station Administration → Members → CSV import) were all completed without further engineering involvement. LAUNCH-OPS5 (chief's full shift-start walkthrough) and LAUNCH-OPS6 (volunteer walkthrough) remain open on the active backlog.

---

## Session AO — Pre-Deploy Correctness and Security Sweep (2026-06-23)

Goal: resolve every outstanding correctness and security finding before pushing the production deploy. Fifteen issues were identified and resolved across a single session.

On the backend, two route handlers in `admin_items.py` — `update_par_level` and `list_vehicle_compartments` — were missing `require_station_membership` calls, leaving them accessible to users at other stations. Both were corrected. A separate `db.commit()` call inside the par-level deactivate route was found to release the active SQLAlchemy savepoint prematurely, causing committed rows to persist across otherwise-isolated test runs; the commit was removed and the route's own transaction handling verified correct. The `PAR-B1` reactivation query was also found to be missing an `ORDER BY` clause, meaning the "reactivate the most recently deactivated row" intent was only satisfied by coincidence of insertion order; an explicit `ORDER BY deactivated_at DESC` was added.

On the frontend, three components were found to contain `<form>` elements in violation of the project's no-form-submit rule (form submit breaks the PWA); all were converted to `onClick`/`onChange` handlers. A stale closure in `ItemSearchCombobox` was causing searches to use the `stationId` value from the first render rather than the current one; the dependency array was corrected. The `deriveLocType` helper had two proposed implementations and the correct one (Option A, using `location_id` directly) was confirmed and locked in. A CSS utility class shared across modules was placed in a module-scoped file rather than `index.css`, causing it to silently disappear whenever that module was not loaded; it was moved to `index.css`. The `useApi` hook's error path was not exposing the error fields expected by callers, causing silent null-data states on API failure; the error shape was corrected.

A dead test file (`_par_level_fix.py`, a placeholder that had never been wired into the suite) was deleted. Test fixtures for par-level tests were updated to use per-test unique names to prevent leakage across committed rows. The full suite reached 530 backend tests passing with linting and formatting clean. The production deploy followed immediately after this session confirmed green.

---

## Session AN — ITM-7 + ITM-8: Multi-location Assign-from-Item and Launch Gate Closure (2026-06-22)

Goal: complete the two remaining pre-launch items. ITM-7 improves the item-assignment UX so that a single item can be assigned to several locations in one pass without navigating away. ITM-8 adds the missing frontend test coverage for the "Where" picker work from the prior session and formally closes the launch gate.

For ITM-7, `AddAssignmentForm` in `ItemAssignments.jsx` was updated so that a successful assignment no longer collapses the form. Instead, it shows an inline confirmation row ("✓ Assigned to [Vehicle] › [Compartment]") with two follow-up actions: "+ Assign to another location" (resets the form's Where picker and compartment selection while carrying the min/max values forward as defaults) and "Done" (closes the panel). The parent component's callback was split into two: one to refresh the assignments list in the background and one to close the panel, so the form can stay open during multi-location entry. A corresponding CSS pair (`.add-assignment-confirm` / `.add-assignment-confirm__msg`) using the `--color-status-pass` token was added to `admin.css`.

For ITM-8, a new `ItemAssignments.test.jsx` (9 tests) was added to `modules/admin/__tests__/`. The test file covers: assignment display rows showing `vehicle_number` for vehicle assignments and `location_label` for non-vehicle; the vehicle, jump bag, and supply room assignment paths each submitting the correct payload shape (vehicle\_id vs. location\_id, no cross-contamination); supply room auto-select behavior; the ITM-7 confirmation state (Done button appears, Assign button is gone, confirmation text contains vehicle number and compartment name); the "Assign to another location" reset (form returns to vehicle mode, min/max carried over verified by re-selecting vehicle + compartment); and the Done button closing the form. A `mockImplementation` strategy differentiating between the assignments list and compartments `useApi` calls by `typeof deps[0]` was used to avoid fragile call-count sequencing.

`ItemCatalog.test.jsx` was already at 15 tests from Session AK. Backend `test_item_station_scoping.py` was already at 14 tests from Session AJ. Frontend test count is 233 passing; backend test count is 498 passing (no new backend tests this session). All pre-launch gate items (ITM-1 through ITM-8) are now complete.

---

## Session AM — SEC-AL1/AL2/CLEANUP-AL1 Closure, Two Sibling `station` ReferenceErrors, a Compartment PATCH Bug, and core/auth.py Test Coverage (2026-06-22/23)

Goal: close out the three security and hygiene items carried forward from the prior incident-response session, then continue into VERIFY-AL1 verification — which surfaced a recurring frontend bug pattern across two sibling components, one unrelated backend bug, and one test-coverage gap worth closing before the next deploy.

**Security cleanup (SEC-AL1, SEC-AL2, CLEANUP-AL1):** the Postgres administrator password — generated by Terraform, stored to Key Vault, and flowing into the application's connection string and the App Service's settings — was rotated after being pasted in plaintext during the prior session's database-wipe procedure. Rotation was triggered by tainting the password generator resource and re-applying. The first rotation attempt broke the live site: every API call failed with what the browser reported as a CORS error, a misleading downstream symptom. The App Service log stream showed the real cause — the backend couldn't resolve its database hostname at startup, because the newly generated password happened to contain a literal `@` character, and the connection string interpolates the raw password directly into a `postgresql://user:password@host` URI with no escaping. This was a latent bug in the password generator's allowed special-character set, not a mistake in the rotation procedure — any rotation could eventually have rolled an `@` and hit the same failure. The fix excludes `@` (and other URI-meaningful characters) from the generator's special-character set, so the failure mode can't recur without a deliberate, documented change; a corrected password was generated, the App Service restarted, and the site confirmed working. The temporary Postgres firewall rule from the wipe procedure was removed directly via the Azure Portal. The orphaned Key Vault left over from an earlier mismatched Terraform apply was confirmed absent from both Terraform state and every App Service setting before being deleted via the Azure CLI.

**VehiclesScreen crash:** while performing VERIFY-AL1 (confirming the prior session's seed-gate fix actually rendered correctly in the live app), expanding any vehicle card with compartments threw a `ReferenceError: station is not defined`. Root cause: `VehicleAdminCard` passed `stationId={station.station_id}` into `CompartmentParLevels`, but the component only ever receives a `vehicle` prop — `station` was never in scope. The bug had shipped unnoticed because the only existing test coverage exercised the vehicle list itself, never an expanded card's compartment section. Fixed by swapping to `vehicle.station_id`, which was already proven in scope a few lines above in the same component's location-fetching call.

**Compartment rename 422:** a related but separate bug surfaced immediately after, this time in Station Supplies — renaming a shelf returned a 422 with a misleading "Field required" message even though the name field was filled in. Root cause: `PATCH /inventory/compartments/{id}` reused `CompartmentCreate` as its request schema, which requires `location_id` — a field the rename form never sends, since renaming isn't supposed to need it at all. The admin Vehicles screen's "Edit Compartment" form had masked this same defect for months by coincidentally always sending the full object. Fixed by introducing a dedicated `CompartmentUpdate` schema with every field `Optional`, following the same `model_fields_set` partial-update pattern already established by `StockLotUpdate` elsewhere in the same router; the route now only applies fields actually present in the request body. Eight regression tests were added directly pinning this behavior (name-only rename, unrelated-field updates leaving name untouched, no `location_id` required, duplicate-name conflict, self-rename not falsely conflicting, 404, and 403 for responders). The fix was lost to an unexplained file revert twice mid-session before a third, verified write held through to deploy — both the schema file's and the router's content were independently re-confirmed on disk immediately afterward and again at session close.

**Test coverage gap:** a coverage report showed `core/auth.py` at 44%, almost entirely the real Azure AD JWT validation path (`_validate_azure_token`) — every other test in the suite authenticates via the dev-mode fake `test-{role}` token path, so the production-grade signature, audience, issuer, expiry, and tenant-matching logic had zero automated coverage. A new `test_auth.py` was added: a session-scoped RS256 test keypair mints real, correctly-signed JWTs, with `_get_jwks_client` monkeypatched to hand back the test public key in place of a real network call to Azure AD. Twenty-five tests now cover valid-token resolution (including audience and user-id/email fallback variants), expired and not-yet-valid tokens, wrong audience, wrong issuer, missing audience claim, tenant-ID mismatch (and the intentional leniency when `tid` is absent entirely), unknown-role filtering, malformed and wrong-key-signed tokens, the `CurrentUser` helper methods, and the dev-mode fake-token fallthrough logic. The same session, an unrelated coverage distortion was found and corrected: `routers/admin.py` — the pre-split monolithic admin router superseded by `admin_items.py`/`admin_stations.py`/`admin_vehicles.py` back in Session X — was still sitting in the repo, never imported by `main.py`, reporting 0% coverage on 436 dead statements and dragging the project-wide total down by roughly nine points for no real reason. Confirmed fully unreferenced and staged for removal.

**PortableLocationsScreen crash (same-session follow-up):** after the first two fixes deployed and were confirmed live, the identical `ReferenceError: station is not defined` surfaced a second time — this time expanding a Jump Bag in Station Administration → Portable Locations. The root cause was the same pattern exactly: `ShelfManager`, a nested helper component analogous to `VehicleAdminCard`, passed `stationId={station.station_id}` into `CompartmentParLevels` despite only ever receiving `location` and `getToken` as props. Fixed with `location.station_id`, which the backend already populates on every `InventoryLocation` record. Before closing this out, the third sibling consumer of `CompartmentParLevels` — `StationSuppliesScreen` — was checked and confirmed clean: it calls `CompartmentParLevels` directly from the screen's own top-level render function, where `station` genuinely is a prop, with no intervening helper component to lose that scope. All three known consumers of `CompartmentParLevels` are now verified correct. The fix was confirmed via the full `npm test` + `npm run build` sequence, deployed, and confirmed live: Jump Bag compartments now expand without error.

The recurring nature of this bug — the same mistake made independently in two sibling components — was traced to a real test-coverage gap rather than developer error alone: no existing test for either screen ever rendered a card or shelf in its *expanded* state, only the collapsed list view, so neither instance could have been caught short of manual UI testing. A follow-up item (component tests covering expanded-state rendering for both screens) was added to the post-launch backlog rather than addressed in this session, to keep the fix-and-verify loop tight while the live site was in a partially-broken state.

All fixes from this session were confirmed working in the live app after their respective deploys: vehicle compartments expand without error, the Station Supplies rename saves correctly, and Jump Bag compartments expand without error.

---

## Session AL — Incident Response: Auth Outage and Seed Gate Logic Bug (2026-06-21)

An unplanned incident-response session, triggered while preparing for the next ITM backlog items. Three separate issues surfaced and were resolved: a backend deployment failure, a Terraform configuration drift problem, and a critical site-wide authentication outage.

The App Service had gone down after a deploy because an Alembic migration backfilled a default `station_id` of `0` for legacy rows and then added a foreign key to the stations table — the dev database had stale rows with no matching station, so the foreign key creation failed and the migration step aborted the container's startup script before the server process could start. This was resolved with a full database wipe and reseed, consistent with the project's "no production data exists yet" policy. A related configuration bug caused the dev environment to behave as if it were production, silently skipping seed logic on every dev deploy; the Terraform module's environment flag had been hardcoded rather than driven from the existing dev/prod toggle.

While preparing the fix for that issue, a `terraform plan` revealed that several Azure AD application settings had drifted from source — they had been changed by hand in the Azure portal over time and were never captured in Terraform. These included the sign-in audience setting (required for personal Microsoft accounts to authenticate), OAuth scope definitions, and the token version claim shape. All drifted settings were reconciled back into Terraform configuration after careful, human-reviewed plan iterations, since an uncontrolled apply would have reverted live-working authentication settings.

Applying that reconciliation caused a brief, critical, site-wide sign-in outage (AADSTS500011, "resource principal not found") because the Azure AD application's Identifier URI had been inadvertently cleared in an earlier revision of the Terraform change. This is required for Azure AD to resolve the API scope the frontend requests on every token call. It was restored using the Azure AD Terraform provider's documented workaround (a dedicated identifier-URI resource, since the value can't be set inline due to a self-referential dependency on the application's own client ID) and confirmed fixed live immediately after.

Separately, a long-standing seed-gate bug was found and fixed: the startup script used a row-count check to decide whether to seed the two real operational stations, but a second always-on seed pass (which creates a training station) meant the stations table was never empty after the first successful boot — permanently disabling the operational seed gate. The gate was changed to check for the two real stations by name instead, closing the race condition for good. While investigating, a related crash in the training-data seed script was also found and fixed: it had never been updated for the per-station item scoping introduced earlier and was inserting rows with a null station ID, failing silently into a startup warning. Several training-item names were also renamed to match the canonical item-catalog naming convention, and incorrect oxygen-tank pressure thresholds were corrected.

All affected stations were also renamed to drop an incorrect "Station 1" suffix — both are single-station townships, not the first of several locations.

The full test suite, linter, and formatter were confirmed green both before and after the fix set. The deploy was confirmed live with sign-in working. Visual confirmation that both real stations now appear correctly in the live app (and that training inventory populates with canonical names) was deferred to the next session. A handful of cleanup items were flagged for follow-up: rotating a database credential that had been exposed in plaintext during the wipe procedure, removing a temporary firewall rule added for direct database access, and removing a stray duplicate Key Vault resource.

---

## Session AK — ITM-6: Frontend Item Catalog Station Scoping (2026-06-21)

Goal: extend the Item Catalog and item-assignment UI to support per-station item scoping and let items be assigned to jump bags and the station supply room, not just vehicle compartments.

The catalog's API calls were updated to pass a station ID, matching the backend's now-required scoping (added in the prior session). The catalog UI's category filter chips were replaced with the catalog's six/seven new "cabinet group" labels, and item assignment gained a "Where" picker so an item can be assigned to a vehicle compartment, a jump bag compartment, or the station supply room, instead of only vehicles. Item search components across the admin and supply-room modules were threaded with the same station scoping so search results never cross station boundaries.

No backend changes were required this session — the prior session's API already supported both assignment payload shapes. Four new tests were added covering the new cabinet-group filtering behavior; all existing tests continued to pass unchanged.

---

## Session AJ — ITM-5: Backend Station Scoping for Item Endpoints (2026-06-21)

Goal: scope every item-related backend route to the caller's station, completing the architectural work needed before the frontend changes in the following session.

All eleven routes on the item catalog router were updated to require station membership before reading or mutating item data — non-members now get a 403, and Administrators bypass the check as expected. List and search endpoints gained a required station-ID query parameter. The previous global name-uniqueness constraint on items was replaced with a per-station constraint, so the same item name can now exist independently at different stations while remaining unique within any one station; barcode uniqueness remains global, since a physical barcode still corresponds to one product across the organization.

Fourteen new tests were added covering station-scoped listing, search, creation, and per-station name uniqueness, alongside fixes to a few pre-existing test fixtures that had been quietly relying on the old unscoped behavior. The full suite passed at 498 tests, with linting and formatting both clean.

---

## Session AI — ITM-4: Item Seed Rewrite with Per-Station Scoping (2026-06-20)

Goal: rewrite the database seed script around the deduplicated item catalog finalized in the architectural planning session, resolving the test failures introduced when item records first became station-scoped.

The seed script now builds each station's item catalog from a single canonical seed list of roughly 100 items, organized into seven cabinet-group categories, with the look-up/creation helper scoped to station and name to match the new per-station uniqueness constraint. Several previously duplicated, location-suffixed item names (multiple stethoscope variants, multiple gauze variants, two LUCAS device entries, and others) were merged into single canonical items per the project's confirmed merge rules — merge across locations, never across sizes. Oxygen tank pressure thresholds for the stretcher and jump-bag tanks were corrected to their proper smaller-tank range, distinct from the larger on-board tank.

Each station now seeds its own copy of the canonical catalog rather than sharing one global item list. A latent bug in the per-station unique-constraint migration was also found and fixed during this work: the original migration's approach to dropping the old global uniqueness constraint relied on SQLite schema introspection that silently failed to remove the constraint across repeated schema rewrites. It was replaced with an explicit raw-SQL table rebuild that reliably produces the intended schema. All affected integration tests were updated to match the new canonical naming and corrected thresholds.

---

## Session AH — ITM-3: Cabinet Grouping Field for Items (2026-06-20)

Goal: add a catalog-wide "cabinet group" classification to items, to support better organization in the Item Catalog UI without altering the underlying compartment structure used for physical inventory checks.

A new nullable field was added to the item model and corresponding schema, with a database migration to match. The field is purely an organizational label for catalog browsing — it has no effect on which physical compartment an item is assigned to, and the existing ambulance compartment seed data was left untouched. The field round-trips cleanly through existing item endpoints with no changes required at any existing call site.

---

## Session AG — ITM-1: Per-Station Item Scoping (2026-06-20)

Goal: make items station-scoped at the model and database level, addressing two related problems discovered during user-acceptance testing of the Item Catalog — items could not be assigned to jump bags or supply rooms from the UI, and the item catalog was globally shared, meaning supervisors at one station could inadvertently rename or retire another station's items.

A required station foreign key was added to the item model, and the global item-name uniqueness constraint was replaced with a per-station equivalent. A related data-isolation bug was found in the supply-catalog endpoint, which was missing a station filter entirely and could return items (and stock levels) belonging to a different station under certain conditions; this was fixed alongside the schema change. The test suite was updated throughout to create a station before creating any item, since item creation now requires a valid station reference.

This session intentionally left the seed script unchanged, so the full suite reported the seed-integrity tests as expected failures pending the seed rewrite completed in a later session.

---

## Session AF — Compliance Calendar Fixes, Par-Level Reactivation, and Audit Test Timezone Bug (2026-06-19)

Three user-acceptance-testing findings and one backend test-suite flake were resolved this session.

The Compliance Dashboard and calendar were showing retired vehicles in both the "today" list and the monthly grid; the vehicle-listing endpoint returns retired and active vehicles together unless explicitly filtered, and nothing downstream applied that filter. The calendar component was also missing jump bags from its monthly view and had no representation of the station supply room's count status at all; both were added, with the supply room intentionally limited to the monthly view rather than the weekly view to avoid wasted space at that cadence.

A second bug allowed "this item is already assigned to this compartment" errors when re-adding an item to a compartment after it had been previously removed. The underlying uniqueness constraint on par levels had no concept of an inactive row, so a soft-deleted assignment still occupied the slot. The fix reactivates the matching inactive row instead of attempting a new insert, preserving its original history.

The backend test suite had two intermittent failures in audit-log date-boundary tests. The first root cause was test pollution: because committed database rows are never rolled back within a test session, two tests asserting against the entire unfiltered audit log were picking up unrelated rows from earlier tests once the suite grew large enough; they were rescoped to data they create themselves. A second, distinct failure emerged afterward from a genuine timezone mismatch — the tests computed "tomorrow" using local wall-clock time, while audit timestamps are always written in UTC, so the two could disagree near a U.S. evening boundary. Tests were corrected to compute their date boundaries in UTC consistently with how the audit log itself is written.

A same-day follow-up after deploy found that the Station Supplies Count reminder was showing "no count on record" for a count that had, in fact, been completed the day before. The reminder had been wired to a date-range-limited endpoint that silently failed once the calendar fix widened its lookback window beyond that endpoint's server-side cap; it was switched to a location-scoped endpoint with no such limit, which is the more appropriate data source for "most recent check ever" regardless of how that need is later revisited.

The full test suite, linter, and formatter were confirmed green, and all fixes — including the same-day follow-up — were deployed and confirmed live.

---

## Changelog Archive — Sessions Z through AF (Consolidated Version History)

A compressed cross-reference of the version-history footer originally tracked in the active backlog file. The full session write-ups above remain authoritative for technical detail.

- **v2.07–v2.04:** Session AF — compliance calendar and par-level reactivation fixes, audit test timezone correction, full suite confirmed green and deployed.
- **v2.03–v2.02:** Session AE — member-management consolidation completed, verified, and deployed.
- **v2.01:** Recovery note for a missing-files incident caused by a tooling interruption; all files confirmed restored.
- **v2.00:** Session AD — retired-vehicle visibility fix completed.
- **v1.99:** Session AC — email alignment diagnostic completed.
- **v1.98:** Session AB — training station, dependency security patches, and Settings UI fixes completed. All pre-launch gates met at this point (later reopened for the item-scoping architectural work).
- **v1.97:** Help screen added.
- **v1.96–v1.95:** Session Z closed — member management and multi-role support, published to Azure.

---

## Session AE — Member Management Consolidation (2026-06-19)

Goal: resolve user-acceptance-testing feedback that Station Administration → Members and Settings → Team Members were two overlapping, confusing screens, and that removing a member from one of them threw a type-validation error.

Root cause: the frontend had two independent implementations of member management hitting the same backend routes. One was outdated and still sent a user's email address where the backend now expected an integer membership ID, a mismatch introduced when a prior session changed the underlying routes to support multiple roles per person as separate rows. The other implementation was already correct and more complete, supporting multi-role grouping, name edits, and CSV import. No backend changes were needed.

The two screens were consolidated into a single, correct implementation under Station Administration. The outdated module was retired, and shared CSS that had drifted into a module-specific stylesheet was moved to the shared stylesheet, consistent with the project's cross-module CSS convention. As a result, supervisors — who already had the necessary backend permissions — can now manage their own station's members directly, without needing Administrator access; only the previous UI split had been obscuring that capability. The fix was verified against the existing backend test suite (no backend changes were made) and the relevant frontend tests, then deployed and confirmed live.

---

## Session AD — Retired Vehicle Visibility Fix (2026-06-19)

Goal: fix a user-acceptance-testing finding where a retired vehicle continued to appear in the Admin vehicles list (with the out-of-service filter unchecked) and still offered a working "Return to Service" action.

Root cause: a vehicle's "active" flag and its "retired" timestamp are independent fields, and retiring a vehicle sets the active flag as a side effect rather than as the canonical signal. Several frontend screens were checking only the active flag and never the retirement timestamp directly, so retired-vehicle exclusion worked by coincidence rather than by design and didn't distinguish a permanently retired vehicle from a temporarily out-of-service one. The retirement endpoint itself was correct throughout — this was purely a frontend display and action-gating issue.

Four screens were corrected to check the retirement timestamp explicitly: the admin vehicles screen, the vehicle status screen and its vehicle card component, the home screen's unresolved-issue badge logic, and the check wizard's vehicle picker (the last of these as a defensive fix, since it happened to be safe already). New regression tests were added for the vehicle status card and a previously uncovered admin vehicles screen, which is how the bug had shipped unnoticed in the first place.

---

## Session AC — Email Alignment Diagnostic and Settings UI (2026-06-19)

Goal: close out the one remaining engineering item on the post-launch operational checklist — detecting station members whose stored email address doesn't look like a valid email, the standard symptom of someone typing a display name into that field during manual entry or CSV import.

Built as an on-demand administrator diagnostic rather than a startup-time check, since membership rows can be added or imported at any time after the app is already running. The new endpoint is read-only and never modifies data, with optional filtering by station and an option to include soft-deleted rows. A corresponding Settings UI was added allowing an administrator to run the check, review flagged members, choose other administrators or supervisors at the station as recipients (excluding anyone who is themselves flagged), and draft a notification email — opened via the administrator's own mail client, since no email-sending service is connected in this environment. The UI and its tests were later relocated as part of the broader member-management consolidation in a subsequent session, with no behavior change.

---

## Session AB — Training Station, Dependency Security Patches, and Settings Polish (2026-06-18)

Goal: add a permanent, visually distinct training environment for crew practice, resolve several dependency security advisories, and polish the Settings screen's styling.

A dedicated training station was added with two ambulances and two jump bags, carrying roughly a third of the real station's inventory but covering all six check types, including AED and powered-CPR-device priority checks, oxygen pressure measurement, and full-check-required compartments — a training run takes about five minutes versus twenty for the full real-station inventory. The training data is seeded by a standalone script that runs on every deploy, including production, so the training environment is automatically restored after any database reset without manual intervention; the main operational seed script's production safeguard was left untouched.

Several dependency security advisories were resolved by upgrading affected packages, with one follow-on compatibility fix where the upgrade introduced a deprecation warning resolved by switching HTTP client libraries. A database migration was also fixed to apply cleanly on both SQLite and PostgreSQL by removing an inline, unnamed foreign-key constraint that the batch-migration approach couldn't handle consistently across both databases. The Settings screen's CSS was cleaned up to align member-row spacing and heading styles with the rest of the admin UI.

---

## Session AA — Help Screen, Privacy Banner, and Launch Gate (2026-06-14)

Added an in-app Help screen with a quick-reference section, a feature guide, and a way to replay the onboarding tutorial. Added a persistent privacy/PII disclaimer banner to the login screen, visible at all times with no acknowledgement step required. Replaced the temporary test-station production safeguard with the dedicated training-station strategy completed in the following session.

---

## Session Z — Station Member Management and Azure Publish (2026-06-14)

Implemented three related member-management capabilities together: editing a member's display name (with the change propagating to all of that person's role rows), support for a single person holding multiple roles at a station as separate rows rather than one constrained row, and CSV bulk import of members with a downloadable template. A database migration replaced the old single-role-per-person uniqueness constraint with one that accounts for multiple roles. The role-switcher UI was updated to read from a new endpoint listing all of a user's available roles. Thirty-two new tests were added covering the new member-management behavior. The application was published to Azure for the first time this session.

---

## Session Y — UAT Complete, Test Suite Fix, and Open Questions Closed (2026-06-14)

All planned user-acceptance-testing scenarios passed, including responder, cross-role, edge-case, and multi-station coverage, plus cold-run walkthroughs of a full ambulance shift-start check, an after-call usage log, and a damaged-item scenario. Two backend test failures were fixed: an audit-log helper was passing a raw date object directly to the JSON serializer instead of a formatted string, and a par-level duplicate check had a gap for compartment-less (location-level) par levels that the database constraint alone didn't catch. All outstanding open questions from earlier sessions were resolved, including a decision to build a CSV export feature when the first compliance report becomes due, and a decision to handle permanent deletion of old soft-deleted checks via a scheduled cloud function rather than a manual process. The application was considered launch-ready at the close of this session.

---

## Session X — Code Quality Cleanup (2026-06-14)

A focused cleanup pass intended to bring the codebase to a portfolio-ready state ahead of launch. The check-date field's storage type was corrected from a string to a proper date type, with a accompanying migration. Two schema classes that had drifted into the wrong module were relocated to their correct schema files. A large, monolithic admin router file was split into three focused sub-routers by resource type. On the frontend, a check-wizard component's eighteen separate state variables were consolidated into a single reducer for maintainability. A par-level duplicate-check refinement narrowed an overly broad pre-check to only the case the database constraint couldn't catch on its own.

---

## Session W — Check History Endpoints and Usage Log Gap Closure (2026-06-13)

Added administrator-only permanent deletion of check records, supervisor-and-above listing and restoration of soft-deleted check records, and closed a gap where item usage logged after a check's last reading wasn't being reflected in subsequent readings. Also added location-level scoping to usage events, ensuring usage logged at a specific jump bag or supply room is queried correctly rather than bleeding across locations.

---

## Session V — UAT Continued (2026-06-12)

Continued user-acceptance testing, covering supervisor and administrator role scenarios. Several UI bugs were found and fixed: a progress indicator that mislabeled supply-room checks as vehicle checks, an incorrect subject label on a single-item check flow, a blank check date on the final wizard step, and a supply-room check that wasn't correctly updating the supply view after reconciliation. Several pieces of dead code identified during this pass were removed. A CI configuration change excluded development-only dependencies from the vulnerability audit gate so unrelated tooling advisories wouldn't block deployment. A par-level listing endpoint was fixed to correctly filter out inactive rows.

---

## Session U — Supervisor UAT and Damaged Items (2026-06-12)

User-acceptance testing from a supervisor's perspective surfaced two bugs: the "Log Items Used" screen showed no ambulances due to a stale status-field check that didn't match the vehicle model's actual active/retired fields, and the "No Change" check option was incorrectly bypassing inventory reconciliation even when items were genuinely short. A flaky backend test caused by a non-unique identifier in test data was also fixed. Added a damaged-items endpoint and corresponding UI panel for supervisors, along with a fix for a fail-status banner that persisted on a vehicle after its reported issue had already been repaired.

---

## Sessions A–T — Foundation Through Par Level Deactivation (2026-05-26 to 2026-06-11)

Full history available in git. Highlights from this foundational period include Azure AD JWT authentication, the three-role (Responder/Supervisor/Administrator) access model, the five-step check wizard flow, the compliance dashboard, the station supply room module, vehicle and item retirement support, security headers, and the CI/CD pipeline.

---

## Post-Session L — Frontend Test Infrastructure and Rate Limiting (2026-06-08/09)

Established frontend test infrastructure, including authentication mocking and an initial set of component test files. Added backend API rate limiting with a test-mode bypass, moved check-date computation to the server, and ensured the "performed by" field on checks is always derived from the authenticated user's identity rather than trusted from client input. Added linting to CI and a composite database index for query performance.
