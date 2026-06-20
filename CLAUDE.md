# CLAUDE.md — AI Development Rules for EMS ReadyKit
# Last updated: 2026-06-19 — Session AF closed (PAR-B1, Compliance Calendar, audit timezone test fix; deployed)
# Load alongside CODEBASE_INDEX.md at the start of every session. Compacted 2026-06-19 — same rules, less prose.

---

## Startup protocol
1. Read `CODEBASE_INDEX.md`, then `docs/backlog.md`.
2. Read only files needed for the current task. No speculative reads, no load-the-whole-module.
3. No session handoff files — `backlog.md` is the single source of truth.

## Environment
- Windows 11, PowerShell. Backslash paths. `;` not `&&` for chaining.
- **Never run `pytest` or `alembic` yourself** — ask the user to run and paste output.
- grep: `Select-String`/`findstr` in PowerShell, or `bash_tool` + `grep` if filesystem MCP falls short.

## Paths
| Root | Path |
|---|---|
| Backend | `C:\Users\jinni\source\repos\EMS_ReadyKit\app\ems_readykit\` |
| Frontend | `C:\Users\jinni\source\repos\EMS_ReadyKit\frontend\src\` |
| Docs | `C:\Users\jinni\source\repos\EMS_ReadyKit\docs\` |
| Tests | `C:\Users\jinni\source\repos\EMS_ReadyKit\app\tests\` |

---

## Filesystem rules (critical)

**Never use `filesystem:edit_file`.** Silently fails on Windows CRLF — reports success, shows a valid diff, file on disk is unchanged. Only safe workflow, every file type, no exceptions:
1. `filesystem:read_text_file` the FULL file (not head/tail for the write step)
2. Edit in memory
3. `filesystem:write_file` the FULL file back

Writing back a partial file silently truncates the rest — this has actually happened (Session AE close-out). For large files, edit in bounded chunks via repeated full read → full write, never a partial write.

- **No delete operation** — only `move_file`. Stage removed files in `_session_XX_removed/` at repo root; tell the user to `git rm` at session close.
- New files: `filesystem:write_file` only. Never the sandbox `create_file` tool (writes to the container, not the repo).
- `view_range` on `read_text_file` is unreliable — may silently return from line 1. Fall back to `bash_tool` + `grep -n`.

---

## Backend rules (Python/FastAPI)

- **Shared deps only** — import `ALL_ROLES`, `SUPERVISOR_PLUS`, `ADMIN_ONLY`, `get_current_user`, `require_role`, `get_vehicle_or_404`, `require_station_membership` from `routers/deps.py`. Never redeclare locally.
- **Audit writes** — always `core/audit.py::write_audit_event()`, never inline `AuditEvent(...)`. Kwargs only: `actor=`, `metadata=` (never `performed_by=`/`detail=`).
- **Station scoping** — call `require_station_membership(station_id, current_user, db)` before touching station-scoped data. Admins bypass automatically.
- **Identity** — `performed_by` always server-derived (`current_user.email or current_user.name`). Never trust client-supplied identity.
- **Status computation** — server-side only, never from client. `EXPIRED` > `MISSING`; one `FAIL` line item fails the whole check; `NEEDS_RESTOCK` is second-worst.
- **Rate limiting** — singleton in `core/limiter.py` (not `main.py`, avoids circular import). `TESTING=true` (conftest.py) sets a high limit so tests never trip it.
- **Migrations** — Alembic batch mode always (SQLite compat). After adding one, update the migration table in `CODEBASE_INDEX.md`.
- **Timezone (Session AF)** — `AuditEvent.timestamp` is always `datetime.now(timezone.utc)`. Any test computing a date boundary to compare against it must use `datetime.now(timezone.utc).date()`, never local `date.today()` — the two diverge once local time crosses a UTC midnight boundary (common US evening hours).

### Tests
- Run: `cd app; pytest` (you don't run it — the user does)
- Two fixtures, don't mix: `db` (in-memory SQLite, rolls back per test, default) vs `seeded_db` (read-only, `test_seed_integrity.py` only, skips if dev DB absent, never write to it).
- **`db.commit()` inside any route handler releases the SAVEPOINT** — committed rows are never rolled back for the rest of that pytest session. Implications:
  - Fixtures creating uniquely-constrained rows need get-or-create or per-test-unique naming (`request.node.name`), not fixed names.
  - Tests asserting against a broad/unscoped query (e.g. plain `GET /audit`) must instead scope to data the test itself created (station_id, vehicle_id, etc.) — never assert `== []` against a shared table.
- `TestClient.delete()` doesn't support `json=`/`content=` directly — use `client.request("DELETE", url, content=json.dumps(body), headers={"Content-Type": "application/json"})`.
- Persona files, do not delete: `test_priority_items.py`, `test_persona_responder.py` (Jamie), `test_persona_supervisor.py` (Earl), `test_persona_admin.py` (Jennifer), `test_safety_checks.py`, `test_seed_integrity.py`, `test_usage.py`, `test_damaged_items.py`.
- `test_routers.py` is 67 KB — add to a domain-specific file when one exists instead of growing it further.

---

## Frontend rules (React/Vite PWA)

- Module shape: `index.jsx` (orchestration only) + `api/` + `components/`.
- API calls only via `shared/api/client.js` (Axios + auth injector). Never raw `fetch()` in components.
- Auth only via `useAuth.jsx`. Never parse the JWT manually.
- Drafts: `useDraft.js`, key includes `started_at` (supports multiple in-progress checks/day). Last-known station cached in localStorage so draft banners show before the station API returns.
- `VITE_API_BASE_URL` is the API base env var; `DevBanner.jsx` uses it to detect non-prod.
- **No `<form>` elements ever** — `onClick`/`onChange` only (form submit breaks the PWA).
- **Vehicle shape** — `active: boolean`, `retired_at: string|null`. No `status` field exists. Always filter `v.active === true && !v.retired_at`. Never `v.status === 'ACTIVE'`.
- **Member endpoints** — only `modules/admin/api/membersApi.js` may call `/stations/{id}/members*`. PATCH/DELETE take integer `member_id`, never `user_id` (a person can hold multiple roles as separate rows since ACC-B7). Don't create a second member-CRUD module — that's exactly how the MERGE-1 bug happened (a stale `user_id`-based copy in `adminApi.js`).

### CSS
1. Tokens only — no hardcoded hex/rem/px except `0`, `1px` borders, media breakpoints.
2. Check `index.css` for an existing utility class before writing custom CSS (`.ems-card`, `.ems-card--warn/fail/pass`, `.ems-section-head`, `.ems-preview-row`).
3. Station color = `var(--station-primary)`/`var(--station-text)`; vehicle color = `var(--vehicle-primary)` (inherits station, override inline on root).
4. Semantic tokens: `--color-damaged(-bg)`, `--color-priority(-bg)`, `--color-no-change(-bg)`.
5. New styles go in the module's own CSS file. Never a new patch/fix file; never a new root-level CSS file.
6. **Shared component CSS → `index.css`**, not a module file — otherwise it's missing whenever that module isn't loaded. Confirmed past victims: `.item-combobox`, `.csv-import`, `.settings-section`/`.settings-row`/`.badge`/`.member-*`/`.email-alignment__*`.

### UX constraints (non-negotiable)
60px min tap target · design for 60+ year old users with limited tech comfort · one task per screen · plain English, no jargon · high contrast for sunlight · large text.

---

## Documentation + session close

After completing any backlog item:
1. Move it from `docs/backlog.md` to `docs/backlog_completed.md`.
2. Update `backlog.md`'s header line + summary table.
3. Update `CODEBASE_INDEX.md` if files were added/removed/changed; update its migration table if a migration was added.
4. New architectural decision? Add a row to the table below.

At session close:
1. Ask the user to run `cd app; pytest` — confirm green.
2. Ask the user to run `cd app; ruff check .` and `cd app; black --check .` — fix violations first.
3. Do steps 1–3 above (backlog_completed.md, banners, CODEBASE_INDEX.md).
4. Note any incomplete items as 🔄 In progress in `backlog.md`, don't fake-close a session.

---

## Key architectural decisions

| Decision | Rule |
|---|---|
| Status computation | Server-side only |
| Identity binding | JWT-bound server-side only |
| Audit writes | `core/audit.py::write_audit_event()` always |
| Role constants | From `deps.py` always |
| Station scoping | `require_station_membership()` always |
| Rate limiter | `core/limiter.py`; `TESTING=true` disables in tests |
| Draft key | Includes `started_at` |
| StationMember.user_id | Email, not OID |
| StationMember PATCH/DELETE | `member_id` only, never `user_id`; only `membersApi.js` calls these (Session AE) |
| Member management UI | One screen: Station Administration → Members (`MembersScreen.jsx`); Settings has no member UI (Session AE) |
| Supply room | `LocationType.STATION_SUPPLY_ROOM`, not a fake vehicle |
| Build zip | Always built on Linux in CI — Windows paths break Oryx extraction |
| OpenAPI docs | Disabled in production (SEC-2) |
| X-Frame-Options | Not set on API — set in `staticwebapp.config.json` (SWA only) |
| Migration booleans | Python `True`/`False` in raw SQL params, never `0`/`1` (Postgres rejects ints for bool columns; SQLite doesn't) |
| Vehicle on-hand | From last check's `quantity_found`, not stock lots |
| No Change line items | `buildNoChangeLineItems` skips all reading types (MEASUREMENT/FUNCTIONAL/DATE_RECORD) — null readings → MISSING → FAIL. Mirror: `_compute_line_item_status` in checks.py |
| Supply room wizard | `activeWizard = { _supplyRoom: true, location_id, station_id, selection_label: 'Station Supply Room' }`; `Step1Vehicle` auto-selects on `draft._supplyRoom` |
| `station_supply` flag | `Item.station_supply = False` excludes from supply catalog (SR-B1); FUNCTIONAL items excluded regardless of flag |
| Auto-decrement supply room | `_auto_decrement_supply_room` (SR-B4) — vehicle checks only, best-effort, never blocks submission |
| Supply room reconcile | `_reconcile_supply_room_check` (SR-B5) — `quantity_found` = new absolute truth, FIFO-adjusts StockLot, never raises |
| Supply room creation | `POST /stations/{id}/supply-room` get-or-create (Supervisor+); frontend detects 404 via `e.status === 404` |
| File editing | `write_file` only, full-file read+write, never `edit_file` (see Filesystem rules above) |
| File deletion | `move_file` to `_session_XX_removed/`, then `git rm` at close |
| Vehicle API shape | No `status` field — `v.active === true && !v.retired_at` only |
| Audit timestamp boundary | UTC always — `datetime.now(timezone.utc).date()`, never local `date.today()` (Session AF) |

---

## Flagged technical debt

| Item | Location | Action |
|---|---|---|
| `ems_readykit_dev.db` committed | `app/` | `git rm --cached app/ems_readykit_dev.db` |
| `deploy.zip` committed | repo root | gitignore + `git rm --cached deploy.zip` |
| `test_routers.py` | `app/tests/` | 67 KB — split by domain on next major addition |
| `VehiclesScreen.jsx` | `frontend/.../admin/components/` | 25 KB — extract sub-components on next touch |
| CSS patch files | `frontend/src/` | `module-card-fix.css`, `submitted-screen-patch.css`, `wizard-station.css`, `wizard.css` in src root — consolidate into module files |
| `wizard.css` location | `frontend/src/styles/` | Belongs in `modules/check-wizard/` — move on next touch |
| `_damagedOverrides` comment | `check-wizard/components/Step3Items.jsx` | Dead comment artifact — remove on next touch |
| No tests for MembersScreen/MemberManagementSection | `admin/__tests__/` | TEST-AE1 in backlog.md |
| No tests for ComplianceCalendar.jsx | `supervisor/__tests__/` | TEST-AF1 in backlog.md |
| `_par_level_fix.py` stray file | `app/tests/` | Placeholder, not part of the real suite — safe to delete |
