# EMS ReadyKit — Active Backlog
# v1.19 | Updated: 2026-05-23
# Completed items → backlog_completed.md
# Priority: High / Medium / Low | Status: 📋 Not started | 🔄 In progress | ⛔ Blocked

# ✅ SESSION COMPLETE 2026-05-23
# See backlog_completed.md for full list.
# Key items completed this session:
#   - CI/CD fixed, app live in Azure
#   - Migrations 0006 + 0007, 9 endpoints, 151 tests passing
#   - Vehicle & Equipment Status frontend (F-5E1/2/3, VE-F1)
#   - Check History frontend (CH-F1/2/3/4/5)
#   - FAIL check → repair request flow (F-UX33)
#     SubmittedScreen now shows outcome-appropriate content:
#       PASS → "cleared for service"
#       NEEDS_RESTOCK → "can go out, restock when possible"
#       FAIL → never says cleared; prominent "File Repair Request Now" button
#
# NEXT SESSION: Commit everything, then Phase 5H (Azure Static Web Apps).
# F-5H1 → F-5H4: Terraform module + GitHub Actions deploy job.
# After 5H: Supervisor Dashboard (F-5F1, F-5F3/4/5/7).

---

## 1. Backend — Phase 6 Endpoints
| # | Endpoint | Description | Pri | Status | Needs |
|---|----------|-------------|-----|--------|-------|
| B-E3 | `GET /checks/daily/station/{id}?from=&to=` | Date-range compliance query | High | 📋 | |
| B-E5 | `POST /inventory/transfer` | Move stock between supply room and vehicle | High | 📋 | |
| B-E6 | `GET /inventory/locations/{id}/stock-summary` | Stock vs par per item | High | 📋 | |
| B-E7 | `GET /stations/{id}/users` | Active users at station via MS Graph | Medium | 📋 | |
| B-E8 | `PUT /inventory/lots/{id}` | Supervisor corrects expiry date on lot | Medium | 📋 | |
| B-E9 | `PATCH /inventory/par-levels/{id}` | Soft-deactivate par level | Medium | 📋 | |
| B-E10 | `POST /feedback` | Submit bug/enhancement/general feedback | Medium | 📋 | |
| B-E11 | `GET /feedback` | List feedback (Administrator only) | Medium | 📋 | |
| B-E12 | `GET /notifications` | Unread notifications scoped by role | Medium | 📋 | |
| B-E13 | `PATCH /notifications/{id}/read` | Mark notification read | Medium | 📋 | |
| B-E14 | `POST /admin/user-requests` | Supervisor submits user onboarding request | Medium | 📋 | |
| B-E15 | `GET /admin/user-requests` | List user requests (Administrator only) | Medium | 📋 | |
| B-E18 | `GET /audit?from=&to=` | Date-range audit export | Medium | 📋 | |

*All paths prefixed `/api/v1/`*

---

## 2. Backend — Data Models
| # | Item | Pri | Status |
|---|------|-----|--------|
| B-M2 | New table: `notifications` | Medium | 📋 |
| B-M3 | New table: `feedback_entries` | Medium | 📋 |
| B-M4 | New table: `user_requests` | Medium | 📋 |
| B-M6 | Alter `par_levels`: add `active`, `deactivated_at`, `deactivation_reason` | Medium | 📋 |
| B-M8 | Alter `daily_inventory_checks`: add `started_by` (check handoff) | Medium | 📋 |
| B-M10 | Alter `stations`: add `allow_check_modification` (Boolean, default False) | High | 📋 |
| B-M11 | Alter `stations`: add `primary_color` (String, nullable) | Medium | 📋 |
| B-M12 | New table: `user_preferences` | Medium | 📋 |
| B-M13 | Alter `inventory_lots`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| B-M14 | New table: `loaned_items` | Medium | 📋 |
| RET-M1 | Alter `vehicles`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M2 | Alter `locations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M3 | Alter `stations`: add `retired_at`, `retired_by`, `retirement_reason` | High | 📋 |
| RET-M4 | Scheduled nightly job: hard-delete retired objects where `retired_at` > 5 yrs | High | 📋 |

---

## 3. Backend — Code Quality
| # | Item | Pri | Status |
|---|------|-----|--------|
| B-Q1 | Structured `logger` calls in `inventory.py`, `stations.py`, `vehicles.py`, `items.py` | Medium | 📋 |
| B-Q2 | Standardise `extra={}` logging shape in `core/auth.py` | Low | 📋 |

---

## 4. Backend — Check History Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| CH-B4 | `DELETE /checks/daily/{id}/force` | Administrator force hard-delete (PII spill) | High | 📋 | Admin only |
| CH-B5 | `GET /checks/daily/deleted?station_id=` | List soft-deleted checks within 90-day window | Medium | 📋 | Admin only |
| CH-B6 | `PATCH /checks/daily/{id}/restore` | Restore soft-deleted check within 90-day window | Low | 📋 | Admin only |
| CH-B7 | `PATCH /stations/{id}/settings` | Update station settings incl. `allow_check_modification` | High | 📋 | Admin only |
| CH-B8 | `GET /stations/{id}/settings` | Read station settings | High | 📋 | Supervisor+ |

---

## 5. Backend — Retirement Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| RET-B1 | `PATCH /vehicles/{id}/retire` | Retire vehicle | High | 📋 | Supervisor+ |
| RET-B2 | `PATCH /locations/{id}/retire` | Retire jump bag / portable location | High | 📋 | Supervisor+ |
| RET-B3 | `PATCH /stations/{id}/retire` | Retire station | High | 📋 | Admin only |
| RET-B4 | `GET /admin/retired?type=&station_id=` | List retired objects | Medium | 📋 | Admin only |
| RET-B5 | `PATCH /inventory/lots/{id}/retire` | Retire a specific lot | High | 📋 | Supervisor+; needs B-M13 |
| RET-B6 | `GET /inventory/lots/retired?location_id=` | List retired lots | Medium | 📋 | Supervisor+ |

---

## 6. Backend — Loaned Item Endpoints
| # | Endpoint | Description | Pri | Status | Notes |
|---|----------|-------------|-----|--------|-------|
| LOAN-B1 | `POST /equipment/loans` | Record a loan | Medium | 📋 | All roles; needs B-M14 |
| LOAN-B2 | `PATCH /equipment/loans/{id}/resolve` | Mark loan resolved | Medium | 📋 | All roles |
| LOAN-B3 | `GET /equipment/loans?vehicle_id=&resolved=false` | Open loans for a vehicle | Medium | 📋 | Supervisor+ |
| LOAN-B4 | `GET /equipment/loans/my?resolved=false` | Current user's open loans | Medium | 📋 | All roles |

---

## 7. Frontend — Phase 5C: Help System
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5C1 | First-run tutorial — 8 steps, auto-shown on first login, replayable, skip button | High | 📋 |
| F-5C2 | Contextual "?" help — bottom sheet per wizard step | High | 📋 |
| F-5C3 | Searchable FAQ — client-side filter, crew + supervisor sections, 15 questions | Medium | 📋 |
| F-5C4 | `src/modules/help/content.js` — single source of truth for all help text | Medium | 📋 |

---

## 8. Frontend — Phase 5D: Item Management
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5D1 | Item catalog search component | Medium | 📋 |
| F-5D2 | Add item form — Responder requests; Supervisor/Admin adds directly | Medium | 📋 |
| F-5D3 | Remove item with mandatory documented reason | Medium | 📋 |

---

## 9. Frontend — V&E Status (remaining)
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| VE-F2 | Open loans panel — unresolved loans per vehicle; Resolve button per row | Medium | 📋 | LOAN-B3 |
| VE-F3 | Log a loan form — lot picker + destination note field | Medium | 📋 | LOAN-B1 |
| VE-F4 | Resolve loan modal — optional note, calls LOAN-B2 | Medium | 📋 | LOAN-B2 |

---

## 10. Frontend — Phase 5F: Supervisor Dashboard
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-5F1 | Supervisor landing — today's compliance summary and active alerts | High | 📋 | |
| F-5F2 | Monthly compliance calendar — color-coded per vehicle per day | High | ⛔ | B-E3 |
| F-5F3 | Check detail view — all line items, lot numbers, expiry dates | High | 📋 | |
| F-5F4 | Print layout — legally defensible record with chain of custody + signature lines | High | 📋 | |
| F-5F5 | Supervisor acknowledgement + corrective action on FAIL checks | High | 📋 | |
| F-5F6 | Notification bell with unread badge | Medium | ⛔ | B-E12 |
| F-5F7 | Supply room stock view (stock vs par, color coded, reorder form) | Medium | 📋 | |

---

## 11. Frontend — Phase 5G: Supporting Modules
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-5G1 | Feedback module — floating button, bug/enhancement/general form | Medium | 📋 | |
| F-5G2 | User management module | Medium | ⛔ | B-E14 |
| F-5G3 | Data export — CSV for check history, audit events, repair requests | Medium | 📋 | |
| F-5G4 | Role switcher (crew mode for supervisors) — amber CREW MODE badge | Low | 📋 | |

---

## 12. Frontend — Phase 5H: Infrastructure
| # | Item | Pri | Status |
|---|------|-----|--------|
| F-5H1 | Terraform module: Azure Static Web Apps | High | 📋 |
| F-5H2 | GitHub Actions frontend build + deploy job | High | 📋 |
| F-5H3 | Add Static Web App URL to CORS allowed origins (Terraform) | High | 📋 |
| F-5H4 | Register Static Web App URL as SPA redirect URI in Azure AD | High | 📋 |

---

## 13. Frontend — Check Wizard UX
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| F-UX2 | Left/right chevron navigation between compartments | Medium | 📋 | |
| F-UX3 | "Jump to unvalidated" sticky button | Medium | 📋 | |
| F-UX4 | Expired item replacement prompt | Medium | 📋 | |
| F-UX5 | Check handoff support | Medium | ⛔ | B-M8 |
| F-UX6 | Compartment location descriptor on cards | Medium | 📋 | |
| F-UX7 | "Last checked today" indicator on vehicle cards | High | 📋 | |
| F-UX8 | Item count on compartment cards | Low | 📋 | |
| F-UX9 | Two-state submit with offline queue | Low | 📋 | |
| F-UX10 | "Caller/spotter view" large-text mode | Low | 📋 | |
| F-UX32 | BORROWED badge on loaned items during check; shortcut to V&E Status | Medium | 📋 | B-M14 |

---

## 14. Frontend — Check History (remaining)
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| CH-F6 | Acknowledgement / corrective note on submitted check | High | ⛔ | B-M10, CH-B8 |
| CH-F7 | Deleted records screen (Admin) — restore or force hard-delete | High | 📋 | |
| CH-F8 | Force hard-delete confirmation — type "PERMANENTLY DELETE" to confirm | High | 📋 | |

---

## 15. Frontend — Settings Module
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| S-F1 | Settings nav entry — role-scoped visibility | High | 📋 | |
| S-F2 | Station color picker (Supervisor+) — live preview | Medium | 📋 | B-M11 |
| S-F3 | Allow check modification toggle (Admin only) | High | 📋 | B-M10 |
| S-F4 | Default station selector (all roles) | Medium | 📋 | B-M12 |
| S-F5 | Display name / preferred name override (all roles) | Low | 📋 | B-M12 |
| S-F6 | Station management — create, edit, retire | High | 📋 | RET-B3/B4 |
| S-F7 | Vehicle / portable equipment management — add, edit, retire | High | 📋 | RET-B1/B2 |
| S-F8 | Par level management — view and edit per vehicle/compartment | Medium | 📋 | B-E9 |
| S-F9 | User onboarding management — approve/reject, assign role + station | Medium | 📋 | B-E14/15 |

---

## 16. Frontend — Retirement Actions
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| RET-F1 | Retire vehicle (Supervisor+) | High | 📋 | RET-B1 |
| RET-F2 | Retire jump bag / portable location (Supervisor+) | High | 📋 | RET-B2 |
| RET-F3 | Retire inventory lot (Supervisor+) | High | 📋 | RET-B5, B-M13 |
| RET-F4 | Retire station (Admin only) | High | 📋 | RET-B3 |
| RET-F5 | Retired objects list (Admin) — filterable by type, read-only | Medium | 📋 | RET-B4 |

---

## 17. Infrastructure / Security
| # | Item | Pri | Status | Needs |
|---|------|-----|--------|-------|
| I-1 | Azure Firewall in `modules/network` with UDR + FQDN allow-list | Medium | 📋 | |
| I-2 | Re-add route table to subnets | Medium | ⛔ | I-1 |
| I-3 | `HTTPSRedirectMiddleware` in `main.py` (production-gated) | Low | 📋 | |
| I-4 | `X-Content-Type-Options` and `X-Frame-Options` headers | Low | 📋 | |
| I-5 | Document Azure AD token lifetime; confirm CAE enabled | Low | 📋 | |
| I-6 | Write `docs/adr/ADR-006-DDoS-Strategy.md` | Low | 📋 | |

---

## 18. Documentation
| # | Item | Pri | Status | Notes |
|---|------|-----|--------|-------|
| D-R1 | **Documentation audit** — full review of all existing and planned docs | High | 📋 | See criteria below |

### D-R1 Criteria
Review every file in `docs/` plus `README.md` against these questions:

**Value:**
- Does this document need to exist, or does it duplicate something better expressed in code/tests?
- Does it add value to the application (operational reference)?
- Does it add value to the portfolio (demonstrates enterprise engineering judgment)?
- Could two documents be merged without losing anything?

**Security best practices (enterprise cloud standard):**
- Does `docs/security.md` cover: auth model, RBAC matrix, token lifecycle, encryption at rest/in transit, secrets management, audit log schema, threat model, incident response?
- Do ADRs document security decisions and their rationale (e.g. why Azure AD over custom auth)?
- Is the data retention policy (`docs/data_retention_policy.md`) defensible for a healthcare-adjacent system?
- Is the PII emergency procedure in `docs/operations.md` complete and unambiguous?

**Portfolio signal (enterprise cloud software engineer):**
- Does `README.md` lead with the problem being solved, not the tech stack?
- Is the architecture documented at the right level — decision-oriented (ADRs) rather than just descriptive?
- Does the documentation demonstrate you understand the full lifecycle: design → build → deploy → operate → retire?
- Is there a clear separation between what the system does now vs. what's planned?

**Quality:**
- Is every document precise, concise, and free of filler?
- Are there sections that exist only because "docs should have this" rather than because someone will read them?
- Is the tone consistent — professional but not bureaucratic?
- Are all code examples and command snippets correct and tested?

**Output of the review:**
- List of docs to keep as-is
- List of docs to rewrite (with specific issues)
- List of docs to merge
- List of planned docs to drop entirely
- List of gaps that genuinely need filling (especially security)

---

## 19. Open Questions
| # | Question | Owner |
|---|----------|-------|
| Q-1 | Notification delivery: email (Azure Comms) or in-app only? | Project owner |
| Q-2 | MS Graph user lookup: cache in DB? | Engineering |
| Q-3 | 90-day max range sufficient for compliance calendar? | Project owner |
| Q-4 | BLOCKING feedback bugs auto-create GitHub issue? | Project owner |
| Q-5 | Supply room reorder tracking: Phase 6 or defer to Phase 7? | Project owner |
| Q-6 | Auto-hard-delete scheduler (90-day checks + 5-yr retired): Azure Function or startup cleanup job? | Engineering |
| Q-7 | Check modification setting default: False (conservative) or True (permissive)? | Project owner |
| Q-8 | Restored soft-deleted checks: visible in responder history, or admin screen only? | Project owner |
| Q-9 | 5-year hard-delete job: share mechanism with Q-6 or separate process? | Engineering |

---

## Summary
| Area | 📋 | ⛔ | Total |
|------|----|----|-------|
| Backend — Phase 6 Endpoints | 13 | 0 | 13 |
| Backend — Data Models | 14 | 0 | 14 |
| Backend — Code Quality | 2 | 0 | 2 |
| Backend — Check History | 5 | 0 | 5 |
| Backend — Retirement | 6 | 0 | 6 |
| Backend — Loaned Items | 4 | 0 | 4 |
| Frontend — Phase 5C Help | 4 | 0 | 4 |
| Frontend — Phase 5D Item Mgmt | 3 | 0 | 3 |
| Frontend — V&E Status (remaining) | 3 | 0 | 3 |
| Frontend — Phase 5F Supervisor | 5 | 2 | 7 |
| Frontend — Phase 5G Supporting | 3 | 1 | 4 |
| Frontend — Phase 5H Infra | 4 | 0 | 4 |
| Frontend — Check Wizard UX | 10 | 1 | 11 |
| Frontend — Check History (remaining) | 2 | 1 | 3 |
| Frontend — Settings | 9 | 0 | 9 |
| Frontend — Retirement Actions | 5 | 0 | 5 |
| Infrastructure / Security | 5 | 1 | 6 |
| Documentation | 1 | 0 | 1 |
| **Total** | **113** | **6** | **119** |
