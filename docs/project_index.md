# EMS ReadyKit — Project Documentation Index
# Document version: 1.0
# Last updated: 2026-05-15

---

## Project Overview

EMS ReadyKit is a cloud-native inventory and vehicle readiness platform modeled
for a small Fire and EMS organization. It demonstrates Infrastructure-as-Code
discipline, role-based access control, operational observability, domain modeling,
and cost-aware architectural decision-making. The system is a technical
demonstration; it does not process patient data and is not a live operational
deployment.

**Live URL:** https://app-ems-readykit-dev.azurewebsites.net
**Repository:** https://github.com/Jinniyah/EMS_ReadyKit
**CI/CD status:** See README badge

---

## Documentation Standards

All phase documents follow this standard structure:
1. Executive Summary — one paragraph; what was built and why
2. Objectives — table of measurable goals
3. Scope — explicit in/out of scope
4. Technical Decisions — key design choices with rationale
5. Deliverables — table with location and completion status
6. Testing — test strategy and results
7. Known Issues and Tradeoffs — honest accounting of limitations
8. Phase Dependencies — what this phase requires and provides
9. Next Phase — brief forward pointer

---

## Phase Documents

| Phase | Document | Status | Description |
|-------|----------|--------|-------------|
| Phase 1 | `phase1_platform_foundation.md` | ✅ Complete | Azure infrastructure, Terraform modules, RBAC, logging, governance |
| Phase 2 | `phase2_backend_api.md` | ✅ Complete | FastAPI application, domain model, REST endpoints, 74 automated tests |
| Phase 3 | `phase3_auth_cicd.md` | ✅ Complete | Azure AD JWT auth, RBAC enforcement, GitHub Actions CI/CD pipeline |
| Phase 4 | `phase4_compartments_line_items.md` | ✅ Complete | Compartment model, check line items, expiration tracking, lot validation |
| Phase 5 | `phase5_frontend_pwa.md` | 📋 Planned | Progressive Web App — check wizard, supervisor dashboard, help system |
| Phase 6 | `phase6_backend_extensions.md` | 📋 Planned | Backend extensions for Phase 5 supervisor, management, and notification modules |

**Session handoff:** `session_handoff_2026-05-15.md` — complete state snapshot, next steps, prompt for next session

---

## Architecture Decision Records

| ADR | Document | Status | Decision |
|-----|----------|--------|----------|
| ADR-001 | `adr/ADR-001-Architecture.md` | Accepted | Single-app, single-datastore, single-region architecture |
| ADR-002 | `adr/ADR-002-RBAC.md` | Accepted | Group-based Azure AD RBAC + application-layer authorization |
| ADR-003 | `adr/ADR-003-Logging-and-Audit.md` | Accepted | Centralized Log Analytics + explicit audit events |
| ADR-004 | `adr/ADR-004-Terraform-Module-Structure.md` | Accepted | Modular Terraform organized by architectural responsibility |

---

## Supporting Documents

| Document | Purpose |
|----------|---------|
| `Requirements.md` | Functional and non-functional requirements; project framing |
| `architecture.md` | Architecture diagram (Mermaid) with component relationships |
| `runbook.md` | Deployment, validation, and teardown procedures |
| `help_content.md` | All tutorial, FAQ, and contextual help text (single source of truth) |
| `req_build_order_plan.txt` | Original build sequence planning notes |
| `req_final_domain_model.txt` | Original domain model definition |
| `req_user_stories.txt` | User stories by role |
| `req_security.txt` | Security and monitoring requirements |
| `req_terraform_layout.txt` | Terraform design notes |
| `req_cost_estimates.txt` | Monthly cost breakdown and cost control strategy |
| `phase3_auth_todo.md` | Phase 3 implementation checklist (historical reference) |

---

## Current System State

### What is deployed and running

| Component | Status | Notes |
|-----------|--------|-------|
| Azure infrastructure (Phase 1) | ✅ Live | North Central US; F1 tier |
| FastAPI backend (Phase 2) | ✅ Live | https://app-ems-readykit-dev.azurewebsites.net |
| Azure AD authentication (Phase 3) | ✅ Live | RS256 JWT; three app roles |
| RBAC enforcement (Phase 3) | ✅ Live | All endpoints protected |
| GitHub Actions CI/CD (Phase 3) | ✅ Live | Test → Build → Deploy on push to main |
| Compartments and line items (Phase 4) | ✅ Live | Alembic migration 0002 applied |
| Expiration tracking (Phase 4) | ✅ Live | EXPIRED status on check line items |
| Frontend PWA (Phase 5) | ❌ Not started | Planning complete |
| Backend extensions (Phase 6) | ❌ Not started | Planning complete |

### Test suite status

| Metric | Value |
|--------|-------|
| Total tests | 90 |
| Passing | 90 |
| Failing | 0 |
| Runtime | ~1.66 seconds |
| Coverage areas | Models, routers, schema validation, RBAC, compartments, line items, expiration |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Cloud platform | Microsoft Azure |
| IaC | Terraform |
| Backend framework | FastAPI 0.111.0 |
| ORM | SQLAlchemy 2.0.30 |
| Database migrations | Alembic 1.13.1 |
| Schema validation | Pydantic 2.7.1 |
| Database | PostgreSQL 16 (Azure Flexible Server) |
| Runtime | Python 3.11.15 |
| ASGI server | Gunicorn + UvicornWorker |
| Authentication | Azure Active Directory (RS256 JWT) |
| CI/CD | GitHub Actions |
| Frontend (planned) | React PWA + MSAL |
| Frontend hosting (planned) | Azure Static Web Apps |
| Testing | pytest + pytest-asyncio + Starlette TestClient |

---

## Role Summary

| Role | Platform scope | Application scope |
|------|---------------|------------------|
| Administrator | Subscription-level Reader | Full access — create stations, vehicles, items, par levels |
| Supervisor | Resource group Contributor | Station-level — manage inventory, review checks, approve requests |
| Responder | Authenticated access only | Vehicle-level — submit checks, read items and inventory |

---

## Key Design Decisions Summary

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| Monolithic API over microservices | Reduced complexity; appropriate for small domain | ADR-001 |
| Single region | Cost and complexity justified | ADR-001 |
| Group-based RBAC | No user-level assignments; real enterprise pattern | ADR-002 |
| Explicit audit events (not DB-derived) | Preserves actor intent; compliance-grade audit | ADR-003 |
| Terraform modular structure | IaC maturity; separation of concerns; reproducible | ADR-004 |
| PostgreSQL over Azure SQL | Open-source; lower cost; SQLAlchemy alignment | Phase 1 |
| F1 → B1 upgrade path | F1 zero-cost for dev; B1 one variable change | Phase 1 |
| Status computed server-side (immutable) | Tamper-resistant; enforces correct semantics | Phase 4 |
| EXPIRED takes priority over MISSING | Conservative compliance; field safety | Phase 4 |
| Linux zip build in CI/CD | Eliminates Windows backslash path issue permanently | Phase 3 |
| localStorage offline draft | Never lose work mid-check; submit on completion only | Phase 5 |
| Modular React architecture | Module failures are isolated; app never fully crashes | Phase 5 |
| Validate button per item | Ensures every item is explicitly acknowledged | Phase 5 |
| Client-side CSV generation | No server-side export endpoint needed; simpler architecture | Phase 5 |
| UTF-8 BOM on CSV download | Ensures correct rendering in Excel without manual re-encoding | Phase 5 |

---

## Phase 6 Backend Backlog (Prioritized)

| Priority | Endpoint | Required by |
|----------|----------|-------------|
| High | PATCH /api/v1/vehicles/{id} | Vehicle inactive/active module |
| High | PATCH /api/v1/checks/daily/{id}/acknowledge | Supervisor FAIL check workflow |
| High | GET /api/v1/checks/daily/station/{id}?from=&to= | Compliance calendar + CSV export |
| High | POST /api/v1/vehicles/{id}/repair-requests | Vehicle repair reporting |
| Medium | GET /api/v1/stations/{id}/users | Second crew picker; shift context |
| Medium | PUT /api/v1/inventory/lots/{id} | Supervisor expiry correction |
| Medium | PATCH /api/v1/inventory/par-levels/{id} | Par level deactivation (item removal) |
| Medium | POST /api/v1/feedback | Feedback module |
| Medium | GET/PATCH /api/v1/notifications | Notification module |
| Medium | POST /api/v1/admin/user-requests | User onboarding request |
| Medium | GET /api/v1/audit?from=&to= (date filter) | Audit event CSV export |
| Medium | GET /api/v1/vehicles/{id}/repair-requests | Repair request CSV export |
| High | POST /api/v1/inventory/transfer | Supply room restock during check |
| High | GET /api/v1/inventory/locations/{id}/stock-summary | Supply room stock vs par view |

---

## Data Export Summary

Module 7 (Data Export) provides on-demand CSV downloads scoped by role:

| Dataset | Supervisor scope | Administrator scope | Phase 6 endpoint needed? |
|---------|-----------------|--------------------|--------------------------|
| Daily check history | Own station | All stations | Yes — date range filter |
| Check line items | Included in check response | Included | No — already in response |
| Controlled substance checks | Own station vehicles | All vehicles | No — exists per vehicle |
| Stock lots / inventory | Own station locations | All locations | No — exists per location |
| Expiring lots | Own station | All | No — exists |
| Items catalog | Global (read-only) | Global | No — exists |
| Par levels | Own station | All | No — exists per location |
| Audit events | Own station | All | Yes — date range filter |
| Repair requests | Own station vehicles | All vehicles | Yes — new endpoint |

**CSV format:** UTF-8 with BOM, RFC 4180, ISO 8601 dates, blank empty fields.
**Generation:** Client-side from API response data (`utils/csvBuilder.js`).
**Download trigger:** Browser file download via `utils/csvDownload.js`.
**Filename:** `{dataset}_{scope}_{from}_to_{to}.csv`
