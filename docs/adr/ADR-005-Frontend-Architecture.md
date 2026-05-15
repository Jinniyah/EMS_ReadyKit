# ADR-005: Frontend Architecture

**Status:** Accepted
**Date:** 2026-05-15
**Decision Owner:** EMS ReadyKit Project

**Related Artifacts:**
- `docs/phase5_frontend_pwa.md` — full frontend implementation plan
- `docs/help_content.md` — tutorial, FAQ, and contextual help content
- `docs/adr/ADR-001-Architecture.md` — overall system architecture
- `docs/adr/ADR-002-RBAC.md` — role-based access control model
- `docs/adr/ADR-003-Logging-and-Audit.md` — logging and audit strategy

---

## Context

Phase 5 delivers the user-facing application for EMS ReadyKit. The primary
users are EMTs and Paramedics performing daily vehicle inventory checks, and
supervisors reviewing compliance. Secondary users are administrators managing
the system.

The frontend must satisfy several constraints that significantly shape the
architectural choices:

**Operational context:**
- Used on personal phones and tablets in field conditions
- Users may be fatigued (end of shift), stressed, or in a hurry
- Checks must be completable in 10–15 minutes
- A crew member may be interrupted mid-check (toned out for a call)
- Another crew member may need to complete an interrupted check
- Network connectivity in station garages may be intermittent

**User profile:**
- Primary users aged 20–65+, including users with limited technology comfort
- Two distinct role experiences: Responder (check wizard) and Supervisor (dashboard)
- Supervisors occasionally work operational shifts and need to switch views

**Legal and compliance requirements:**
- Identity must be cryptographically bound to every submission
- Check records must be printable with chain of custody documentation
- Audit trail must survive the app being rebuilt or replaced

**Developer maintenance requirements:**
- Modular architecture — one broken feature cannot crash the whole app
- New modules must be addable without touching existing modules
- A new developer must be able to understand the codebase quickly

---

## Decisions

### Decision 1: Progressive Web App (PWA) over native mobile app

**Chosen: PWA (React, deployed to Azure Static Web Apps)**

**Rationale:**
- No App Store installation required — medics add to home screen from browser
- Single codebase serves iOS, Android, and desktop
- Works offline via localStorage draft saving
- Deployable via the existing GitHub Actions pipeline
- Integrates with MSAL for Azure AD authentication in-browser
- Cost: Azure Static Web Apps free tier — $0/month

**Rejected: React Native / Expo**
- Requires App Store submission and review cycles
- Adds build complexity (Xcode, Android Studio)
- Over-engineered for a form-based workflow application

**Rejected: Xamarin / MAUI**
- Microsoft-specific; poor open-source ecosystem alignment
- Heavier development overhead for this use case

**Rejected: Plain HTML/JS (no framework)**
- State management for a multi-step wizard with offline draft saving
  requires more structure than vanilla JS efficiently provides
- Component reuse across 9 modules would be difficult to maintain

---

### Decision 2: Modular React architecture with ErrorBoundary isolation

**Chosen: Feature modules — each module is a self-contained directory with
its own components, hooks, API slice, and ErrorBoundary wrapper.**

```
src/modules/
  check-wizard/         ← daily check workflow
  item-management/      ← add/remove items
  vehicle-status/       ← inactive toggle, repair requests
  supervisor-dashboard/ ← calendar, compliance, print
  user-management/      ← onboarding requests
  feedback/             ← bug reports, enhancements
  data-export/          ← CSV downloads
  supply-room/          ← restock workflow
  help/                 ← tutorial, FAQ, contextual help
```

Each module's `index.jsx` is wrapped in `<ErrorBoundary>`. If a module
throws an unhandled error, it renders an inline error state rather than
crashing the whole application.

**Rationale:**
- A broken Data Export module cannot prevent a medic from submitting a check
- A new developer can read one module folder and understand the complete
  feature without reading the rest of the codebase
- Modules can be enabled or disabled per role without affecting other modules
- Testing is scoped — module tests don't require understanding global state

**Rejected: Single monolithic component tree**
- Any unhandled error anywhere crashes the whole app
- In a field environment, a crash during an active check is unacceptable
- Makes maintenance and onboarding harder as the codebase grows

---

### Decision 3: localStorage offline draft saving

**Chosen: Write-on-every-interaction draft saving to localStorage.**

Draft key format: `ems_draft_{vehicle_id}_{check_date}`

Draft schema:
```json
{
  "vehicle_id": 1,
  "station_id": 1,
  "check_date": "2026-05-15",
  "saved_at": "2026-05-15T09:35:00Z",
  "second_crew": "Jane Smith",
  "overall_notes": "",
  "repair_needed": false,
  "compartments": {
    "12": {
      "compartment_id": 12,
      "name": "Drug Bag",
      "status": "in_progress",
      "line_items": [
        {
          "item_id": 5,
          "lot_id": 3,
          "quantity_found": 2,
          "validated": true,
          "status": "OK"
        }
      ]
    }
  }
}
```

**Rationale:**
- A medic toned out mid-check loses zero work
- Draft resumes on any device logged in as the same user
- No backend endpoint required for draft state
- Handoff flow: a second crew member opening the draft sees who started it
  and can continue under their own identity

**Consequences:**
- localStorage is per-browser — a draft started on one phone is not
  automatically available on a different phone
- Low device storage can cause localStorage to be cleared by the OS —
  mitigated by a storage warning banner when space is low
- Draft is deleted after successful server submission

**Rejected: Server-side draft saving (new API endpoint)**
- Adds backend complexity and a new API endpoint
- Requires network connectivity to save progress
- Defeats the offline-first purpose — a check started in a dead zone
  could not be saved

---

### Decision 4: Display-only role switching (Crew Mode)

**Chosen: UI role switching with localStorage preference. No JWT change.**

When a Supervisor opens the user pill and selects "Switch to crew mode":
- The React application renders the Responder module set only
- An amber "CREW MODE" badge appears in the user pill on every screen
- A dismissible banner reads "You are in crew mode. [Switch back]"
- The localStorage key `ems_role_mode` is set to `"crew"`
- On next login, the preference resets to `"supervisor"`
- The JWT is unchanged — all API calls still carry Supervisor permissions

**Rationale:**
- Small departments have supervisors working operational shifts
- Hiding the supervisor dashboard while working a crew shift removes
  distraction and cognitive load
- No re-authentication required — one tap to switch, one tap to switch back
- The check record is not affected — performed_by still reflects the real identity
- No backend changes required — purely frontend state

**Rejected: Separate login per role**
- Requires two accounts per supervisor
- Azure AD group management complexity doubles
- Unacceptable user experience

**Rejected: Modifying the JWT per role switch**
- Requires re-authentication flow
- Azure AD does not support runtime role downgrade without re-auth
- Latency is unacceptable in a field environment

---

### Decision 5: Client-side CSV generation

**Chosen: CSV is generated in the browser from API response data.**

Implementation:
- `src/modules/data-export/utils/csvBuilder.js` converts API JSON to CSV string
- `src/modules/data-export/utils/csvDownload.js` triggers browser file download
- UTF-8 BOM prepended to ensure correct rendering in Microsoft Excel

**Rationale:**
- No new server endpoint required — reuses existing paginated API
- No server memory overhead for large export datasets
- File never touches a server — reduces data handling surface
- Instant feedback: download begins as soon as data is fetched

**Consequence:**
- Maximum practical export size limited by browser memory (~50,000 rows safe)
- For datasets larger than 365 days, a chunked multi-request approach is used

**Rejected: Server-side CSV generation endpoint**
- New endpoint required with its own auth, pagination, and error handling
- Server must hold the entire dataset in memory during generation
- Slower time-to-download for the user
- Adds infrastructure cost if response is large

---

### Decision 6: Validate button per item (mandatory acknowledgement)

**Chosen: Each item row requires an explicit validate tap before the compartment
can be saved. Items start with a light red background (unvalidated).**

**Rationale:**
- On paper, a medic physically touches every item they check
- Without an explicit acknowledgement, a digital form allows skipping items
  without any evidence — creating a compliance gap
- The validate button creates an intentional, deliberate moment per item
- "Save compartment" is disabled until all items are validated
- Auto-saved to localStorage draft in validated=true state

**Shortcuts that preserve intent without adding friction:**
- "All N present" button: sets quantity_found = quantity_needed + validates in one tap
- Numeric keypad: tap count value → enter quantity → checkmark confirms
- These shortcuts still trigger validation — they cannot be used to skip

**Rejected: Auto-validate on count entry**
- A medic could accidentally tap + and immediately move on without looking
- Removes the intentional acknowledgement that makes the workflow defensible

---

### Decision 7: Check handoff (started_by / completed_by)

**Chosen: When a second user opens an in-progress draft, they see an explicit
handoff screen showing who started the check, what was completed, what remains,
and a confirmation that both names will appear on the record.**

Backend change required (Phase 6):
- Add `started_by` field to `DailyInventoryCheck` model
- `performed_by` remains the submitter; `started_by` records who opened the check

**Rationale:**
- In real EMS operations, checks are frequently interrupted by emergency calls
- The legal record must reflect who started and who completed the check
- Without this, a check started by Jane and submitted by Mark shows only Mark

**Rejected: Single submitted_by field (current behavior)**
- Does not capture the full accountability picture for interrupted checks
- A supervisor cannot see that a check was split between two crew members

---

### Decision 8: Help system architecture

**Chosen: Three-layer help system, all content managed in one file.**

- Layer 1: First-run tutorial (8 steps, shown on first login, replayable)
- Layer 2: Per-screen contextual help (? button → bottom sheet, no navigation loss)
- Layer 3: Searchable FAQ (crew and supervisor sections, 15+ questions)

All content lives in `src/modules/help/content.js` — single source of truth.
Components import from this file; help text is never hardcoded inline.

Reading level target: Grade 6–8. No medical jargon. No acronyms without explanation.

**Rationale:**
- Users aged 60+ with limited technology background need explicit guidance
- Contextual help (bottom sheet) allows reading help without losing check progress
- Single content file means protocol changes require editing one file only
- Discoverable design reduces help requests but does not eliminate the need for help

---

## Summary of key decisions

| Decision | Choice | Key reason |
|----------|--------|-----------|
| App type | React PWA | No App Store; offline; single codebase |
| Architecture | Feature modules + ErrorBoundary | Failure isolation; maintainability |
| Offline strategy | localStorage draft | Zero work loss on interruption |
| Role switching | Display-only, no JWT change | No re-auth; one tap; correct record |
| CSV export | Client-side generation | No new endpoint; instant download |
| Item validation | Explicit validate button per item | Defensible compliance record |
| Check handoff | started_by + completed_by | Legal accountability for split checks |
| Help system | 3-layer, single content file | 60+ users; single source of truth |

---

## Consequences

### Positive
- App works offline — critical for spotty station garage signal
- A module crash never prevents a check from being submitted
- Supervisors can work crew shifts without a separate account
- Check records are legally defensible including interrupted checks
- Help system is maintainable from a single file
- No new infrastructure required for CSV export

### Tradeoffs
- localStorage drafts are per-browser — cross-device handoff requires
  server-side draft saving (Phase 7 consideration)
- Client-side CSV is limited to ~50,000 rows per export
- Display-only role switching means Supervisor API permissions are always
  active even in Crew Mode (mitigated by hiding the UI — not a security risk
  since the JWT is still required for every API call)

---

## Related ADRs

- ADR-001: Overall System Architecture
- ADR-002: Role-Based Access Control Model
- ADR-003: Logging and Audit Strategy
- ADR-004: Terraform Module Structure

---

**Decision affirmed and approved.**
