## 1. Code — Refactoring Sprint ✅ COMPLETE 2026-05-27

| # | Item | Status | Notes |
|---|------|--------|-------|
| REF-1 | Extract `_write_audit_event()` to `core/audit.py` | ✅ Done | Every audit write now emits a structured log line |
| REF-2 | Move `_get_vehicle_or_404()` to `deps.py` | ✅ Done | Eliminated duplication in `checks.py` and `repair_requests.py` |
| REF-3 | Move `_ALL_ROLES` / `_SUPERVISOR_PLUS` / `_ADMIN_ONLY` to `deps.py` | ✅ Done | Single source of truth across 9 router files |
| REF-4 | Move `require_station_membership()` to `deps.py` | ✅ Done | Also completes ACC-B10; ready for Session C |
| REF-5 | Consolidate frontend CSS patch files into `src/styles/wizard.css` | ✅ Done | 3 patch files merged; 1 placeholder deleted |
| REF-6 | Standardise `extra={}` logging in `core/auth.py` | ✅ Done | All warning log lines now structured |
| REF-7 | Replace deprecated `HTTP_422_UNPROCESSABLE_ENTITY` constant | ✅ Done | 8 test warnings eliminated |

See backlog_completed.md for full details.