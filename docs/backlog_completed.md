# EMS ReadyKit — Completed Items
# Last updated: 2026-05-26

---

## Backend — Tests
| # | Item | Completed |
|---|------|-----------|
| B-T1 | Write `TestCheckTypes` class: MEASUREMENT, FUNCTIONAL, DATE_RECORD, DOCUMENT, Jump Bag location | 2026-05-22 |
| B-T2 | Update duplicate check test → `test_multiple_checks_same_vehicle_same_day_all_succeed` | 2026-05-22 |

---

## Backend — Data Models
| # | Item | Completed |
|---|------|-----------|
| B-M0 | Migration 0005: drop `uq_check_vehicle_date`; replace with non-unique `ix_check_vehicle_date` | 2026-05-22 |
| B-M1 | New table: `repair_requests` | 2026-05-23 |
| B-M5 | Alter `vehicles`: add `inactive_reason`, `inactive_since` | 2026-05-23 |
| B-M7 | Alter `daily_inventory_checks`: add `reviewed_by`, `reviewed_at`, `corrective_action` | 2026-05-23 |
| B-M9 | Alter `daily_inventory_checks`: add `deleted_at`, `deleted_by`, `deletion_reason`, `force_deleted` | 2026-05-23 |

---

## Backend — Phase 6 Endpoints
| # | Item | Completed |
|---|------|-----------|
| B-E0 | `GET /api/v1/stations/{id}/locations` — list checkable non-vehicle locations | 2026-05-22 |
| B-E1 | `PATCH /vehicles/{id}` — mark vehicle active/inactive | 2026-05-23 |
| B-E2 | `PATCH /checks/daily/{id}/acknowledge` — supervisor corrective action | 2026-05-23 |
| B-E4 | `POST /vehicles/{id}/repair-requests` — file repair request | 2026-05-23 |
| B-E16 | `PATCH /vehicles/{id}/repair-requests/{rid}` — update repair request status | 2026-05-23 |
| B-E17 | `GET /vehicles/{id}/repair-requests` — list repair requests for vehicle | 2026-05-23 |

---

## Backend — Check History Endpoints
| # | Item | Completed |
|---|------|-----------|
| CH-B1 | `GET /checks/daily/my-history` — current user's submitted checks | 2026-05-23 |
| CH-B2 | `GET /checks/daily/{id}/detail` — full check detail with RBAC scoping | 2026-05-23 |
| CH-B3 | `DELETE /checks/daily/{id}` — soft-delete with mandatory reason | 2026-05-23 |

---

## Frontend — Phase 5E / Vehicle & Equipment Status
| # | Item | Completed |
|---|------|-----------|
| F-5E1 | Repair request form — severity selector, description, URGENT escalation | 2026-05-23 |
| F-5E2 | Mark vehicle inactive toggle (Supervisor+) | 2026-05-23 |
| F-5E3 | Repair request status tracking display | 2026-05-23 |
| VE-F1 | Rename "Vehicle Status" → "Vehicle & Equipment Status" throughout app | 2026-05-23 |

---

## Frontend — Check History
| # | Item | Completed |
|---|------|-----------|
| CH-F1 | "My Checks" screen — user's submitted checks grouped by date | 2026-05-23 |
| CH-F2 | Check detail view (read-only for Responders) | 2026-05-23 |
| CH-F3 | Show supervisor acknowledgement on check detail | 2026-05-23 |
| CH-F4 | Supervisor check history list — filterable by status | 2026-05-23 |
| CH-F5 | Soft-delete check (Supervisor+) — mandatory reason, 90-day warning | 2026-05-23 |

---

## Frontend — Check Wizard UX
| # | Item | Completed |
|---|------|-----------|
| F-UX1 | Station picker on home screen | 2026-05-16 |
| F-UX11 | Discard check button with confirmation modal | 2026-05-21 |
| F-UX12 | Three-tier item row color (green/yellow/red) | 2026-05-21 |
| F-UX13 | Surface short/fail on Step 2 compartment badges | 2026-05-21 |
| F-UX14 | Save compartment force-confirms all touched items | 2026-05-21 |
| F-UX15 | Jump bag / portable cards on Step 1 | 2026-05-21 |
| F-UX16 | One jump bag per ambulance with alpha-sort grouping | 2026-05-21 |
| F-UX17 | Step 4 Reconcile — interactive shopping list with share/copy | 2026-05-22 |
| F-UX18 | Wizard renumbered to 5 steps | 2026-05-22 |
| F-UX19 | Step 2 button label: "Reconcile →" vs "Review and Submit →" | 2026-05-22 |
| F-UX20 | Step 5 back button routes to Reconcile or Compartments intelligently | 2026-05-22 |
| F-UX21 | Minimal test unit (Unit TEST QRV) — all check types in < 5 min | 2026-05-22 |
| F-UX22 | Bug fix: Reconcile routing for fail-only checks | 2026-05-22 |
| F-UX23 | Bug fix: Check date blank on Step 5 | 2026-05-22 |
| F-UX24 | Bug fix: Overall status always showed Pass | 2026-05-22 |
| F-UX25 | Bug fix: Repair needed auto-selected and pre-filled from fail items | 2026-05-22 |
| F-UX26 | Bug fix: Repair notes showed "Unknown compartment" | 2026-05-22 |
| F-UX27 | DATE_RECORD "Today" button — one tap sets date and locks card | 2026-05-22 |
| F-UX28 | Multiple checks per day — draft key uses started_at; home screen groups drafts with picker modal | 2026-05-22 |
| F-UX29 | Backend: drop uq_check_vehicle_date; remove 409 guard; allow unlimited checks per day | 2026-05-22 |
| F-UX30 | DraftBanner uses selection_label — fixes null label for jump bag checks | 2026-05-22 |
| F-UX31 | Reconcile "Add N" top-off button — inline with +/− controls | 2026-05-22 |
| F-UX33 | FAIL check → repair request prompt on submitted screen | 2026-05-23 |

---

## Frontend — Phase 5H: Infrastructure
| # | Item | Completed |
|---|------|-----------|
| F-5H1 | Terraform module: Azure Static Web Apps (centralus) | 2026-05-24 |
| F-5H2 | GitHub Actions 4-job pipeline: test-backend, build-frontend, deploy-backend, deploy-frontend | 2026-05-24 |
| F-5H3 | SWA URL added to CORS allowed origins (Terraform app module) | 2026-05-24 |
| F-5H4 | SWA URL registered as SPA redirect URI in Azure AD | 2026-05-24 |

---

## Infrastructure / Security
| # | Item | Completed |
|---|------|-----------|
| I-7 | Confirm Azure deployment healthy — App Service B1, VNet integration, CI/CD green | 2026-05-24 |

---

## Documentation
| # | Item | Completed |
|---|------|-----------|
| D-1 | Update `project_index.md` ADR table (ADR-006 slot) | 2026-05-22 |

---

## Session A — Security Gate (2026-05-26)

All items completed in one session. 153 tests pass. pip-audit reports 0 known vulnerabilities.

### Dead Code Removal
| # | Item | Completed |
|---|------|-----------|
| — | Delete `routers/_patch_cs_message.py` — dangling code snippet, not imported anywhere | 2026-05-26 |
| — | Delete `routers/_patch_get_check.py` — dangling code snippet, not imported anywhere | 2026-05-26 |
| — | Remove `tests/test_rbac_block.py` stub — contained only a "delete me" comment | 2026-05-26 |

### Gitignore
| # | Item | Completed |
|---|------|-----------|
| — | Add `ems_readykit_dev.db` to `.gitignore` | 2026-05-26 |
| — | Add `deploy.zip` to `.gitignore` | 2026-05-26 |

### Security — OWASP A06: pip-audit in CI
| # | Item | Completed |
|---|------|-----------|
| SEC-1 | Add `pip-audit` step to `.github/workflows/deploy.yml` before pytest — fails build on known CVEs | 2026-05-26 |

### Security — OWASP A05: Security Misconfiguration
| # | Item | Completed |
|---|------|-----------|
| SEC-2 | Disable OpenAPI `/docs`, `/redoc`, `/openapi.json` in production (`main.py`) | 2026-05-26 |
| SEC-3 | Add security headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy` | 2026-05-26 |

### Security — OWASP A02: Cryptographic Failures
| # | Item | Completed |
|---|------|-----------|
| SEC-4 | Startup assertion: fail loud if `SECRET_KEY == "change-me-in-production"` in production | 2026-05-26 |

### Security — OWASP A09: Logging and Monitoring
| # | Item | Completed |
|---|------|-----------|
| SEC-5a | Structured `logger` calls added to `inventory.py` — all POST mutations | 2026-05-26 |
| SEC-5b | Structured `logger` calls added to `stations.py` — POST mutations | 2026-05-26 |
| SEC-5c | Structured `logger` calls added to `vehicles.py` — POST mutations | 2026-05-26 |
| SEC-5d | Structured `logger` calls added to `items.py` — POST mutations | 2026-05-26 |

### Security — OWASP A04: Insecure Design
| # | Item | Completed |
|---|------|-----------|
| SEC-6 | Document `secondary_signer` free-text limitation in `checks.py` with OWASP A04 comment | 2026-05-26 |

### Dependency Upgrades (resolving all pip-audit CVEs)
| # | Package | From | To | CVEs resolved | Completed |
|---|---------|------|----|---------------|-----------|
| — | `fastapi` | 0.111.0 | 0.136.1 | Unlocks starlette 1.x | 2026-05-26 |
| — | `starlette` | 0.37.2 | 1.1.0 | CVE-2024-47874, CVE-2025-54121, CVE-2025-62727, PYSEC-2026-161 | 2026-05-26 |
| — | `pydantic` | 2.7.1 | 2.13.4 | Required by fastapi 0.136.1 | 2026-05-26 |
| — | `pydantic-settings` | 2.2.1 | 2.14.1 | Required by pydantic 2.13.4 | 2026-05-26 |
| — | `azure-identity` | 1.16.0 | 1.19.0 | CVE-2024-35255 | 2026-05-26 |
| — | `PyJWT` | 2.8.0 | 2.12.0 | PYSEC-2026-120, PYSEC-2025-183 | 2026-05-26 |
| — | `cryptography` | 42.0.8 | 46.0.7 | CVE-2024-12797, CVE-2026-26007, GHSA-h4gh-qq45-vh27, PYSEC-2026-35, PYSEC-2026-36 | 2026-05-26 |
| — | `pytest` | 8.2.0 | 9.0.3 | CVE-2025-71176 | 2026-05-26 |
| — | `pytest-asyncio` | 0.23.6 | removed | Unused (zero async tests); conflicted with pytest 9 | 2026-05-26 |

### Bug Fix
| # | Item | Completed |
|---|------|-----------|
| — | Supervisor "All Checks" tab was calling `getMyHistory` (filtered by current user) instead of `getStationChecksToday` — PASS checks from other crew members were invisible | 2026-05-26 |
