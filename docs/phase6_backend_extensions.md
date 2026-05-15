# EMS ReadyKit — Phase 6: Backend Extensions
# Document version: 1.0
# Status: Planned — Not Yet Started
# Last updated: 2026-05-15

---

## 1. Executive Summary

Phase 6 delivers the backend API extensions required to complete the
Phase 5 supervisor dashboard, vehicle management, user management,
notification, and feedback modules. Ten new or updated endpoints are
planned, along with the data model additions and migrations needed to
support them. This phase also introduces the supervisor acknowledgement
and corrective action workflow, closing the legal accountability loop
on FAIL inventory checks.

---

## 2. Objectives

| Objective | Description |
|-----------|-------------|
| Vehicle lifecycle management | Mark vehicles inactive/active with documented reason; required for calendar accuracy |
| Repair request tracking | Full lifecycle from filed to resolved; escalation for urgent requests |
| Supervisor acknowledgement | FAIL checks must be acknowledged with corrective action before they are considered resolved |
| Compliance calendar API | Date-range query returning check status per vehicle per day |
| Station user list | Endpoint for second crew member picker and "who is on shift" context |
| Lot expiry correction | Supervisors can correct expiry dates observed as wrong during a check |
| Par level lifecycle | Soft-delete par levels when items are removed from a compartment |
| Feedback system | Store and surface crew feedback, bug reports, and enhancement requests |
| Notifications | In-app notification delivery for repair requests, FAIL checks, user requests |
| User management requests | Document new user onboarding requests for administrator action |

---

## 3. Scope

### New data models

| Model | Purpose |
|-------|---------|
| RepairRequest | Vehicle repair request with severity, status lifecycle, and resolution notes |
| Notification | In-app notification with type, recipient role, linked entity, and read status |
| FeedbackEntry | Crew-submitted feedback with type, severity, description, and context |
| UserRequest | Supervisor-submitted new user onboarding request |

### Modified data models

| Model | Changes |
|-------|---------|
| Vehicle | Add `active` (Boolean), `inactive_reason` (String), `inactive_since` (DateTime) |
| ParLevel | Add `active` (Boolean), `deactivated_at` (DateTime), `deactivation_reason` (String) |
| DailyInventoryCheck | Add `reviewed_by` (String), `reviewed_at` (DateTime), `corrective_action` (String) |

### New migration

Migration 0003 — `phase6_extensions`

---

## 4. Planned Endpoints

### 4.1 Vehicle lifecycle

#### PATCH /api/v1/vehicles/{id}
Mark a vehicle active or inactive.

**Request body:**
```json
{
  "active": false,
  "inactive_reason": "Brake repair — ETA 3 days",
  "inactive_since": "2026-05-15T08:00:00Z"
}
```

**Business rules:**
- Inactive vehicles do not appear in the check wizard for responders
- Inactive vehicles show as gray stripe in compliance calendar
- Audit event logged: `VEHICLE_DEACTIVATED` or `VEHICLE_REACTIVATED`
- Role required: Supervisor, Administrator

---

### 4.2 Repair requests

#### POST /api/v1/vehicles/{id}/repair-requests
File a repair request for a vehicle.

**Request body:**
```json
{
  "severity": "URGENT",
  "description": "Rear compartment door latch broken. Cannot secure equipment.",
  "reported_by": "Jane Doe"
}
```

**Business rules:**
- Severity: `URGENT` (vehicle may be unsafe) or `NON_URGENT`
- `URGENT` requests trigger immediate notification to supervisor
- `URGENT` requests not acknowledged within 60 minutes escalate to administrator
- Audit event logged: `REPAIR_REQUEST_FILED`
- Role required: All roles

#### PATCH /api/v1/vehicles/{id}/repair-requests/{request_id}
Update repair request status.

**Status lifecycle:** `FILED` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`

Each transition requires a note. Resolution requires `resolution_notes`.

**Role required:** Supervisor, Administrator

#### GET /api/v1/vehicles/{id}/repair-requests
List repair requests for a vehicle, most recent first.

**Role required:** Supervisor, Administrator

---

### 4.3 Supervisor acknowledgement

#### PATCH /api/v1/checks/daily/{id}/acknowledge
Acknowledge a FAIL check and record corrective action.

**Request body:**
```json
{
  "corrective_action": "Replaced expired Epi 1:10,000. New lot XYZ, exp 2027-08-01. Restocked at 09:15am."
}
```

**Business rules:**
- Only available on checks with status `FAIL`
- `reviewed_by` set from JWT identity (cannot be overridden)
- `reviewed_at` set to current UTC timestamp
- Audit event logged: `CHECK_ACKNOWLEDGED`
- Unacknowledged FAIL checks show notification badge on supervisor dashboard
- Role required: Supervisor, Administrator

---

### 4.4 Compliance calendar

#### GET /api/v1/checks/daily/station/{id}?from={date}&to={date}
Return all daily checks for a station within a date range.

**Query parameters:**
- `from` — start date (YYYY-MM-DD, required)
- `to` — end date (YYYY-MM-DD, required, max 90 days range)

**Response:** List of `DailyInventoryCheckRead` objects including vehicle_id,
check_date, status, performed_by, and line item summary counts.

**Frontend use:** Calendar module aggregates this response to produce the
compliance grid (one cell per vehicle per day).

**Role required:** Supervisor, Administrator

---

### 4.5 Station users

#### GET /api/v1/stations/{id}/users
Return list of active users at a station.

**Response:**
```json
[
  { "user_id": "azure-ad-oid", "name": "Jane Doe", "role": "Responder", "last_login": "2026-05-15T06:12:00Z" }
]
```

**Frontend use:** Second crew member picker; "who is on shift" context.

**Implementation note:** User records are sourced from Azure AD group membership.
This endpoint queries the Microsoft Graph API for members of the station's
responder and supervisor groups, not a local database table.

**Role required:** All roles

---

### 4.6 Lot expiry correction

#### PUT /api/v1/inventory/lots/{id}
Correct the expiration date on a stock lot.

**Request body:**
```json
{
  "expiration_date": "2027-02-15",
  "correction_reason": "Physical lot label reads 2027-02-15; system had 2027-03-15 entered in error."
}
```

**Business rules:**
- Audit event logged: `LOT_EXPIRY_CORRECTED` with old and new dates
- Does not retroactively change the status of historical check line items
- Role required: Supervisor, Administrator

---

### 4.7 Par level lifecycle

#### PATCH /api/v1/inventory/par-levels/{id}
Deactivate a par level (soft delete).

**Request body:**
```json
{
  "active": false,
  "deactivation_reason": "King Combi-tube removed per medical director order dated 2026-03-01."
}
```

**Business rules:**
- Deactivated par levels are excluded from check wizard item lists
- Historical check records retain the item (data is never deleted)
- Audit event logged: `PAR_LEVEL_DEACTIVATED`
- Role required: Supervisor, Administrator

---

### 4.8 Feedback

#### POST /api/v1/feedback
Submit a feedback entry.

**Request body:**
```json
{
  "type": "BUG",
  "severity": "MAJOR",
  "description": "The validate button does not respond on iPhone SE (first generation).",
  "current_screen": "SCREEN_ITEMS",
  "allow_followup": true
}
```

**Types:** `BUG`, `ENHANCEMENT`, `GENERAL`
**Severity (bugs only):** `BLOCKING`, `MAJOR`, `MINOR`

**Business rules:**
- `BLOCKING` and `MAJOR` bugs trigger email notification to administrator
- All feedback visible to administrator in admin module
- `submitted_by` set from JWT; `submitted_at` set to UTC timestamp
- Role required: All roles

#### GET /api/v1/feedback
List all feedback entries with optional type and severity filters.

**Role required:** Administrator

---

### 4.9 Notifications

#### GET /api/v1/notifications
Return unread (and recently read) notifications for the current user.

**Response:**
```json
[
  {
    "notification_id": 42,
    "type": "FAIL_CHECK",
    "title": "Unit 401 check failed",
    "body": "1 expired item, 2 missing items. Submitted by Jane Doe at 06:15am.",
    "linked_entity_type": "DailyInventoryCheck",
    "linked_entity_id": 4271,
    "created_at": "2026-05-15T06:16:00Z",
    "read": false
  }
]
```

**Notification types:**
- `FAIL_CHECK` — check submitted with FAIL status
- `REPAIR_REQUEST` — repair request filed (severity badge included)
- `REPAIR_URGENT_ESCALATION` — urgent repair not acknowledged within 60 minutes
- `ITEM_ADD_REQUEST` — responder requested item addition
- `ITEM_REMOVE_REQUEST` — responder requested item removal
- `USER_REQUEST` — supervisor requested new user onboarding

#### PATCH /api/v1/notifications/{id}/read
Mark a notification as read.

**Role required:** Supervisor, Administrator (notifications scoped by role)

---

### 4.10 User management requests

#### POST /api/v1/admin/user-requests
Submit a new user onboarding request.

**Request body:**
```json
{
  "name": "John Smith",
  "email": "john.smith@township.gov",
  "requested_role": "Responder",
  "station_id": 1,
  "start_date": "2026-06-01",
  "notes": "New hire starting June 1."
}
```

**Business rules:**
- Administrator receives notification
- Administrator manually adds user to Azure AD group
- Request marked complete when user first authenticates successfully
- Role required: Supervisor, Administrator

#### GET /api/v1/admin/user-requests
List user requests with status filter.

**Role required:** Administrator

---

## 5. Migration 0003 — Phase 6 Extensions

### New tables
- `repair_requests` (vehicle_id FK, severity, status, description, resolution_notes, filed_by, filed_at, acknowledged_by, acknowledged_at, resolved_by, resolved_at)
- `notifications` (type, recipient_role, title, body, linked_entity_type, linked_entity_id, created_at, read, read_at)
- `feedback_entries` (type, severity, description, current_screen, allow_followup, submitted_by, submitted_at)
- `user_requests` (name, email, requested_role, station_id, start_date, notes, requested_by, requested_at, status, completed_at)

### Modified tables
- `vehicles` — add `active`, `inactive_reason`, `inactive_since`
- `par_levels` — add `active`, `deactivated_at`, `deactivation_reason`
- `daily_inventory_checks` — add `reviewed_by`, `reviewed_at`, `corrective_action`

---

## 6. Test Plan

New test classes to be written:

| Class | Tests |
|-------|-------|
| TestVehicleLifecycle | inactive/active toggle, calendar exclusion, RBAC |
| TestRepairRequests | file request, status lifecycle, urgent escalation, RBAC |
| TestSupervisorAcknowledgement | acknowledge FAIL, RBAC, tamper resistance |
| TestComplianceCalendar | date range, multi-check days, inactive vehicles |
| TestLotExpiry | correct expiry, audit trail, historical immutability |
| TestParLevelLifecycle | deactivate, reactivate, historical preservation |
| TestFeedback | all types, severity, admin visibility |
| TestNotifications | creation, delivery, mark-read |
| TestUserRequests | request flow, admin notification |

Estimated: ~45 new tests. Total suite target: ~135 tests.

---

## 7. Phase Dependencies

| Dependency | Direction |
|------------|-----------|
| Phase 2–4 | Requires: All base models, endpoints, and migrations |
| Phase 3 | Requires: Authentication for all new protected endpoints |
| Phase 5 | Provides: All endpoints needed by supervisor, management, and notification modules |

---

## 8. Open Questions

| Question | Owner | Target |
|----------|-------|--------|
| Should notification delivery include email (Azure Communication Services)? | Project owner | Before Phase 6 start |
| Should Graph API user lookup be cached locally? | Engineering | Phase 6 design |
| Is a 90-day compliance calendar date range sufficient? | Project owner | Before Phase 6 start |
| Should BLOCKING feedback bugs auto-create a GitHub issue? | Project owner | Phase 6 design |
