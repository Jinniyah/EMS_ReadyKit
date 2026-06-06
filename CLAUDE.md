# CLAUDE.md — AI Development Rules for EMS ReadyKit
# Last updated: 2026-06-06
# Updated: Session K — Supply Room Redesign complete; 3 architectural decisions added
# Load this file at the start of every session alongside CODEBASE_INDEX.md.

---

## Session Startup Protocol

Every new session MUST follow this sequence before writing any code:

1. **Read `CODEBASE_INDEX.md`** — orientation, file map, flagged issues
2. **Read `docs/backlog.md`** — current open work and session plan
3. **Read only the files needed for the current task** — no speculative reads
4. **Confirm understanding** of the task before touching any file

Do not read files you don't need. Do not load entire modules to change one function.
Do not write session handoff files — backlog.md is the single source of truth.

---

## Environment

- **OS:** Windows 11
- **Shell:** PowerShell (not bash)
- **Path separator:** backslash `\` — always use Windows paths
- **Command chaining:** use `;` not `&&` (e.g. `cd app; pytest`)
- **grep equivalent:** use `Select-String` or `findstr` in PowerShell,
  OR use `bash_tool` with `grep` when the filesystem MCP is insufficient
- **Line endings:** CRLF — if `filesystem:edit_file` fails on exact match,
  CRLF in the file may be the cause; use `filesystem:write_file` to rewrite
  the whole file as a fallback

---

## Filesystem Rules

### Paths
- Backend root: `C:\Users\jinni\source\repos\EMS_ReadyKit\app\ems_readykit\`
- Frontend root: `C:\Users\jinni\source\repos\EMS_ReadyKit\frontend\src\`
- Docs root:     `C:\Users\jinni\source\repos\EMS_ReadyKit\docs\`
- Tests:         `C:\Users\jinni\source\repos\EMS_ReadyKit\app\tests\`

### Before editing any file
1. Read the file first — always. Never edit blind.
2. For targeted edits in large files, use `filesystem:read_text_file` with `head`
   or `tail` to locate the relevant section before editing.
3. Use `filesystem:read_multiple_files` to read related files simultaneously
   (e.g., router + schema + model when adding an endpoint).

### Editing
- Use `filesystem:edit_file` for surgical edits within existing files.
- `filesystem:edit_file` requires **exact whitespace matching** in `oldText`.
  If it fails silently, use `bash_tool` with `grep -n` to find exact line content.
- Use `filesystem:write_file` to create new files or fully replace a file.
- **Never use the sandbox `create_file` tool** — it writes to the container,
  not the repo. All file creation must use `filesystem:write_file`.

### The `filesystem:read_text_file` view_range parameter
Has been unreliable in past sessions — if it returns from line 1 regardless
of range, fall back to `bash_tool` with `grep -n` for targeted lookups.

---

## Code Rules — Backend (Python / FastAPI)

### Imports — always use shared deps
```python
from ems_readykit.routers.deps import (
    ALL_ROLES, SUPERVISOR_PLUS, ADMIN_ONLY,
    get_current_user, require_role,
    get_vehicle_or_404, require_station_membership,
)
```
**Never** define local `_ALL_ROLES`, `_SUPERVISOR_PLUS`, or `_get_vehicle_or_404()`
in a router. Those were consolidated into deps.py in Session B (REF-1–REF-7).

### Audit events
Always use `core/audit.py::write_audit_event()`. Never write `AuditEvent(...)`
inline in a router — the helper includes the required `logger.info` call.

### Role enforcement pattern
```python
# Access control only (no user object needed in handler):
@router.get("/endpoint", dependencies=[Depends(require_role(*ADMIN_ONLY))])

# Access control + user identity in handler:
@router.post("/endpoint")
def handler(..., current_user: CurrentUser = Depends(require_role(*ALL_ROLES))):
```

### Station membership
Call `require_station_membership(station_id, current_user, db)` before any
operation that touches station-scoped data. Administrators bypass automatically.

### Identity binding
`performed_by` must always be bound from the JWT server-side (`current_user.email`
or `current_user.oid`). Never trust a client-supplied user identity field.

### Status computation
Check and line-item status are **computed server-side only**. Never accept
status values from the client. Business rules:
- `EXPIRED` beats `MISSING` (conservative compliance)
- One `FAIL` line item → whole check is `FAIL`
- `NEEDS_RESTOCK` is second-worst

### Migrations
- Always use **Alembic batch mode** for ALTER TABLE (SQLite compat required for tests)
- Migration file: `app/alembic/versions/`
- After adding a migration: update the migration count in `CODEBASE_INDEX.md`
- Run: `cd app; alembic upgrade head`

### Tests
- Test DB: SQLite in-memory (conftest.py); no external services needed
- Run: `cd app; pytest`
- Test count target: all tests green before any commit
- When adding a new endpoint, add tests to the appropriate test file
- `test_routers.py` is 67 KB — prefer adding to the domain-specific file
  (`test_repair_requests.py`, `test_check_history.py`, etc.) when one exists

---

## Code Rules — Frontend (React / Vite PWA)

### Module structure
Each module in `src/modules/` is self-contained:
```
modules/my-module/
  index.jsx          # Entry point; orchestration only
  api/               # API call functions (no UI)
  components/        # Sub-components
```

### API calls
Always use `shared/api/client.js` (Axios instance with auth token injector).
Never construct fetch() calls manually in components.

### Auth
Use `useAuth.jsx` hook for user identity and role. Never parse the JWT manually
in a component.

### Draft persistence
`useDraft.js` manages localStorage draft state. Draft key includes `started_at`
to support multiple in-progress checks for the same vehicle on the same day.
Last-known station is cached in localStorage so draft banners show immediately
before the station API returns.

### Environment variables
Frontend env var for API base URL: `VITE_API_BASE_URL`
Check `shared/api/client.js` for how it's consumed. The dev banner
(`DevBanner.jsx`) uses it to detect non-production environments.

### No HTML form tags
Never use `<form>` elements in React components. Use `onClick`/`onChange`
event handlers instead. (Causes submit behavior issues in the PWA.)

### CSS and theming — mandatory rules
1. **Tokens only.** All CSS values must use tokens from `index.css :root` — no hardcoded hex colors, raw rem values, or raw px sizes except for `0`, `1px` borders, and media query breakpoints.
2. **Shared utility classes first.** Before writing custom CSS, check if `index.css` already has a class that does the job: `.ems-card`, `.ems-card--warn/fail/pass`, `.ems-section-head`, `.ems-preview-row`.
3. **Station color is always `var(--station-primary)` / `var(--station-text)`.** Vehicle color is `var(--vehicle-primary)` which inherits station color by default; override via inline style on the component root.
4. **Semantic color tokens for new Session H/I/J features:** `--color-damaged`/`--color-damaged-bg`, `--color-priority`/`--color-priority-bg`, `--color-no-change`/`--color-no-change-bg`.
5. **Module CSS placement.** New styles go in the relevant module CSS file (e.g. `supervisor.css`, `supply-room.css`). Never create a new patch/fix CSS file — if a module doesn't have a CSS file yet, create one. Never create new root-level CSS files in `src/`.

### UX constraints — these are non-negotiable
- Minimum tap target: **60px**
- Design for **60+ year old users** with limited tech comfort (primary persona:
  68-year-old retired police chief on iPhone)
- One task at a time — no multi-panel or multi-step actions on one screen
- Plain English labels — no jargon
- High contrast for bright sunlight readability
- Large text wherever possible

---

## Documentation Rules

### After completing any backlog item
1. Move the item from `docs/backlog.md` to `docs/backlog_completed.md`
2. Update the session complete line at the top of `docs/backlog.md`
3. Update the summary table at the bottom of `docs/backlog.md`
4. Update `docs/project_index.md` if the system state table changes
5. Update `CODEBASE_INDEX.md` if files were added, removed, or significantly changed

### After adding a new migration
Update the migration list in `CODEBASE_INDEX.md` with the new migration number
and a one-line description.

### ADR decisions
If a significant architectural decision is made (new pattern, major tradeoff,
technology choice), write a new ADR in `docs/adr/` following the existing format.

---

## Session Handoff

No handoff files. At the end of every session:
1. Move completed items to `docs/backlog_completed.md`
2. Update session complete line + summary table in `docs/backlog.md`
3. Run `cd app; pytest` and confirm all tests pass
4. Update `CODEBASE_INDEX.md` — file sizes, new files, migration list, flagged items
5. Add any new architectural decisions to CLAUDE.md Key Architectural Decisions table
6. Note incomplete items with 🔄 In progress status in backlog.md

---

## Key Architectural Decisions (quick reference)

| Decision | Rule |
|----------|------|
| Status computation | Server-side only, never from client |
| Identity binding | JWT-bound server-side only |
| Audit writes | Always via `core/audit.py::write_audit_event()` |
| Role constants | Always from `deps.py` — never re-declare locally |
| Station scoping | Always call `require_station_membership()` |
| Draft key | Includes `started_at` — supports multi-draft |
| StationMember.user_id | Email (preferred_username), not OID — see station_members.py |
| Supply room | Uses `LocationType.STATION_SUPPLY_ROOM` — not a fake vehicle |
| Build zip | Always on Linux in CI — Windows paths break Oryx extraction |
| OpenAPI docs | Disabled in production (SEC-2) |
| X-Frame-Options | NOT set on API — set in staticwebapp.config.json (SWA only) |
| Migration booleans | Always use Python `True`/`False` in raw SQL parameters — never `0`/`1`. PostgreSQL rejects integer literals for boolean columns; SQLite accepts them silently. |
| Vehicle on-hand | Computed from last check `quantity_found`, not stock lots. Once items leave the supply room the stock room doesn't track them on the vehicle. `stockQtyMap` removed from compartment card calculations. |
| No Change line items | `buildNoChangeLineItems` skips ALL reading types (MEASUREMENT, FUNCTIONAL, DATE_RECORD). Submitting null reading values → MISSING → FAIL on backend. Reading items must be confirmed inline and merged separately. Mirror: `_compute_line_item_status` in checks.py. |
| Supply room wizard | Pass `{ _supplyRoom: true, location_id, station_id }` as `activeWizard` to launch wizard for supply room. `Step1Vehicle` detects `draft._supplyRoom` and auto-calls `onSelect` with the supply room location, skipping vehicle selection entirely. |
| `station_supply` flag | `Item.station_supply = False` excludes item from supply catalog (SR-B1). Set in seed.py for AED, LUCAS, drug items. FUNCTIONAL items are also excluded by SR-B1 query regardless of flag. |
| Auto-decrement supply room | `_auto_decrement_supply_room` fires in `create_daily_check` only when `payload.vehicle_id` is set — supply room checks (vehicle_id=None) do NOT trigger auto-decrement. Best-effort: depletes to zero, never blocks submission. |

---

## Flagged Technical Debt

Address these when touching the relevant area:

| Item | Location | Action |
|------|----------|--------|
| `ems_readykit_dev.db` committed | `app/` | `git rm --cached app/ems_readykit_dev.db` |
| `deploy.zip` committed | repo root | Add to .gitignore; `git rm --cached deploy.zip` |
| `test_routers.py` | `app/tests/` | 67 KB — split by domain when it next needs major additions |
| `admin/components/VehiclesScreen.jsx` | frontend | 25 KB — extract sub-components when next modified |
| CSS patch files | `frontend/src/` | `module-card-fix.css`, `submitted-screen-patch.css`, `wizard-station.css`, `wizard.css` in src root — consolidate into module CSS files |
| `wizard.css` location | `frontend/src/styles/` | Should be in `modules/check-wizard/` — move when next modified |
| `_damagedOverrides` comment | `modules/check-wizard/components/Step3Items.jsx` | Abandoned approach left as comment artifact — remove on next touch |
