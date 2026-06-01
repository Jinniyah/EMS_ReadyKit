# EMS ReadyKit — User Acceptance Testing (UAT-1)
# Session F Block 6
# Version: 1.0 | Date: 2026-05-30
# Status: DRAFT — to be reviewed with project owner before UAT execution

---

## How to use this document

Each section is a **role sheet** — work through it top to bottom in a single session.
Every test case is written as an observable outcome, not an instruction to dig into code.

**Pass / Fail / Block legend**
- ✅  PASS — outcome matched exactly
- ❌  FAIL — outcome did not match; note the deviation below the row
- ⛔  BLOCK — could not reach this step (upstream failure or missing setup)
- ➖  SKIP — consciously skipped with a reason noted

**Environment**: `https://lively-bush-0ed75ca10.7.azurestaticapps.net`

**Test accounts needed** (set up before starting):

| Account | Role | Member of |
|---------|------|-----------|
| uat-responder@yourdomain | Responder | Test Station A |
| uat-supervisor@yourdomain | Supervisor | Test Station A |
| uat-admin@yourdomain | Administrator | Test Station A, Test Station B |

**Test data needed before starting**:

| What | Detail |
|------|--------|
| Test Station A | Has 2+ active vehicles (AMB-401, AMB-402), at least 1 ALS |
| Test Station B | Has 1 active vehicle |
| AMB-401 compartments | At least 3: "PC 1 (Airway)", "PC 2 (Cardiac)", "Drug Bag" |
| Item catalog | At least 5 items across categories: NRB Mask, O2 Tubing, BVM, AED Battery OK, Morphine 10mg (CS) |
| Par levels | NRB Mask assigned to AMB-401 / PC 1, min 4, max 10 |
| Check history | AMB-401 has at least one submitted PASS check from today |
|               | AMB-402 has a FAIL check from today (missing NRB Masks) |
| Repair request | AMB-402 has one open URGENT repair request |

---

## Sheet 1 — Responder Role

Tester: _____________________________ Date: _____________ Result: PASS / FAIL

Sign in as **uat-responder@yourdomain**.

### 1.1  Home screen loads correctly

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-01 | Page loads after sign-in | Home screen visible with greeting "Good [morning/afternoon/evening], [first name]" | | |
| R-02 | Role shown below name | "Responder" | | |
| R-03 | Station band shows Test Station A | "📍 Test Station A" visible in colored band | | |
| R-04 | Module cards visible | "Daily Check", "Vehicle & Equipment Status", "Check History", "Help & Tutorial" | | |
| R-05 | Supervisor-only cards absent | No "Station Administration" card, no "Compliance Dashboard" card | | |

### 1.2  Station selection

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-06 | "Change" button appears (if assigned to 2+ stations) | Tap Change → station picker shows all assigned stations | | |
| R-07 | Selecting Test Station B switches context | Station band updates to "Test Station B" | | |
| R-08 | Switch back to Test Station A | Station band updates to "Test Station A" | | |
| R-09 | Station persists on reload | Reload the page — Test Station A still selected | | |

### 1.3  Daily Check Wizard — vehicle selection (Step 1)

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-10 | Tap "Start" on Daily Check | Check wizard opens at Step 1 | | |
| R-11 | Vehicles listed | AMB-401 and AMB-402 shown as selectable cards | | |
| R-12 | Inactive vehicles absent | Out-of-service vehicles do NOT appear | | |
| R-13 | ALS badge on ALS vehicle | AMB-401 shows "ALS" badge | | |
| R-14 | Tap AMB-402 (no check today) | **Last-check banner appears** below the card list | | |
| R-15 | Banner shows red styling | Red background, ⚠ icon, "Never checked" or shows days-ago count | | |
| R-16 | Tap AMB-401 (PASS check today) | Banner switches to green, shows "All clear" | | |
| R-17 | Banner loads with shimmer first | Brief grey skeleton visible before text appears | | |
| R-18 | "Continue to compartments →" button enabled | Button clickable after vehicle selected | | |
| R-19 | "Select a vehicle or bag to continue" shown when nothing selected | Button is greyed out | | |

### 1.4  Daily Check Wizard — compartments (Step 2)

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-20 | Tap AMB-401 and tap Continue | Compartment list shows PC 1 (Airway), PC 2 (Cardiac), Drug Bag | | |
| R-21 | Progress bar visible | Step indicator shows step 2 | | |
| R-22 | Compartment cards have status indicators | Unstarted compartments show "Not started" | | |
| R-23 | "Discard check" button visible | Button appears in header while in check | | |

### 1.5  Daily Check Wizard — items (Step 3)

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-24 | Tap "PC 1 (Airway)" | Item list opens with NRB Mask and any other assigned items | | |
| R-25 | Par level quantities visible | "Needs 4, have 4 (max 10)" or similar | | |
| R-26 | Enter a quantity below minimum | Item status shows warning/fail color | | |
| R-27 | Back to compartment list | Compartment card shows partial completion | | |
| R-28 | Auto-save indicator | "☁ Auto-saved" appears in header after a few seconds | | |

### 1.6  Daily Check Wizard — submit

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-29 | Complete all compartments and tap Review | Submit screen appears | | |
| R-30 | Overall status shown | PASS / FAIL / NEEDS_RESTOCK based on what was entered | | |
| R-31 | Tap "Submit" | Confirmation screen appears | | |
| R-32 | Submitted screen shows correct status | Same status as step 5 summary | | |
| R-33 | "Start New Check" resets wizard | Vehicle selection screen shown fresh | | |

### 1.7  Vehicle & Equipment Status

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-34 | Open "Vehicle & Equipment Status" | List of all vehicles at Test Station A visible | | |
| R-35 | AMB-402 shows "Unresolved Issue" badge on home card | ⚠ badge visible before opening the module | | |
| R-36 | Tap "File Repair" on AMB-401 | Repair form opens | | |
| R-37 | Submit a ROUTINE repair | Success; repair appears in AMB-401's request list | | |

### 1.8  Check History

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-38 | Open Check History | Today's checks listed | | |
| R-39 | Own check visible in history | Check responder just submitted appears | | |
| R-40 | Tap a check | Detail view opens with items and statuses | | |
| R-41 | Back → back to history list | No crash | | |

### 1.9  Discard draft

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-42 | Start a check, enter data, tap "Discard check" | Confirmation modal appears | | |
| R-43 | Tap "Yes, discard" | Home screen shown; draft banner NOT shown | | |
| R-44 | Reload page | Draft banner does not reappear | | |

### 1.10  Draft resume

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| R-45 | Start a check, enter some data, tap "← Home" | Home screen shown; **draft banner appears** | | |
| R-46 | Draft banner shows correct vehicle and date | "[Vehicle number] · [today's date]" | | |
| R-47 | Tap "Resume" | Check wizard reopens at compartment step | | |
| R-48 | Previously entered data still present | Items from earlier session pre-filled | | |

---

## Sheet 2 — Supervisor Role

Tester: _____________________________ Date: _____________ Result: PASS / FAIL

Sign in as **uat-supervisor@yourdomain**.

### 2.1  Home screen

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-01 | Module cards | "Daily Check", "Vehicle & Equipment Status", "Check History", "Station Administration", "Compliance Dashboard" all visible | | |
| S-02 | Role shown | "Supervisor" | | |

### 2.2  Compliance Dashboard — today's view

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-03 | Open Compliance Dashboard | Dashboard opens for Test Station A | | |
| S-04 | Summary tiles show correct counts | PASS: 1, FAIL: 1, Not Checked: 0 (or whatever matches test data) | | |
| S-05 | FAIL alert banner visible | "✗ 1 vehicle failed today's check" | | |
| S-06 | AMB-402 card shows FAIL styling | Red border, FAIL badge | | |
| S-07 | Tap filter tile "Failed" | Only AMB-402 shown in list | | |
| S-08 | Tap filter tile "All" | Both vehicles shown | | |
| S-09 | AMB-401 shows PASS styling | Green border | | |
| S-10 | Tap AMB-402 check | Check Detail Panel opens | | |

### 2.3  Check Detail Panel

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-11 | Failed items listed | NRB Mask shown with FAIL/MISSING badge | | |
| S-12 | "I Fixed This — Record Resolution" button visible | Button present | | |
| S-13 | Tap "I Fixed This" | Resolution form opens | | |
| S-14 | Submit a resolution note (at least 5 chars) | Check marked as resolved; green banner appears | | |
| S-15 | Back to dashboard | AMB-402 card no longer shows "Needs Ack" | | |
| S-16 | All items listed in the "All Items" section | Complete list visible | | |

### 2.4  Compliance Calendar — week view

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-17 | Scroll below vehicle cards to calendar section | Calendar visible | | |
| S-18 | Calendar shows current week (Mon–Sun) | Header shows correct date range | | |
| S-19 | AMB-401 row shows ✅ for today | Green check visible in today's cell | | |
| S-20 | AMB-402 row shows ❌ for today | Red cross visible | | |
| S-21 | Today's column has a filled circle on day number | Visual highlight present | | |
| S-22 | Past days with no check show red wash | Any unchecked day before today has reddish background | | |
| S-23 | Tap ❌ on AMB-402 today cell | Check Detail Panel opens for that check | | |
| S-24 | Back to dashboard → calendar still present | Calendar has not reset | | |

### 2.5  Compliance Calendar — month view

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-25 | Tap "Month" button | Calendar switches to full month | | |
| S-26 | Header shows "May 2026" (current month) | Correct month shown | | |
| S-27 | Vehicle picker chips appear (2+ vehicles) | AMB-401, AMB-402 chips visible | | |
| S-28 | Tap AMB-401 chip | Only AMB-401 row shown | | |
| S-29 | Tap AMB-401 chip again | All vehicles shown | | |
| S-30 | Tap "Week" button | Switches back to week view | | |

### 2.6  Station Administration — Members

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-31 | Open Station Administration | Admin home shows station + 3 nav cards | | |
| S-32 | Tap "Members" | Members list for Test Station A opens | | |
| S-33 | Current member list visible | At least supervisor account and responder account listed | | |
| S-34 | Role badge correct | Supervisor shows blue badge, Responder shows green | | |

### 2.7  Station Administration — Vehicles

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-35 | Back → tap "Vehicles" | Vehicles list opens | | |
| S-36 | AMB-401 and AMB-402 listed | Both vehicle cards shown | | |
| S-37 | Expand AMB-401 card | Color picker section and compartments section appear | | |
| S-38 | Select a color swatch on AMB-401 | Swatch rings and color dot appears in card header | | |
| S-39 | Reload page, navigate back to Vehicles | AMB-401 color dot still shows selected color | | |
| S-40 | Tap "×" (Inherit) swatch | Dot disappears from header | | |
| S-41 | Mark AMB-402 "Out of Service" | Reason form appears | | |
| S-42 | Enter a reason and confirm | AMB-402 shows red border and "Out of service" badge | | |
| S-43 | Show inactive vehicles toggle | AMB-402 still visible when toggle is on | | |
| S-44 | Return AMB-402 to service | "Return to Service" button → confirm → badge removed | | |

### 2.8  Station Administration — Item Catalog

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-45 | Back → tap "Item Catalog" | Catalog opens with item list | | |
| S-46 | Count shown in header | "(N items)" label present | | |
| S-47 | Search "NRB" | NRB Mask appears in results | | |
| S-48 | Clear search | All items return | | |
| S-49 | Filter chip "Medication" | Only medication items shown | | |
| S-50 | Filter chip "All" | All items return | | |
| S-51 | NRB Mask assignments toggle label | "Assigned to 1 compartment" (without expanding) | | |
| S-52 | Expand NRB Mask assignments | Row shows AMB-401 › PC 1 (Airway) · Min 4 · Max 10 | | |
| S-53 | Tap "Edit" on the assignment | Edit form opens pre-populated | | |
| S-54 | Change Max to 12 and save | Row updates to Max 12 | | |
| S-55 | Collapse and re-expand | Correct values still shown | | |
| S-56 | Tap "+ Assign to vehicle" | Add form opens | | |
| S-57 | Select AMB-401 from vehicle dropdown | Compartment dropdown appears | | |
| S-58 | Select "PC 2 (Cardiac)" | Quantity fields appear (default Min 1, Max 4) | | |
| S-59 | Tap "Assign" | New row appears in list; count increments | | |
| S-60 | Tap "✕" on the new assignment | Row disappears; count decrements | | |
| S-61 | Try assigning NRB Mask to AMB-401 / PC 1 again | 409 error shown "already assigned to this compartment" | | |
| S-62 | Tap "+ Add item" | Item creation form opens | | |
| S-63 | Create a new item ("UAT Test Item", Consumable, count, each) | Item appears in catalog | | |

### 2.9  Last-check banner (in wizard)

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| S-64 | Start a Daily Check | Step 1 shows vehicle selection | | |
| S-65 | Tap AMB-401 (PASS check today) | Green banner: "All clear · Checked today by [name]" | | |
| S-66 | Tap AMB-402 | Banner switches; shows FAIL status or amber/red | | |
| S-67 | No banner when no vehicle selected | Banner hidden before any card tapped | | |

---

## Sheet 3 — Administrator Role

Tester: _____________________________ Date: _____________ Result: PASS / FAIL

Sign in as **uat-admin@yourdomain**.

### 3.1  Home screen

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| A-01 | Role shown | "Administrator" | | |
| A-02 | All module cards visible | Same as Supervisor | | |
| A-03 | Assigned to 2 stations | Station picker shows both Test Station A and Test Station B | | |

### 3.2  Add Station

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| A-04 | Open Station Administration | Admin home shows 2 stations in the selector | | |
| A-05 | "+ Add Station" button visible at bottom | Low-prominence text button | | |
| A-06 | Tap "+ Add Station" | Inline form appears (no modal) | | |
| A-07 | Submit without Name | Validation error on Name field | | |
| A-08 | Submit without Address | Validation error on Address field | | |
| A-09 | Submit without Region | Validation error on Region field | | |
| A-10 | Submit with all required fields + a color | Success | | |
| A-11 | New station auto-selected | Admin home shows new station with nav cards | | |
| A-12 | Color bar on new station button reflects chosen color | Colored left bar shown | | |
| A-13 | Call sign field filled in | Call sign badge appears on station button | | |
| A-14 | Cancel button works | Form disappears, "+ Add Station" button returns | | |

### 3.3  Item deactivation (Administrator-only action)

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| A-15 | Open Item Catalog | Catalog loads | | |
| A-16 | Find "UAT Test Item" created by supervisor | Item visible | | |
| A-17 | Tap Edit on UAT Test Item | Edit form opens | | |
| A-18 | "Show inactive items" toggle visible | Toggle present (Admin only) | | |
| A-19 | Deactivate UAT Test Item (via edit form or deactivate button) | Item disappears from active list | | |
| A-20 | Enable "Show inactive items" | UAT Test Item reappears with "Inactive" badge | | |
| A-21 | Supervisor cannot see deactivate button | Sign in as supervisor — no deactivate control visible on item forms | | |

### 3.4  Multi-station check

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| A-22 | Switch to Test Station B in admin | Nav cards update for Station B | | |
| A-23 | Vehicles screen shows Station B's vehicles | Only Station B vehicles listed | | |
| A-24 | Item Catalog is not station-scoped | Same catalog shown regardless of station | | |
| A-25 | Switch back to Test Station A | Correct station shown; no data from B bleeds in | | |

### 3.5  Vehicle color persists in compliance calendar

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| A-26 | Set AMB-401 color to Navy (#1a3a5c) in Vehicles | Color dot appears in vehicle card header | | |
| A-27 | Open Compliance Dashboard | Calendar row for AMB-401 shows navy dot next to vehicle number | | |
| A-28 | AMB-402 has no color set | Dot shows station brand color (or brand default) | | |

---

## Sheet 4 — Cross-Role Scenarios

Tester: _____________________________ Date: _____________ Result: PASS / FAIL

### 4.1  Role enforcement

| # | What to check | Log in as | Expected | Result | Notes |
|---|---------------|-----------|----------|--------|-------|
| X-01 | Station Admin card not visible | Responder | Card absent | | |
| X-02 | Compliance Dashboard card not visible | Responder | Card absent | | |
| X-03 | Item deactivation not available | Supervisor | No deactivate button in edit form | | |
| X-04 | "Show inactive items" toggle absent | Supervisor | Toggle not present | | |
| X-05 | "+ Add Station" button absent | Supervisor | Button not present | | |

### 4.2  Data isolation

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| X-06 | Check submitted by Responder visible in Supervisor's dashboard | Responder submits check; Supervisor opens dashboard → check card visible | | |
| X-07 | Supervisor acknowledges a FAIL; Responder views history | Responder opens check history → acknowledgement note visible | | |
| X-08 | Color set by Supervisor on vehicle appears in Admin's vehicle list | Same color shown | | |

### 4.3  End-to-end check flow

Run this with both a Supervisor and a Responder collaborating:

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| X-09 | Responder submits a FAIL check on AMB-401 (short on NRB Masks) | Check appears in Supervisor's compliance dashboard | | |
| X-10 | Supervisor opens the FAIL check detail | Correct missing item listed | | |
| X-11 | Supervisor uses "I Fixed This" | Resolution recorded, check acknowledged | | |
| X-12 | Responder checks Check History | Check shows acknowledged status | | |
| X-13 | Supervisor's compliance calendar shows ❌ for today on AMB-401 | Calendar updates after refresh (↻ button) | | |
| X-14 | Responder starts next check on AMB-401 | Last-check banner shows amber (FAIL today) | | |

### 4.4  Draft resilience

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| X-15 | Start a check, enter partial data, close the browser tab entirely | Reopen tab → draft banner still present on home screen | | |
| X-16 | Resume draft → all previously entered data present | No data lost | | |
| X-17 | Two drafts open (two different vehicles) | Both draft banners shown on home screen | | |
| X-18 | Discard one draft | Only the other banner remains | | |

---

## Sheet 5 — Edge Cases

Tester: _____________________________ Date: _____________ Result: PASS / FAIL

### 5.1  Empty states

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| E-01 | Item with no assignments — toggle label | "No compartments assigned" (no need to expand) | | |
| E-02 | Station with no vehicles — check wizard | "No active vehicles or equipment at this station" | | |
| E-03 | Compliance dashboard with all vehicles checked/PASS | "✓ All vehicles checked — no issues today" alert | | |
| E-04 | Check history for a station with no checks | Empty state message shown | | |

### 5.2  Validation and boundary conditions

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| E-05 | Assign item: Max < Min | "Max must be ≥ min" error | | |
| E-06 | Assign item: Min = 0 | "Min must be at least 1" error | | |
| E-07 | Station name with only whitespace | Validation error "Field must not be blank" | | |
| E-08 | Vehicle color with invalid hex | Backend rejects with validation error | | |
| E-09 | Check date set 8 days ago (beyond 7-day window) | Date clamped to 7 days max | | |

### 5.3  Navigation and crash recovery

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| E-10 | Mid-check: tap "← Home" and then "Resume" | Returns to correct compartment step | | |
| E-11 | Back button in browser while in check wizard | Returns to home (draft preserved) | | |
| E-12 | Admin: open two item cards' assignment panels simultaneously | Both open independently; no interference | | |
| E-13 | Rapidly tap vehicle cards in Step 1 | Last-check banner shows correct vehicle each time (no stale data) | | |

### 5.4  Mobile / narrow screen

| # | What to check | Expected | Result | Notes |
|---|---------------|----------|--------|-------|
| E-14 | Home screen at 375px width | All cards fit; no horizontal scroll | | |
| E-15 | Check wizard at 375px | Step 1 vehicle cards stack cleanly | | |
| E-16 | Compliance calendar month view at 375px | Table scrolls horizontally; vehicle label stays pinned | | |
| E-17 | Last-check banner at 375px | Banner text does not overflow or clip | | |
| E-18 | Color picker (12 swatches) at 375px | Swatches wrap gracefully; none cut off | | |

---

## Sign-off

| Role | Tester name | Date | Pass / Fail | Notes |
|------|-------------|------|-------------|-------|
| Responder | | | | |
| Supervisor | | | | |
| Administrator | | | | |
| Cross-role | | | | |
| Edge cases | | | | |

**Overall UAT result**: PASS / FAIL / CONDITIONAL PASS

**Conditional pass conditions** (if applicable):
-
-
-

**Known deviations acceptable for launch**:
-
-

**Blockers that must be resolved before launch**:
-
-

---

*Document version 1.0 — EMS ReadyKit Session F Block 6*
*Next revision: after UAT execution, update with actual results and tester sign-offs.*
