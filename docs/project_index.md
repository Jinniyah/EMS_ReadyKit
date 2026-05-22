# EMS ReadyKit — Project Documentation Index
# Document version: 1.2
# Last updated: 2026-05-21

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
| Phase 5 | `phase5_frontend_pwa.md` | 🔄 In Progress | Progressive Web App — 5A+5B complete; 5C–5H planned |
| Phase 6 | `phase6_backend_extensions.md` | 📋 Planned | Backend extensions for Phase 5 supervisor, management, and notification modules |

**Session handoff:** `session_handoff_2026-05-15-continued.md` — most recent state snapshot

---

## Architecture Decision Records

| ADR | Document | Status | Decision |
|-----|----------|--------|----------|
| ADR-001 | `adr/ADR-001-Architecture.md` | Accepted | Single-app, single-datastore, single-region architecture |
| ADR-002 | `adr/ADR-002-RBAC.md` | Accepted | Group-based Azure AD RBAC + application-layer authorization |
| ADR-003 | `adr/ADR-003-Logging-and-Audit.md` | Accepted | Centralized Log Analytics + explicit audit events |
| ADR-004 | `adr/ADR-004-Terraform-Module-Structure.md` | Accepted | Modular Terraform organized by architectural responsibility |
| ADR-005 | `adr/ADR-005-Frontend-Architecture.md` | Accepted | React PWA, modular architecture, localStorage draft |
| ADR-006 | `adr/ADR-006-DDoS-Strategy.md` | 📋 Needed | DDoS Protection Standard cost/benefit tradeoff |

---

## Supporting Documents

| Document | Purpose |
|----------|---------|
| `Requirements.md` | Functional and non-functional requirements; project framing |
| `architecture.md` | Architecture diagram (Mermaid) with component relationships |
| `backlog.md` | **Canonical backlog** — all open items across backend, frontend, infra, and docs |
| `osi_security_review.md` | OSI layer-by-layer security analysis; coverage status and gap/action list |
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
| Compartments and line items (Phase 4) | ✅ Live | Alembic migrations applied |
| Expiration tracking (Phase 4) | ✅ Live | EXPIRED status on check line items |
| Frontend PWA — Phase 5A Foundation | ✅ Local | useAuth, useDraft, statusCalc, ErrorBoundary, UserPill, DevBanner |
| Frontend PWA — Phase 5B Check Wizard | ✅ Local | Steps 1–4, submitted screen, draft save/resume, all 5 check types |
| Frontend PWA — Phase 5C–5H | ❌ Not started | See backlog.md |
| Backend Phase 6 endpoints | ❌ Not started | See backlog.md |

### Test suite status

| Metric | Value |
|--------|-------|
| Backend tests | 90+ passing |
| Frontend unit tests | statusCalc (35), dateHelpers (14), useDraft (3) |
| Backend test gaps | TestCheckTypes class not yet written (see B-T1 in backlog.md) |

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
| Frontend | React 18 + Vite (PWA, no TypeScript) |
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
| localStorage offline draft | Never lose work mid-check; submit on completion only | ADR-005 |
| Modular React architecture | Module failures are isolated; app never fully crashes | ADR-005 |
| Validate button per item | Ensures every item is explicitly acknowledged | Phase 5 |
| Client-side CSV generation | No server-side export endpoint needed; simpler architecture | Phase 5 |
| UTF-8 BOM on CSV download | Ensures correct rendering in Excel without manual re-encoding | Phase 5 |
| Display-only role switching (crew mode) | No re-auth needed; JWT unchanged; UI hides irrelevant tools | Phase 5 |
