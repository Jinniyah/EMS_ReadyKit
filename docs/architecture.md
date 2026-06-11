# EMS ReadyKit -- Architecture Overview
# Last updated: 2026-06-11 (Sessions A through T complete)

This document describes the high-level architecture for EMS ReadyKit, a
cloud-native inventory and vehicle readiness platform serving Newberg Township
EMS, Cass County, Michigan.

The design emphasizes:
- Simplicity -- single region, single datastore, single application
- Security by default -- Azure AD RBAC, managed identity, Key Vault, no secrets in code
- Centralized observability -- structured logging, Log Analytics, audit trail
- Cost discipline -- B1 App Service, free Static Web Apps tier, budget alerts
- Clear operational boundaries -- station membership enforced at application layer

---

## High-Level Architecture

```
+-----------------------------------------------------------+
|  Azure Active Directory                                   |
|  Group-Based RBAC -- Administrator / Supervisor /         |
|  Responder -- RS256 JWT tokens                            |
+-------------------------+---------------------------------+
                          | HTTPS + Bearer token
+-------------------------v---------------------------------+
|  Azure Static Web Apps                                    |
|  React 18 PWA -- mobile-first, MSAL authentication       |
|  Free tier; SWA routing; security headers                 |
+-------------------------+---------------------------------+
                          | HTTPS API calls
+-------------------------v---------------------------------+
|  Azure App Service B1 (Python 3.11)                       |
|  FastAPI + Gunicorn + UvicornWorker                       |
|  /api/v1: stations, vehicles, inventory, checks,          |
|           usage, repair requests, admin, audit            |
|                                                           |
|  +-------------------+  +-----------------------------+   |
|  |  Azure Key Vault  |  |  Log Analytics Workspace   |   |
|  |  Managed identity |  |  Structured audit log+KQL  |   |
|  +-------------------+  +-----------------------------+   |
+-------------------------+---------------------------------+
                          | Private connection
+-------------------------v---------------------------------+
|  Azure Database for PostgreSQL Flexible Server            |
|  24 Alembic migrations -- run automatically on startup    |
+-----------------------------------------------------------+
```

All infrastructure is provisioned via Terraform. No manual portal configuration.

---

## Component Responsibilities

| Component | Purpose |
|-----------|---------|
| **Azure Active Directory** | Identity provider; issues RS256 JWT tokens; three app roles: Administrator, Supervisor, Responder |
| **Azure Static Web Apps** | Hosts the React PWA; handles SWA routing and security headers (CSP, HSTS, X-Frame-Options); free tier |
| **Azure App Service B1** | Runs FastAPI + Gunicorn; 24 Alembic migrations auto-apply on startup; managed identity for Key Vault |
| **Azure Database for PostgreSQL** | Primary datastore; Alembic schema management (24 migrations); private connection from App Service |
| **Azure Key Vault** | Stores database credentials and application secrets; accessed via managed identity |
| **Log Analytics Workspace** | Receives structured application logs and audit events; 30-day retention |

---

## Authentication and Authorization Flow

```
User opens app
    -> MSAL authenticates against Azure AD
    -> Azure AD issues RS256 JWT with role claim (Administrator/Supervisor/Responder)
    -> React app stores token; Axios attaches it as Bearer on every API call
    -> FastAPI validates JWT signature against Azure AD JWKS endpoint
    -> require_role() dependency checks role claim
    -> require_station_membership() checks StationMember table for station-scoped endpoints
    -> Handler executes; check_date server-derived; performed_by bound from JWT (never client-supplied)
    -> write_audit_event() logs actor + action + entity to AuditEvent table (immutable)
```

---

## Networking Notes

The App Service runs on B1, which supports VNet integration. The VNet,
subnets, and private endpoint infrastructure are provisioned via Terraform and
ready to activate. Full VNet integration (private PostgreSQL connection, no
public database endpoint) requires enabling the VNet integration setting on the
App Service and adding a Private DNS Zone for
`privatelink.postgres.database.azure.com`.

The current deployment uses an Azure-services firewall rule on PostgreSQL
(only Azure-originating traffic permitted) as an interim measure. An Azure
Firewall module is tracked in the backlog (I-1) for future hardening.

See ADR-001 (`docs/adr/ADR-001-Architecture.md`) for the full architecture
rationale and ADR-004 (`docs/adr/ADR-004-Terraform-Module-Structure.md`) for
the IaC structure.

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Single region | Domain size and volunteer crew footprint do not justify geo-redundancy cost |
| Single datastore (PostgreSQL) | No polyglot persistence needed; SQLAlchemy + Alembic handle the schema cleanly |
| React PWA (not native app) | No app store distribution required; PWA installable on iOS and Android; single codebase |
| Azure Static Web Apps | Free tier sufficient; built-in global CDN; SWA routing handles PWA deep links |
| Station membership at application layer | Azure AD groups handle role; application layer handles station assignment -- more flexible than one AD group per station |
| Audit events in PostgreSQL | Co-located with operational data; queryable via SQL; no additional service required |
| B1 App Service | Always-on (no cold starts); VNet-capable; single Terraform variable to scale |
| Security headers split between API and SWA | X-Frame-Options on SWA only (MSAL iframe compatibility); content headers on API middleware |
| Rate limiting via slowapi | Protects check creation endpoint; TESTING env var raises limit in test suite |
| Build zip on Linux in CI | Windows Compress-Archive creates backslash paths that Oryx cannot extract |

For full decision records, see `docs/adr/`.
