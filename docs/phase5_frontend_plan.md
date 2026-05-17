# Phase 5 — Frontend (PWA) Implementation Plan
# Last updated: 2026-05-15
# Incorporates: original wizard design + date/expiry editing +
#               responder requirements + supervisor requirements +
#               modularity architecture

---

## Core design principles

- **Modular architecture** — every feature is an isolated React module
  (component + hook + API slice). Adding or updating a module does not
  touch other modules. A broken module shows an inline error boundary
  instead of crashing the whole app.
- **Mobile-first** — designed for phones and tablets, 60+ users,
  minimum 48px tap targets, 18px+ body text, high contrast
- **Offline-first** — localStorage draft saves on every interaction;
  submit only goes to the server when the medic is done
- **Identity-first** — the logged-in user is visible on every screen;
  all submissions are cryptographically tied to the JWT identity

---

## Architecture: modularity

### Why this matters
If the Drug Bag module breaks, Compartment #1 still works.
If the Supervisor dashboard breaks, the medic check workflow still works.
If the feedback module breaks, nothing else is affected.

### How it is implemented

```
src/
  modules/                  ← each folder is a self-contained feature
    check-wizard/           ← daily inventory check flow
    item-management/        ← add/remove items from inventory
    vehicle-status/         ← mark vehicle inactive, repair requests
    supervisor-dashboard/   ← calendar view, print, compliance
    user-management/        ← add-user requests
    feedback/               ← bug reports, enhancements, feedback
  shared/                   ← reused across all modules
    components/             ← UserPill, StatusBadge, Modal, Spinner
    hooks/                  ← useAuth, useDraft, useApi
    utils/                  ← statusCalc, dateHelpers, formatters
    api/                    ← client.js (axios + auth interceptor)
```

Each module has its own:
- `index.jsx` — entry point, wrapped in `<ErrorBoundary>`
- `api/` — API calls for that module only
- `components/` — components used only by that module
- `hooks/` — hooks used only by that module

`<ErrorBoundary>` wraps every module. If a module throws, it shows:
"This feature is temporarily unavailable. The rest of the app is unaffected."
and logs to the audit system. Never a white screen or stack trace.

### Navigation
React Router v6. Each module is a route group:
- `/check`            → check-wizard module
- `/items`            → item-management module
- `/vehicle`          → vehicle-status module
- `/supervisor`       → supervisor-dashboard module (role-gated)
- `/admin`            → user-management module (role-gated)
- `/feedback`         → feedback module

Role-gated routes: if the user's JWT does not contain the required role,
they see a "You don't have access to this page" screen, not a broken page.

---

## Module 1: Check Wizard (Responder, Supervisor, Administrator)

The core daily inventory workflow. Four steps plus a confirmation screen.

### Step 1 — Select vehicle + date
- Large tap-target vehicle cards (unit number + type + active status)
- Inactive vehicles are grayed out and not selectable
- Draft banner if a saved check exists for this user/vehicle/date
- **Check date selector** (below vehicle cards):
  - Default = today
  - Shows: "Check date: Tuesday, May 13, 2026  [Edit]"
  - [Edit] opens native HTML date input (large, works on all phones)
  - Clamped: cannot be future; cannot be more than 7 days ago
  - Persists in localStorage draft
- **Second crew member** (below date):
  - Shows: "Second crew member: [None selected]  [Add]"
  - [Add] opens a searchable dropdown of active users at the station
  - Selected name shows with an X to remove
  - Stored in draft and sent in check notes: "Second crew: Jane Smith"
  - Required before submit if station policy requires dual crew (configurable)
- API impact: no backend changes; second crew captured in check.notes

### Step 2 — Select compartment
- Scrollable list of compartments for the selected vehicle
- Status badge per compartment:
  - Not started — light gray background
  - In progress — light blue background
  - Complete, no issues — light green background
  - Complete, flagged — light red background (SHORT/MISSING/EXPIRED items)
- "Review & submit" button appears once all compartments are complete
  (or supervisor can override and submit partial)
- Compartment list is loaded from API; cached in localStorage for offline use

### Step 3 — Count items (per compartment)

#### Item row layout
- Item name (large, 18px+)
- Need quantity shown prominently — this is the par level
- +/− counter buttons (min 48px tap target each)
- Count value color-coded live:
  - Light green background = OK
  - Light amber background = SHORT
  - Light red background = MISSING or EXPIRED
- **Validate button per item row**:
  - Each row starts with a light red background until validated
  - When the medic taps the checkmark/validate button:
    - If count >= need: row turns light green, checkmark turns solid green
    - If count < need: row turns light amber, shows "SHORT" badge
    - If count = 0: row stays light red, shows "MISSING" badge
  - This ensures every item is explicitly touched/verified, not just skipped
  - "Save compartment" button is disabled until all items are validated
- Lot info shown below item name: "LOT-A123 · Exp: Mar 15, 2027"
- EXPIRED items: expiry date shown in red + "EXPIRED" badge
- **Expiry date override** (see dedicated section below)
- **Add item to this compartment** button (see item management module)
- **Comments field** per compartment (optional free text, max 300 chars)

#### Expiry date override
- Tapping [?] next to expiry date opens inline panel:
  "System shows: Mar 15, 2027
   Date on box:  [date input]
   [Use box date]  [Cancel]"
- Override re-evaluates EXPIRED status immediately
- Recorded in line_item.notes: "Medic reported lot expiry as 2027-02-15 (system: 2027-03-15)"
- Does NOT update the StockLot in the database — supervisor corrects separately
- API impact: none — notes field already exists

### Step 4 — Review & submit
- Summary card:
  - Vehicle name and type
  - Check date
  - **Submitted by: [Full name] · [Role] · [Station]** — from JWT, not editable
  - **Second crew member: [Name]** (if selected)
  - Compartments checked: N of N
  - Items counted: N items
- Issues section: all EXPIRED / MISSING / SHORT items with compartment + detail
- **Overall comments field** (optional free text for the whole check)
- **Vehicle repair flag** (see vehicle-status module section below)
- "Back" — returns to Step 2 (compartment list)
- "Submit check" → POST /api/v1/checks/daily
- On success → Submitted screen

### Submitted screen
- Green checkmark
- "Check recorded" title
- "Submitted by [Name] · [time]" — from JWT
- "Second crew: [Name]" if applicable
- If any items flagged: "Your supervisor has been notified"
- "Start another check" — clears draft, returns to Step 1

---

## Module 2: Item Management (Supervisor, Administrator)

Handles adding new items to a compartment and removing existing items,
with full documentation of when and why.

### Add item to inventory
**Trigger**: "Add item" button on Step 3 (item row area) or from the
Supervisor dashboard.

**Flow**:
1. Search or scroll the global item catalog
2. If item exists in catalog: select it, set the Need (par) quantity,
   assign to compartment
3. If item is brand new (e.g. nitro was just authorized):
   - Fill out: item name, category (medication/consumable/equipment),
     unit of measure, controlled substance flag
   - Creates new Item record via POST /api/v1/items (Administrator only)
   - Then assigns par level to compartment
4. Notes field: "Reason for adding: State law now permits nitroglycerin
   administration by EMT-B effective Jan 1, 2026"
5. Audit event logged automatically by API

**Who can do this**:
- Add to catalog: Administrator only
- Add to compartment par: Supervisor or Administrator
- The "Add item" button in the check wizard is visible to Responders
  but opens a "Request item addition" form that goes to their supervisor

### Remove item from inventory
**Trigger**: Long-press or swipe on an item row in Step 3 (with confirmation),
or from the Supervisor dashboard.

**Flow**:
1. Tap "Remove item" (requires Supervisor or Administrator)
2. Confirmation modal:
   "Remove [item name] from [compartment]?
    This will be documented in the audit log.
    Reason: [required text field]"
3. Examples of reasons: "State mandate: King Combi-tube discontinued effective
   March 1, 2026. Removed per medical director order."
4. Deactivates the par level for this item/compartment (does not delete)
5. Item disappears from future checks for this compartment
6. Historical check records are unchanged (the item remains in past data)
7. API: PATCH /api/v1/inventory/par-levels/{id} to set active=false
   (Phase 6 backend task — add active flag to par_level model)

**Who can do this**: Supervisor or Administrator only.
Responders see a "Request item removal" option that creates a supervisor notification.

---

## Module 3: Vehicle Status (All roles, write access Supervisor+)

### Mark vehicle inactive (Supervisor, Administrator)
**Where**: Supervisor dashboard or vehicle detail page.

**Flow**:
1. Toggle "Active / Inactive" on vehicle card
2. Confirmation: "Mark Unit 401 as inactive? Daily inventory checks will
   not be required while this vehicle is inactive."
3. Reason required: "Out for maintenance — brake job, ETA 3 days"
4. Vehicle shows as grayed out in Step 1 of check wizard
5. Supervisor calendar shows inactive vehicles differently (gray stripe,
   not red/green — no check required)
6. API: PATCH /api/v1/vehicles/{id} (Phase 6 backend task — add active
   flag + inactive_reason + inactive_since to Vehicle model)

### Reactivate vehicle
- Supervisor taps "Reactivate" on inactive vehicle
- Confirmation: "Reactivate Unit 401? Daily inventory checks will resume."
- Audit event logged: "Vehicle reactivated by [name]"

### Report vehicle needs repair (All roles)
**Where**: Step 4 review screen AND from a persistent "Report issue" button
visible on every screen.

**Flow**:
1. Tap "Report repair needed"
2. Simple form:
   - Severity: Urgent (vehicle unsafe) / Non-urgent (can wait)
   - Description: free text, 500 chars max
   - Optional: mark vehicle inactive immediately (Supervisor only)
3. Submits a repair request record
4. Supervisor receives an in-app notification and email
5. API: POST /api/v1/vehicles/{id}/repair-requests (Phase 6 backend task)
6. Audit event logged: "Repair request filed by [name]: [severity]"

---

## Module 4: Supervisor Dashboard (Supervisor, Administrator)

### Calendar compliance view
**Concept**: Monthly calendar where each day shows check status per vehicle.

**Layout**:
- Month view, one column per active vehicle
- Each day/vehicle cell:
  - Light green = check completed, all items OK
  - Amber = check completed, some items flagged (SHORT)
  - Red = check completed, items MISSING or EXPIRED
  - Dark red = check NOT completed (missed)
  - Gray stripe = vehicle inactive that day (no check required)
- Tap a cell → opens that specific check instance
- "This month" summary: N checks completed, N missed, N flagged

**API**: GET /api/v1/checks/daily/station/{id} with date range filter
(Phase 6 backend task — add date range filter to compliance endpoint)

### Access and print a specific check
**Trigger**: Tap any calendar cell, or search by date/vehicle.

**Check detail view**:
- Vehicle, date, performed by, second crew member
- Status badge (PASS / NEEDS_RESTOCK / FAIL)
- All compartments with all line items:
  - Item name, Need, Have, status
  - Lot number and expiration date (critical for legal purposes)
  - Any notes or expiry overrides
- Overall check notes and second crew
- Audit trail: who submitted, timestamp
- **Print button**: generates a clean print stylesheet view
  (browser print dialog — no PDF library needed)
  Print layout includes: station letterhead placeholder, all data,
  signature line at bottom for supervisor sign-off

**Use case documented**: "If the ambulance has been sued because the AED
didn't work, pull up that date, see who did the inventory, what the battery
level was documented at, lot number, expiry. Print for legal hold."

### Supervisor notifications
- In-app notification bell (top bar, Supervisor+ only)
- Notifications for:
  - Repair request filed (with severity badge)
  - FAIL check submitted (MISSING or EXPIRED items)
  - User addition request from a crew member
  - Item add/remove request from a crew member
- Tap notification → opens relevant record
- API: GET /api/v1/notifications (Phase 6 backend task)

---

## Module 5: User Management (Supervisor, Administrator)

### Request to add a new user (Supervisor → Administrator)
**Trigger**: "Request new user" button in the Supervisor dashboard.

**Flow**:
1. Supervisor fills out:
   - Name, email address
   - Role: Responder / Supervisor
   - Station assignment
   - Notes: "New hire starting June 1"
2. Submits a user addition request to the app manager (Administrator)
3. Administrator receives an in-app notification + email
4. Administrator manually adds the user to the correct Azure AD group
   (ems-readykit-responders or ems-readykit-supervisors)
5. Request is marked complete once the user logs in successfully

**Why not auto-provision**: Azure AD group membership requires Administrator
consent. This keeps the audit trail clean — a human reviews every new user.

**API**: POST /api/v1/admin/user-requests (Phase 6 backend task)

---

## Module 6: Feedback (All roles)

**Trigger**: "Send feedback" button accessible from every screen
(floating button bottom-right, or in the user pill dropdown).

**Form**:
- Type: Bug report / Enhancement request / General feedback
- Description: free text, 1000 chars max
- Severity (for bugs): Blocking / Major / Minor
- Current screen/context auto-captured
- Optional: allow app manager to follow up? [Yes/No]
- Submit → POST /api/v1/feedback (Phase 6 backend task)

**Where it goes**:
- Stored in the database
- Administrator sees all feedback in the admin dashboard
- Email notification for bugs marked Blocking or Major

---

## Second crew member — detail

- Appears on Step 1 of the check wizard, below the date selector
- Label: "Second crew member" (not "partner" — neutral, professional)
- Searchable dropdown populated from GET /api/v1/stations/{id}/users
  (Phase 6 backend task — expose active users at a station)
- Can be left blank if solo check (not all checks require two people)
- Stored in check.notes: "Second crew: Jane Smith (user_id: 42)"
- Shown on Step 4 review and confirmation screen
- Shown on printed check record for supervisory sign-off
- API impact: notes field already exists; user lookup endpoint is Phase 6

---

## localStorage draft format (updated)

Key: `ems_draft_{vehicle_id}_{check_date}`
Value (JSON):
```json
{
  "vehicle_id": 1,
  "station_id": 1,
  "check_date": "2026-05-13",
  "saved_at": "2026-05-13T09:35:00Z",
  "second_crew": "Jane Smith",
  "overall_notes": "Truck was restocked after morning run.",
  "repair_needed": false,
  "repair_notes": "",
  "compartments": {
    "12": {
      "compartment_id": 12,
      "name": "Drug Bag",
      "status": "flagged",
      "compartment_notes": "Epi restocked mid-shift by supervisor.",
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

Draft is deleted from localStorage after successful submit.
If a draft exists for the same vehicle and date, show a resume banner.

---

## Validate button — detail

**Problem it solves**: On paper, medics physically touch every item.
On a digital form, they could skip an item without noticing.

**Implementation**:
- Each item row has a light red background by default ("unchecked")
- Large checkmark button (≥48px) on the right side of the row
- Tapping the checkmark after entering the count:
  - Runs status computation (OK / SHORT / MISSING / EXPIRED)
  - Changes row background:
    - OK → light green
    - SHORT → light amber
    - MISSING → light red (stays red, but checked red vs unchecked red)
    - EXPIRED → light red with EXPIRED badge
  - Checkmark icon changes from outline to filled (gray → green/amber/red)
- "Save compartment" button is disabled while any item is unvalidated
- Unvalidated item count shown: "3 items not yet checked"
- Validated state stored in localStorage draft per item

---

## API calls — complete list

| Module | Action | Endpoint | Backend status |
|--------|--------|----------|---------------|
| Check wizard | Load vehicles | GET /api/v1/stations/{id}/vehicles | ✅ exists |
| Check wizard | Load compartments | GET /api/v1/inventory/locations/{id}/compartments | ✅ exists |
| Check wizard | Load par levels (Need) | GET /api/v1/inventory/locations/{id}/par-levels | ✅ exists |
| Check wizard | Load stock lots (Have/expiry) | GET /api/v1/inventory/locations/{id}/stock | ✅ exists |
| Check wizard | Submit check | POST /api/v1/checks/daily | ✅ exists |
| Check wizard | Check if done today | GET /api/v1/checks/daily/vehicle/{id} | ✅ exists |
| Item mgmt | Add item to catalog | POST /api/v1/items | ✅ exists |
| Item mgmt | Add par level | POST /api/v1/inventory/par-levels | ✅ exists |
| Item mgmt | Deactivate par level | PATCH /api/v1/inventory/par-levels/{id} | 🔴 Phase 6 |
| Vehicle status | Mark inactive | PATCH /api/v1/vehicles/{id} | 🔴 Phase 6 |
| Vehicle status | File repair request | POST /api/v1/vehicles/{id}/repair-requests | 🔴 Phase 6 |
| Supervisor | Calendar compliance | GET /api/v1/checks/daily/station/{id}?from=&to= | 🔴 Phase 6 |
| Supervisor | Check detail | GET /api/v1/checks/daily/{id} | ✅ exists |
| Supervisor | Notifications | GET /api/v1/notifications | 🔴 Phase 6 |
| User mgmt | User addition request | POST /api/v1/admin/user-requests | 🔴 Phase 6 |
| User mgmt | List station users | GET /api/v1/stations/{id}/users | 🔴 Phase 6 |
| Feedback | Submit feedback | POST /api/v1/feedback | 🔴 Phase 6 |
| Lots | Correct expiry date | PUT /api/v1/inventory/lots/{id} | 🔴 Phase 6 |

---

## Files to create (full structure)

```
app/frontend/
  public/
    index.html
    manifest.json          ← PWA: name, icons, theme color
  src/
    main.jsx               ← MSAL provider + React Router
    App.jsx                ← top-level routes + role guards
    shared/
      api/
        client.js          ← axios instance, auth interceptor, error handler
      components/
        UserPill.jsx        ← identity pill + dropdown (every screen)
        StatusBadge.jsx     ← OK/SHORT/MISSING/EXPIRED colored badge
        ErrorBoundary.jsx   ← wraps every module
        Modal.jsx           ← reusable confirmation modal
        Spinner.jsx         ← loading state
        NotificationBell.jsx← supervisor notification indicator
      hooks/
        useAuth.jsx          ← getToken(), currentUser, role check
        useDraft.js         ← localStorage read/write/clear
        useApi.jsx           ← generic fetch hook with loading/error state
      utils/
        statusCalc.js       ← OK/SHORT/MISSING/EXPIRED logic
        dateHelpers.js      ← format, clamp, parse dates
        roleGuard.js        ← check JWT roles

    modules/
      check-wizard/
        index.jsx           ← ErrorBoundary + wizard router
        api/
          checkApi.js
          vehicleApi.js
          inventoryApi.js
        components/
          VehicleCard.jsx
          CompartmentCard.jsx
          ItemRow.jsx
          ValidateButton.jsx
          DatePicker.jsx
          ExpiryOverride.jsx
          DraftBanner.jsx
          SecondCrewPicker.jsx
          CompartmentNotes.jsx
          OverallNotes.jsx
          RepairFlag.jsx
        hooks/
          useCheckWizard.js  ← state machine for the 4 steps
          useCompartment.js  ← per-compartment item state
        pages/
          Step1Vehicle.jsx
          Step2Compartments.jsx
          Step3Items.jsx
          Step4Review.jsx
          Submitted.jsx

      item-management/
        index.jsx
        api/itemMgmtApi.js
        components/
          AddItemForm.jsx
          RemoveItemConfirm.jsx
          ItemCatalogSearch.jsx
        pages/
          ItemManagement.jsx

      vehicle-status/
        index.jsx
        api/vehicleStatusApi.js
        components/
          InactiveToggle.jsx
          RepairRequestForm.jsx
        pages/
          VehicleStatus.jsx

      supervisor-dashboard/
        index.jsx
        api/supervisorApi.js
        components/
          ComplianceCalendar.jsx
          CalendarCell.jsx
          CheckDetail.jsx
          PrintableCheck.jsx
          NotificationList.jsx
        pages/
          SupervisorHome.jsx
          CheckDetailPage.jsx

      user-management/
        index.jsx
        api/userMgmtApi.js
        components/
          UserRequestForm.jsx
        pages/
          UserManagement.jsx

      feedback/
        index.jsx
        api/feedbackApi.js
        components/
          FeedbackForm.jsx
          FeedbackButton.jsx   ← floating button on all screens
        pages/
          FeedbackPage.jsx
```

Terraform:
```
iac/Terraform/modules/frontend/
  main.tf       ← azurerm_static_web_app
  variables.tf
  outputs.tf    ← static web app URL, default hostname
```

GitHub Actions:
```
.github/workflows/deploy.yml  ← add frontend build + deploy job
```

---

## Build order (revised with new requirements)

### Phase 5A — Foundation (build first, everything depends on this)
1. `shared/api/client.js` + `shared/hooks/useAuth.jsx` — auth + API client
2. `shared/components/ErrorBoundary.jsx` — wrap all modules from the start
3. `shared/utils/statusCalc.js` + `dateHelpers.js` — pure logic
4. `shared/hooks/useDraft.js` — localStorage draft
5. `shared/components/UserPill.jsx` — identity on every screen

### Phase 5B — Check wizard (core workflow)
6. Step1Vehicle + VehicleCard + DatePicker + SecondCrewPicker
7. Step2Compartments + CompartmentCard
8. Step3Items + ItemRow + ValidateButton + ExpiryOverride + CompartmentNotes
9. Step4Review + OverallNotes + RepairFlag
10. Submitted screen
11. DraftBanner — resume/discard flow

### Phase 5C — Item management module
12. ItemCatalogSearch + AddItemForm
13. RemoveItemConfirm

### Phase 5D — Vehicle status module
14. RepairRequestForm
15. InactiveToggle (requires Phase 6 backend endpoint)

### Phase 5E — Supervisor dashboard module
16. ComplianceCalendar + CalendarCell (requires Phase 6 date-range endpoint)
17. CheckDetail + PrintableCheck (GET /checks/daily/{id} already exists)
18. NotificationList (requires Phase 6 notifications endpoint)

### Phase 5F — Supporting modules
19. Feedback module (FeedbackForm + floating FeedbackButton)
20. User management module (UserRequestForm)

### Phase 5G — Infrastructure
21. Terraform frontend module (Azure Static Web App)
22. GitHub Actions frontend deploy job
23. CORS config in API app settings (add Static Web App URL)
24. MSAL redirect URI registration in Azure AD App Registration

---

## Accessibility / usability requirements

- Minimum font: 18px body, 22px item names, 24px counter values
- Minimum tap target: 48×48px on all interactive elements
- High contrast: dark text on white; never gray-on-gray
- Status uses both color AND text label (not color alone)
- No hidden gestures — all actions are visible buttons
- Loading state on every API call — spinner or skeleton, never blank
- Error state: plain English message + "Try again" — never raw errors
- "Are you sure?" confirmation before: discard draft, remove item,
  mark vehicle inactive, submit with flagged items
- Print stylesheet: clean, no nav chrome, includes all relevant data

---

## Supervisor calendar — detail

The calendar is the most important supervisor tool for compliance.

**Monthly view layout**:
```
         Unit 401   Unit 402   Engine 1
May 1    🟢 PASS    🟢 PASS    🟢 PASS
May 2    🟡 FLAG    🟢 PASS    ░░ INACTIVE
May 3    🔴 MISSED  🟢 PASS    ░░ INACTIVE
May 4    🟢 PASS    🔴 MISSED  🟢 PASS
```

**Cell tap** → opens check detail for that vehicle/date
**Month summary** at top: "23 of 28 required checks completed this month"
**Export** button: downloads month summary as CSV (for compliance reporting)

**Color key** (shown as legend at top of calendar):
- 🟢 Light green = completed, PASS
- 🟡 Light amber = completed, NEEDS_RESTOCK
- 🔴 Light red = completed, FAIL (MISSING or EXPIRED items)
- ⬛ Dark red = check NOT completed (missed)
- ░░ Gray stripe = vehicle inactive (no check required)

---

## UX/UI gaps identified — walkthrough review
# Reviewed 2026-05-15 from both EMT and Supervisor perspectives

### 🔴 Must have before launch

1. **Station-filtered vehicle list** — on login, responders only see vehicles
   at their assigned station. Supervisors see all stations with a station
   switcher. Never show cross-station vehicles to a responder.

2. **"Last checked today" on vehicle cards** — each vehicle card shows:
   - "No check yet today" (amber)
   - "Checked today at 06:15am — PASS" (green)
   - "Checked today at 06:15am — FAIL" (red)
   This prevents duplicate checks and ensures nothing is missed.
   API: GET /api/v1/checks/daily/vehicle/{id} already exists.

3. **Per-line-item notes field** — the notes field is currently per
   compartment only. Each item row needs an optional inline notes field:
   "SHORT — used on 06:12 run, awaiting restock from supervisor."
   API impact: line_item.notes field already exists in the model.
   UI: tap a small [note] icon on the item row to expand a text field.

4. **Controlled substance special flow** — CS items (flagged as
   controlled_substance=True) cannot be mixed in with regular items.
   They need:
   - A visible CS badge on the item row (red lock icon)
   - A prompt after validating a CS item: "This is a controlled substance.
     A second crew member must witness this count."
   - The second crew member field (Step 1) becomes required if any CS
     items are being checked
   - On the Drug Bag / Narcotic Lock Bag: a header warning: "Controlled
     substances — dual witness required"
   This connects to the existing ControlledSubstanceCheck API workflow.

5. **Submit with incomplete compartments — explicit warning** — if the
   medic taps "Review & submit" with compartments still showing "Not
   started", show a blocking modal:
   "2 compartments not checked: First Out Bag, Narcotic Lock Bag.
    Submit anyway? This check will be marked INCOMPLETE and your
    supervisor will be notified."
   [Submit incomplete]  [Go back and finish]
   Never silently submit a partial check.

6. **Supervisor landing dashboard** — supervisors do not land on the
   calendar. They land on a dashboard summary:
   - Today's status: "3 of 3 checks complete" or "1 of 3 — Unit 402
     not yet checked"
   - Active alerts: FAIL checks, repair requests, unread notifications
   - Quick links: View calendar, View repair requests, Manage users
   The calendar is reached from the dashboard, not the default view.

7. **Supervisor acknowledgement + corrective action** — when a supervisor
   views a FAIL check, they see an "Acknowledge" button:
   "Acknowledge this check as reviewed?"
   After acknowledging, a corrective action field appears:
   "Action taken: [required text — e.g. 'Replaced expired Epi 1:10,000,
   lot XYZ, exp 2027-08-01 at 09:15am']"
   The check record stores: reviewed_by, reviewed_at, corrective_action.
   API: Phase 6 — add these fields to DailyInventoryCheck model.
   Unacknowledged FAIL checks show a badge on the notification bell.

### 🟡 Important — build shortly after launch

8. **"Jump to unvalidated" button in Step 3** — when a compartment has
   many items (some compartments have 15+), a sticky button at the bottom:
   "3 items not yet checked — Jump to next ↓"
   Scrolls to the first unvalidated item row.

9. **Expired item replacement prompt** — when a medic validates an EXPIRED
   item, show an inline prompt:
   "This item is expired. Was it replaced?
    [Yes — enter new lot number + expiry]  [No — enter reason]"
   If replaced: creates a note with new lot info.
   If not: requires a reason ("No replacement stock available").
   Both paths are recorded in line_item.notes.

10. **Multiple checks per day per vehicle in calendar** — if a vehicle is
    checked twice (day shift + night shift), the calendar cell shows the
    worst-case status with a "2" badge. Tapping shows both checks in a
    list. The cell is never just the first or last — always worst-case.

11. **Repair request status tracking** — repair requests need a lifecycle:
    Filed → Acknowledged → In Progress → Resolved.
    Each transition requires a note. The supervisor sees the current
    status on the vehicle card and in the repair request list.
    Urgent repairs not acknowledged within 60 minutes trigger an
    escalation notification to the administrator.

12. **Check reference number on confirmation screen** — after a successful
    submit, show the check ID prominently:
    "Check #4271 recorded — Unit 401 · May 15, 2026"
    This gives the medic something to reference if asked.

13. **Item count on compartment cards (Step 2)** — each compartment card
    shows: "Compartment #7 · 14 items" so the medic knows how long
    each compartment will take before tapping into it.

14. **Chain of custody header on printed records** — the print layout
    must include:
    - Document ID (check_id)
    - Generated by: [name] at [timestamp]
    - Statement: "This is an official EMS ReadyKit inventory record.
      Record ID: {check_id}. Do not alter."
    - Signature lines: Performed by ___ / Second crew ___ / Supervisor ___
    This makes the printout legally defensible.

### 🟢 Nice to have

15. **Partial/opened lot flag** — an optional "opened" toggle on a lot
    line item for vials/packages that have been partially used.
    Useful for medications where an opened vial has a shorter real-world
    usable life than the printed expiry date.

16. **Time remaining estimate on Step 4** — "2 compartments not checked —
    approximately 6 minutes remaining" based on average item count.
    Helps medics prioritize when time is short.

17. **Suspend/reactivate individual users** — supervisors can temporarily
    deactivate a crew member (injury, leave, suspension) without deleting
    the account. Deactivated users cannot log in; their history is preserved.
    API: Phase 6 — add active flag to user records.

18. **"Who is on shift" context for second crew picker** — the second crew
    dropdown ideally shows who has logged in today or is scheduled, not
    just a flat alphabetical list of all users.

19. **Calendar filter by issue type** — "show only FAIL days", "show only
    Unit 402", "show only missed checks" — filter controls above the
    calendar grid.

---

## Notes for next session

**Backend tasks needed before some frontend modules can be built (Phase 6)**:
- PATCH /api/v1/vehicles/{id} — add active/inactive flag + reason
- POST /api/v1/vehicles/{id}/repair-requests — repair request model + endpoint
- PATCH /api/v1/inventory/par-levels/{id} — add active flag to par_level
- GET /api/v1/checks/daily/station/{id}?from=&to= — date range filter
- GET /api/v1/stations/{id}/users — list active users at a station
- POST /api/v1/admin/user-requests — user addition request
- POST /api/v1/feedback — feedback record
- GET /api/v1/notifications — in-app notifications
- PUT /api/v1/inventory/lots/{id} — supervisor expiry correction

**Infrastructure tasks**:
- Register Static Web App URL as allowed redirect URI in Azure AD App Registration
- Add WEBSITES_CORS_ALLOWED_ORIGINS to API app settings in Terraform
- Check Azure Static Web Apps free tier for custom domain support
- The API enforces real JWT validation in production — frontend must use MSAL tokens

**Design decisions to confirm before building**:
- Is dual crew (second crew member) required or optional per station?
- Should Responders be able to request item additions, or only Supervisors?
- Is the feedback form public (any authenticated user) or internal only?
- Should missed checks trigger an automatic email to the supervisor?
