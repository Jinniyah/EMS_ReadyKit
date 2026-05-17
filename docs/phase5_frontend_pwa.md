# EMS ReadyKit — Phase 5: Frontend PWA
# Document version: 1.0
# Status: In Planning / Not Yet Started
# Last updated: 2026-05-15

---

## 1. Executive Summary

Phase 5 will deliver a Progressive Web App (PWA) enabling EMS crews and
supervisors to perform daily inventory checks on a phone or tablet, replacing
the paper Jan-Care inventory form. The application is designed for users aged
60+ who may have limited technology comfort. It follows a wizard-based workflow
(select vehicle → select compartment → count items → review and submit) with
offline-first local draft saving, explicit identity verification on every screen,
and a modular architecture that isolates failures to individual features.

This document captures the full requirements, UX decisions, design gaps identified
through role-based walkthroughs, technical architecture, and phased build order.

---

## 2. Objectives

| Objective | Description |
|-----------|-------------|
| Replace paper form | Digital equivalent of the Jan-Care paper inventory sheet |
| Mobile-first UX | Phone and tablet optimized; 60+ user accessibility standards |
| Offline resilience | localStorage draft saves on every interaction; submit only on completion |
| Identity on every screen | Logged-in user visible at all times; submission cryptographically bound to JWT |
| Modular architecture | Each feature is an isolated module; a broken module cannot crash the app |
| Supervisor compliance tooling | Calendar view, check detail, print for legal hold |
| Help and onboarding | First-run tutorial, contextual help, searchable FAQ |

---

## 3. Scope

### In scope — Phase 5

#### Module 1: Check Wizard (all roles)
- Step 1: vehicle selection, check date editor (±7 days), second crew picker
- Step 2: compartment list with status badges and item counts
- Step 3: item counting with validate button, expiry display, expiry override, per-item notes, CS badge
- Step 4: review and submit with identity confirmation and repair flag
- Submitted confirmation screen with check reference number
- Draft save/resume/discard flow via localStorage
- Incomplete compartment warning before submit

#### Module 2: Item Management (Responder → Supervisor notification; Supervisor/Administrator → direct)
- Request item addition (Responder: goes to supervisor; Supervisor+: direct)
- Item removal with mandatory documented reason
- Item catalog search

#### Module 3: Vehicle Status (Supervisor, Administrator)
- Mark vehicle inactive with reason and ETA
- Reactivate vehicle
- Repair request (all roles) with severity and description

#### Module 4: Supervisor Dashboard (Supervisor, Administrator)
- Landing page with today's compliance summary and active alerts
- Monthly compliance calendar (color-coded per vehicle per day)
- Check detail view with all line items, lot numbers, expiry dates
- Print layout with chain of custody header
- Supervisor acknowledgement and corrective action on FAIL checks

#### Module 5: User Management (Supervisor → Administrator notification)
- Request new user with role, station, start date
- Administrator receives notification; manually provisions Azure AD group membership

#### Module 6: Feedback (all roles)
- Floating feedback button on all screens
- Bug report, enhancement request, general feedback form
- Severity selector for bugs

#### Module 8: Supply Room Resupply (all roles — write varies)
See dedicated section below.

#### Module 9: Role Switcher (Supervisor, Administrator)
See dedicated section below.

#### Shared infrastructure
- MSAL authentication with Azure AD
- UserPill component on every screen (initials, name, role, sign out)
- ErrorBoundary wrapper on every module
- Loading and error states on all API calls
- First-run tutorial (8 steps, replayable)
- Contextual "?" help on every wizard step
- Searchable FAQ (crew and supervisor sections)

### Out of scope — Phase 5 (Phase 6 backlog)
- Supervisor expiry date correction (PUT /inventory/lots/{id})
- Vehicle active/inactive API endpoint (PATCH /api/v1/vehicles/{id})
- Repair request API endpoint and data model
- Date-range compliance query (calendar view API)
- Notifications API
- Station user list API
- Feedback API
- User request API
- Supervisor acknowledgement API fields

---

## 4. Accessibility and Usability Requirements

These requirements are mandatory, not aspirational. The primary user population
includes crew members aged 60+ with limited technology comfort.

| Requirement | Specification |
|-------------|--------------|
| Body font size | 18px minimum |
| Item name font size | 22px minimum |
| Counter value font size | 24px minimum |
| Tap target size | 48×48px minimum on all interactive elements |
| Contrast | Dark text on white; never gray-on-gray |
| Status communication | Color + text label always used together (never color alone) |
| Navigation | All actions are visible buttons; no hidden gestures, swipes, or long-press required |
| Loading states | Spinner or skeleton on all API calls; never blank screen |
| Error states | Plain English message + "Try again" button; never raw error or stack trace |
| Confirmation dialogs | Required before: discard draft, submit with flags, remove item, mark vehicle inactive |
| Print | Clean print stylesheet; all nav chrome hidden; chain of custody header included |

---

## 5. UX Gaps Identified — Role Walkthroughs

The following gaps were identified through structured walkthroughs from the
perspective of an EMT (Responder) and a Supervisor. All gaps are incorporated
into the design above.

### Must-have before launch

| # | Gap | Resolution |
|---|-----|------------|
| 1 | Station-filtered vehicle list | Responders see only their station's vehicles; supervisors see all with station switcher |
| 2 | "Last checked today" on vehicle cards | Cards show check time and status from today's completed check if any |
| 3 | Per-line-item notes field | Each item row has an optional [note] icon expanding a text field |
| 4 | Controlled substance special flow | CS items show red lock badge; require second crew; compartment header warning |
| 5 | Incomplete compartment warning | Blocking modal listing unchecked compartments before submit |
| 6 | Supervisor landing dashboard | Supervisors land on summary dashboard, not raw calendar |
| 7 | Supervisor acknowledgement + corrective action | FAIL checks require acknowledged_by, reviewed_at, corrective_action (Phase 6 backend) |

### Important — build shortly after launch

| # | Gap | Resolution |
|---|-----|------------|
| 8 | "Jump to unvalidated" button | Sticky button scrolls to first unchecked item when compartment has 10+ items |
| 9 | Expired item replacement prompt | After validating EXPIRED: "Was it replaced?" flow with new lot entry or reason |
| 10 | Multiple checks per day in calendar | Worst-case status shown; "2 checks" badge; tap shows both |
| 11 | Repair request status tracking | Filed → Acknowledged → In Progress → Resolved lifecycle |
| 12 | Check reference number on confirmation | "Check #4271 recorded" prominently on submitted screen |
| 13 | Item count on compartment cards | "Compartment #7 · 14 items" so medic knows duration |
| 14 | Chain of custody header on print | Document ID, generated by, timestamp, signature lines |

### Nice to have

| # | Gap | Resolution |
|---|-----|------------|
| 15 | Partial/opened lot flag | Optional "opened" toggle for partially used vials |
| 16 | Time remaining estimate on Step 4 | "~6 minutes remaining" based on item count |
| 17 | Suspend/reactivate individual users | Active flag on user record (Phase 6) |
| 18 | "Who is on shift" for second crew picker | Show recently logged-in users at top of list |
| 19 | Calendar filter by issue type | Filter calendar by FAIL, SHORT, or missed checks |

---

## 5b. EMS Field UX Review — Speed and Accuracy Findings
# Reviewed 2026-05-15 through the lens of a tired medic with 12 minutes
# before shift handover.

### 🔴 Critical — will cause real problems in the field

**1. The wizard has too many navigations for tired hands**
Four steps plus confirmation = 5 screen transitions before anything is
recorded. For a medic returning to their usual truck, Step 1 (vehicle
selection) is unnecessary — they always check the same truck. Resolution:
- Home screen defaults to a "Continue [vehicle]" card when a draft exists
- Persistent overall progress bar on every screen (not just per-compartment)
- Skip vehicle selection entirely on resume

**2. Two taps per item to validate is too many**
Current flow: enter count (+/−) → tap separate checkmark = 2 actions per
item minimum. For 15-item compartments: 30+ extra taps. Cold hands make
this error-prone. Resolution:
- The checkmark validate button fires after count is non-zero on first
  interaction with that row — one deliberate tap to confirm
- "All present" single-tap button for items the medic can see at a glance
  are fully stocked (sets found = need and validates in one tap)

**3. +/− counter unusable for high-quantity items**
"10 shoe covers" requires 10 taps of +. Unacceptable in the field.
Resolution:
- Tap the count value itself → numeric keypad appears (large digits, green
  confirm button)
- +/− remains for fine adjustment (was 10, used 1, now 9)
- Keypad shows item name and Need quantity for context

**4. No whole-truck progress indicator**
The medic needs to know "where am I?" at a glance without navigating.
"4 of 8 compartments done · 47 items checked" should be visible on every
screen as a persistent progress bar + fraction, not just on Step 2.

**5. Check handoff to another crew member is not supported**
If a medic is toned out mid-check, another crew member must be able to
continue. Current design only saves a draft — it does not handle the
accountability question: whose name goes on the record?
Resolution:
- When a second user opens an in-progress draft, show a handoff screen:
  "Jane started this check. You are completing it. Both names will appear
  on the record."
- Final record stores: started_by (Jane), completed_by (Mark)
- API change: add started_by field to DailyInventoryCheck (Phase 6)

**6. No physical compartment reference**
"Compartment #7" is meaningless without spatial context. Medics walk around
the truck in a specific order. Resolution:
- Each compartment card shows a brief location descriptor:
  "Left rear · driver side" or "Cab overhead"
- Supervisor configures this description when setting up compartments
- Compartment list order (sort_order) maps to physical walk-around sequence

### 🟡 Significant — will slow people down or cause errors

**7. Compartment-to-compartment navigation requires back-navigation**
Current: finish compartment → Save → back to Step 2 list → tap next
compartment → Step 3. That's 3 taps between compartments.
Resolution:
- Left/right chevron navigation between compartments within the item
  counting screen
- Compartment list is still accessible but is not a mandatory waypoint

**8. No "all present" shortcut**
Most items most days are fully stocked. Forcing the medic to tap + N times
for every item is unnecessary friction.
Resolution:
- "All [N] present" button below each item row (not just at compartment
  level) sets found = need + validates in one tap
- Hidden after validation to reduce visual noise

**9. Expiry override requires too many steps**
Tapping [?] → panel opens → enter date → confirm = 4 steps.
Resolution:
- Tap the expiry date text itself to enter edit mode inline
- Date input appears directly; tap outside to cancel

**10. No "safe to leave" affordance**
When the radio goes off, the medic needs to know they can stop in under
2 seconds without losing work. No explicit confirmation exists.
Resolution:
- Persistent "Auto-saved" indicator (cloud icon + "Saved") in the top-right
  corner of every screen during an active check
- On app close/sleep, the last save timestamp is shown on resume: "Saved
  today at 05:48am"

**11. No caller/spotter mode for two-person checks**
Two medics often check together: one calls items, one records. The current
design requires the recorder to read item names from a phone while the caller
looks in the compartment.
Resolution:
- "Caller view" button on compartment screen
- Switches to large-text display: item name (32px), Need quantity (48px),
  status indicator — designed to be read at arm's length by the person
  looking in the compartment
- Recorder keeps the normal counting view on their device

**12. Mobile keyboard scroll destruction**
When a notes field is tapped, the keyboard appears and scrolls the item
row out of view — a known mobile UX failure.
Resolution:
- Notes field uses `scrollIntoView({behavior:'smooth', block:'center'})`
  after keyboard appears
- Item row stays anchored above the keyboard
- Notes field limited to 150 chars for item-level notes (shorter =
  less keyboard time)

### 🟢 Polish — real improvement to efficiency and accuracy

**13. No haptic feedback**
Visual-only feedback is insufficient during rushed, physical work.
Resolution:
- `navigator.vibrate(40)` on validate (short, confirms action)
- `navigator.vibrate([80,40,80])` on FAIL detection (distinctive —
  something needs attention)
- No vibration on OK status (silent confirmation)

**14. Confirmation screen doesn't feel final**
"Check #4271 recorded" is informational. EMS culture values sign-off
moments — the mental closing of a task.
Resolution:
- Large green checkmark, "Unit 401 is ready" as the primary message
- Check number displayed large and copyable
- "Truck is cleared for service" language (mirrors real EMS workflow)
- Timestamp: "Submitted 05:58am · Jane Doe + Mark Johnson"

**15. Status colors lose contrast in bright sunlight**
Light green/amber/red on white (the 50-stop ramps) are readable indoors
but wash out at noon in direct sunlight — exactly when outdoor checks happen.
Resolution:
- Use 200-stop fills (C0DD97, FAC775, F09595) instead of 50-stop fills
  for item row backgrounds
- Count value background uses the 400-stop (saturated) for maximum
  contrast in ambient light
- Validate button uses 600-stop background (darkest readable with white icon)

**16. No network status — medic doesn't know if submit worked**
Spotty signal in station garages is common. The app should not silently
fail or silently succeed.
Resolution:
- Two-state submit: "Saved to device" → "Submitted to server ✓"
- If network is unavailable at submit: queue locally, show "Waiting for
  signal — will submit automatically"
- On reconnect: auto-submit + push notification "Unit 401 check submitted"

**17. Feedback button is a distraction during a check**
A floating feedback button on every screen adds an accidental-tap risk
during the check workflow.
Resolution:
- Feedback button is hidden during active check wizard (Steps 1–4)
- Feedback accessible from: home screen, submitted confirmation screen,
  Help menu only
- During a check, only the ? contextual help button is visible

---

## 6. Validate Button Design

The validate button is the primary mechanism ensuring every item is explicitly
checked. Its behavior:

1. Every item row starts with a light red background and an unfilled checkmark icon
2. Medic enters the quantity found using +/− buttons
3. Medic taps the checkmark button to confirm they physically verified the item
4. System computes status and updates the row:
   - OK → light green background, filled green checkmark
   - SHORT → light amber background, filled amber checkmark
   - MISSING → light red background, filled red X
   - EXPIRED → light red background + EXPIRED badge
5. "Save compartment" is disabled until all items are validated
6. Counter shows "3 items not yet checked" throughout

The validate button solves the problem that, unlike paper, a digital form
allows skipping items without any physical evidence. Every item must be
explicitly acknowledged.

---

## 7. Date Editing Design

Default: today's date. Editable on Step 1.

- Shows as: "Check date: Tuesday, May 13, 2026  [Edit]"
- [Edit] opens native HTML `<input type="date">` — large, works on all phones
- Clamped: cannot be in the future; cannot be more than 7 days ago (configurable)
- Persists in localStorage draft
- No backend changes required (`check_date` field already accepts any YYYY-MM-DD)

---

## 8. Expiry Date Override Design

When the date on the physical package differs from the system record:

1. Medic taps [?] next to the expiry date
2. Inline panel opens:
   ```
   System shows: Mar 15, 2027
   Date on box:  [date input]
   [Use box date]  [Cancel]
   ```
3. If accepted: row re-evaluates EXPIRED status; override recorded in notes:
   `"Medic reported lot expiry as 2026-08-01 (system: 2026-06-01)"`
4. System uses conservative (earlier) date for EXPIRED determination
5. Supervisor corrects the lot record separately (Phase 6 backend)

---

## 9. Second Crew Member Design

- Optional — not required by default (configurable per station policy)
- Appears on Step 1 below the date selector
- Label: "Second crew member (optional)" with [Add] button
- [Add] opens searchable dropdown of active users at station
- Selected name shows with X to remove
- Required if any CS items are present in the vehicle being checked
- Stored in draft and submitted in `check.notes`:
  `"Second crew: Jane Smith (user_id: 42)"`
- Shown on Step 4 review, submitted confirmation, and printed record

---

## 10. localStorage Draft Format

```json
{
  "vehicle_id": 1,
  "station_id": 1,
  "check_date": "2026-05-13",
  "saved_at": "2026-05-13T09:35:00Z",
  "second_crew": "Jane Smith",
  "overall_notes": "Truck restocked after morning run.",
  "repair_needed": false,
  "repair_notes": "",
  "compartments": {
    "12": {
      "compartment_id": 12,
      "name": "Drug Bag",
      "status": "flagged",
      "compartment_notes": "Epi restocked mid-shift.",
      "line_items": [
        {
          "item_id": 5,
          "lot_id": 3,
          "quantity_needed": 2,
          "quantity_found": 2,
          "validated": true,
          "status": "EXPIRED",
          "notes": "Medic reported lot expiry as 2026-08-01 (system: 2026-06-01)"
        }
      ]
    }
  }
}
```

Draft key format: `ems_draft_{vehicle_id}_{check_date}`
Draft deleted from localStorage after successful submit.

---

## 11. Supervisor Compliance Calendar

Monthly grid view — one column per active vehicle, one row per day.

| Cell state | Color | Meaning |
|------------|-------|---------|
| Completed — PASS | Light green | Check done, all items OK |
| Completed — NEEDS_RESTOCK | Light amber | Check done, some SHORT items |
| Completed — FAIL | Light red | Check done, MISSING or EXPIRED items |
| Not completed | Dark red | No check submitted for this vehicle today |
| Vehicle inactive | Gray stripe | No check required (vehicle out of service) |
| Multiple checks | Worst-case + "2" badge | Day shift + night shift both checked |

- "This month" summary above calendar: "23 of 28 required checks completed"
- Export button: CSV download of month summary
- Tap any cell → opens check detail for that vehicle and date

---

## 12. Print Layout Requirements

The printed check record must be legally defensible and include:

- Document header: "EMS ReadyKit — Official Inventory Record"
- Document ID (check_id)
- Generated by: [name] at [timestamp] (logged-in supervisor)
- Statement: "This record was generated from the EMS ReadyKit system. Record ID: {check_id}. Do not alter."
- Vehicle, station, check date
- Performed by, second crew member
- All compartments and line items: item name, Need, Have, status, lot number, expiry date, notes
- Any overall check notes
- Signature lines: Performed by ___ / Second crew ___ / Reviewed by ___
- No navigation chrome, no color backgrounds (print-safe)

---

## 13. Help System

Three layers, all content managed in `src/modules/help/content.js`:

### First-run tutorial (8 steps)
Shown automatically on first login (localStorage flag: `ems_tutorial_complete`).
Replayable from Help menu. Skip button available. Steps cover: welcome,
vehicle selection, compartments, item counting, expiry dates, CS items,
review and submit, completion.

### Contextual screen help
Triggered by "?" button on each wizard step. Opens as bottom sheet
(slides up, dismisses on outside tap). Plain English, no jargon.
Content keyed by screen constant (SCREEN_VEHICLE, SCREEN_COMPARTMENT, etc.).

### FAQ
Searchable, client-side filter. Two sections: crew members and supervisors.
Covers 15 common questions including: starting a check, color meanings,
draft recovery, expired items, validate button, expiry discrepancies, reverting,
adding items, vehicle issues, backdating, supervisor compliance, legal print,
FAIL check handling, vehicle inactive, adding users.

---

## 14. API Requirements

### Available now (Phases 2–4)

| Action | Endpoint |
|--------|----------|
| Load vehicles | GET /api/v1/stations/{id}/vehicles |
| Load compartments | GET /api/v1/inventory/locations/{id}/compartments |
| Load par levels | GET /api/v1/inventory/locations/{id}/par-levels |
| Load stock lots | GET /api/v1/inventory/locations/{id}/stock |
| Submit check | POST /api/v1/checks/daily |
| Check detail | GET /api/v1/checks/daily/{id} |
| Vehicle checks | GET /api/v1/checks/daily/vehicle/{id} |
| Add item to catalog | POST /api/v1/items |
| Add par level | POST /api/v1/inventory/par-levels |

### Required in Phase 6 (not yet built)

| Action | Endpoint | Priority |
|--------|----------|----------|
| Mark vehicle inactive | PATCH /api/v1/vehicles/{id} | High |
| Repair request | POST /api/v1/vehicles/{id}/repair-requests | High |
| Compliance calendar | GET /api/v1/checks/daily/station/{id}?from=&to= | High |
| Station user list | GET /api/v1/stations/{id}/users | Medium |
| User addition request | POST /api/v1/admin/user-requests | Medium |
| Feedback submission | POST /api/v1/feedback | Medium |
| Notifications | GET /api/v1/notifications | Medium |
| Lot expiry correction | PUT /api/v1/inventory/lots/{id} | Medium |
| Supervisor acknowledgement | PATCH /api/v1/checks/daily/{id}/acknowledge | High |
| Par level deactivation | PATCH /api/v1/inventory/par-levels/{id} | Medium |

---

## 15. File Structure

```
app/frontend/
  public/
    index.html
    manifest.json
  src/
    main.jsx
    App.jsx
    shared/
      api/client.js
      components/
        UserPill.jsx
        StatusBadge.jsx
        ErrorBoundary.jsx
        Modal.jsx
        Spinner.jsx
        NotificationBell.jsx
      hooks/
        useAuth.jsx
        useDraft.js
        useApi.js
      utils/
        statusCalc.js
        dateHelpers.js
        roleGuard.js
    modules/
      check-wizard/
      item-management/
      vehicle-status/
      supervisor-dashboard/
      user-management/
      feedback/
      help/
        content.js          ← single source of truth for all help text
        Tutorial.jsx
        FAQ.jsx
        ContextHelp.jsx
```

---

## 16. Build Order

### Phase 5A — Foundation
1. `shared/api/client.js` + `shared/hooks/useAuth.jsx`
2. `shared/components/ErrorBoundary.jsx`
3. `shared/utils/statusCalc.js` + `dateHelpers.js`
4. `shared/hooks/useDraft.js`
5. `shared/components/UserPill.jsx`

### Phase 5B — Check wizard
6. Step1Vehicle + VehicleCard + DatePicker + SecondCrewPicker
7. Step2Compartments + CompartmentCard
8. Step3Items + ItemRow + ValidateButton + ExpiryOverride + CompartmentNotes
9. Step4Review + OverallNotes + RepairFlag
10. Submitted screen
11. DraftBanner — resume/discard flow

### Phase 5C — Help system
12. Tutorial (8 steps)
13. FAQ (searchable)
14. Contextual screen help

### Phase 5D — Item management module
15. ItemCatalogSearch + AddItemForm
16. RemoveItemConfirm

### Phase 5E — Vehicle status module
17. RepairRequestForm (all roles)
18. InactiveToggle (Supervisor+ — requires Phase 6 endpoint)

### Phase 5F — Supervisor dashboard module
19. Supervisor landing dashboard
20. ComplianceCalendar + CalendarCell
21. CheckDetail + PrintableCheck
22. NotificationList

### Phase 5G — Supporting modules
23. Feedback module (form + floating button)
24. User management module (user request form)

### Phase 5H — Infrastructure
25. Terraform frontend module (Azure Static Web Apps)
26. GitHub Actions frontend build + deploy job
27. CORS config in API app settings
28. MSAL redirect URI in Azure AD App Registration

---

## 17. Infrastructure Changes Required

### Azure Static Web Apps
New Terraform module: `iac/Terraform/modules/frontend/`

```hcl
resource "azurerm_static_web_app" "frontend" {
  name                = "stapp-ems-readykit-dev"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = "Free"
  sku_size            = "Free"
}
```

### CORS
Add Static Web App URL to `WEBSITES_CORS_ALLOWED_ORIGINS` in App Service
app settings via the `app` Terraform module.

### Azure AD App Registration
Register Static Web App URL as an allowed redirect URI in the App Registration
(SPA redirect URI). Required for MSAL token acquisition.

---

## 18. Known Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Phase 6 endpoints not ready when frontend module is built | Build UI components against mock data; connect to real API when endpoints are deployed |
| MSAL token acquisition complexity on mobile | Use `@azure/msal-react` with popup flow; fallback to redirect on browsers without popup support |
| localStorage cleared by OS (low storage) | Show "storage warning" banner if available space below threshold; never silently lose data |
| App not added to home screen by users | Prompt to "Add to Home Screen" on second login; show benefit (offline access, full-screen mode) |
| Older users resisting digital change | Tutorial + FAQ + in-app feedback loop; paper form remains available during transition period |

---

## 19. Phase Dependencies

| Dependency | Direction |
|------------|-----------|
| Phase 1 | Requires: Azure infrastructure, App Service, Azure AD |
| Phase 2 | Requires: All API endpoints |
| Phase 3 | Requires: Authentication infrastructure (Azure AD App Registration, MSAL) |
| Phase 4 | Requires: Compartments, line items, expiration tracking endpoints |
| Phase 6 | Provides: 10 additional backend endpoints that complete supervisor, management, and export modules |

---

## 20. Known Risks and Mitigations (Data Export)

| Risk | Mitigation |
|------|------------|
| Large exports timeout browser | Cap at 365 days; chunk requests for >5,000 records |
| Sensitive data in CSV (names, notes) | Export is role-gated; Supervisor sees own station only; remind users CSVs are unencrypted |
| Date range filter not yet on audit endpoint | Build export UI with placeholder; connect when Phase 6 endpoint is deployed |
| User exports wrong date range | Default to last 30 days; filename includes date range for verification |
| CSV encoding issues in Excel | Force UTF-8 BOM on download so Excel opens correctly without re-encoding |

---

| CSV encoding issues in Excel | Force UTF-8 BOM on download so Excel opens correctly without re-encoding |

---

## Module 8: Supply Room Resupply Workflow

### Background
When a vehicle item is SHORT or MISSING during a daily check, the crew member
typically walks to the station supply room, retrieves the needed stock, and
restocks the truck before submitting the check. If the supply room itself is
running low, the supervisor must be notified so a reorder can be placed.

This workflow was not in the original design. It is a critical operational
gap — without it the system has no way to record stock movement, and supply
room depletion goes undetected until it reaches zero.

### Trigger
During Step 3 (item counting), when a medic enters a quantity_found below
quantity_needed for any item, a "Restock from supply room" button appears
below the item row alongside the existing "All present" and notes options.

### Flow
1. Medic taps "Restock from supply room" on a SHORT or MISSING item row
2. App queries supply room stock for that item:
   - Shows: "Supply room has 8 · Bin B3 · Exp Mar 2027"
   - If supply room has none: "Supply room is empty for this item — notify supervisor"
3. Medic enters how many they are taking (numeric keypad)
4. App computes new vehicle count: quantity_found + taken
5. Row re-evaluates status (may become OK or remain SHORT)
6. Transfer recorded:
   - stock_lot quantity decremented at supply room location
   - stock_lot quantity incremented at vehicle location (or new lot created)
   - Audit event: `STOCK_TRANSFERRED` with from_location, to_location, item, quantity, actor
7. If supply room quantity after transfer < supply room par minimum:
   - Supervisor notification generated immediately:
     "Supply room low: [item] — [N] remaining, par minimum is [M]. Reorder needed."
   - Notification badge on supervisor dashboard
   - Audit event: `SUPPLY_ROOM_LOW` with severity WARNING

### Supply room par levels
Supply room par levels work identically to vehicle par levels and are already
supported by the existing `ParLevel` model (`location_id` pointing to the
supply room `InventoryLocation`). The supervisor sets min/max quantities for
the supply room just as they do for vehicles.

The supply room low-stock check is triggered:
- After any stock transfer out of the supply room
- On the daily expiring lots report
- On demand from the supervisor supply room view

### Supply room view (Supervisor, Administrator)
A dedicated supply room screen accessible from the supervisor dashboard:
- Current stock per item with par level comparison
- Color coded: green (at/above par), amber (below par), red (empty)
- Items below par highlighted at the top of the list
- "Record reorder" action: mark an item as ordered with expected delivery date
- When a reorder arrives: "Mark received" updates stock quantity

### Backend requirements (Phase 6)
- POST /api/v1/inventory/transfer — move stock between locations
- GET /api/v1/inventory/locations/{id}/stock-summary — stock vs par per item
- Notification trigger on supply room low stock
- `STOCK_TRANSFERRED` and `SUPPLY_ROOM_LOW` audit event types
- Reorder tracking model (optional Phase 7)

### File additions
```
src/modules/supply-room/
  index.jsx
  api/supplyRoomApi.js
  components/
    SupplyRoomStockList.jsx
    RestockFromSupplyRoom.jsx    ← shown on item row during check
    TransferConfirm.jsx
    LowStockAlert.jsx
    ReorderForm.jsx
  pages/
    SupplyRoomPage.jsx
```

---

## Module 9: Role Switcher (Supervisor, Administrator)

### Background
In small EMS departments, supervisors regularly work operational shifts as
crew members — driving the ambulance and performing patient care alongside
responders. When a supervisor is working a crew shift, they should be able
to use the app in responder mode without navigating a supervisor dashboard
they don't need in that moment.

Conversely, when the supervisor needs to check compliance mid-shift, they
should be able to switch back to supervisor view without logging out and
back in.

### Design decision: display-only role switching
Role switching changes **only the UI** — it does not change the JWT, does
not require re-authentication, and does not affect what the API accepts.
The supervisor's JWT always contains the Supervisor role; the API always
accepts their submissions at the appropriate permission level.

This means:
- A supervisor in Crew Mode can still submit checks (JWT permits it)
- A supervisor in Crew Mode cannot accidentally access management functions
  (the UI hides them)
- The check record always shows their real name and actual role
- No Azure AD changes are required

### UX implementation
The role switcher lives in the user pill dropdown (top-right, every screen).

**Default state (Supervisor view):**
```
[JD] Jane Doe               ▾
     Supervisor · Station 1
     ———————————————
     Switch to crew mode
     My profile
     Sign out
```

**Crew mode active:**
```
[JD] Jane Doe    CREW MODE   ▾
     Supervisor (acting as Responder)
     ———————————————
     Switch to supervisor view
     My profile
     Sign out
```

- An amber "CREW MODE" badge appears in the user pill whenever crew mode is active
- The entire supervisor dashboard, calendar, and management modules are hidden
- The responder check wizard is shown as the home screen
- A persistent banner at the top of the check wizard: "You are in crew mode.
  Your supervisor tools are still available. [Switch back]"
- Crew mode preference stored in localStorage: `ems_role_mode: 'crew' | 'supervisor'`
- Resets to supervisor view on next login (never persists across sessions)

### Check record behavior in crew mode
When a supervisor submits a check in crew mode:
- `performed_by` = "Jane Doe" (from JWT — same as always)
- Check record notes: "Submitted in crew mode"
- Supervisor dashboard shows the check normally; no distinction in compliance calendar
- The supervisor can still acknowledge their own check if it FAILs (role permits it)

### What crew mode does NOT change
- JWT token and claims
- API permissions (Supervisor endpoints still work)
- Audit event attribution
- The check reference number and legal record

### File additions
```
src/shared/hooks/useRoleMode.jsx    ← crew | supervisor mode state
src/shared/components/
  UserPill.jsx                      ← updated: role switcher in dropdown
  CrewModeBanner.jsx                ← persistent reminder during check
  RoleModeToggle.jsx                ← the switch UI in the dropdown
```

### Backend requirements
None — this is entirely frontend state management. No API changes required.

---

## 21. Next Phase

Phase 6 — Backend Extensions: Ten new or updated API endpoints required
by the Phase 5 supervisor dashboard, vehicle management, user management,
feedback, notification, and data export modules.
