# EMS ReadyKit — Phase 1: Platform Foundation
# Document version: 1.0
# Status: Complete
# Last updated: 2026-05-15

---

## 1. Executive Summary

Phase 1 established the cloud infrastructure foundation for EMS ReadyKit using
Infrastructure-as-Code (IaC) principles. All Azure resources required to host,
secure, and observe the application were provisioned via Terraform before a
single line of application code was written. This phase produced a reproducible,
auditable, cost-governed platform that subsequent phases build upon.

---

## 2. Objectives

| Objective | Description |
|-----------|-------------|
| IaC foundation | All infrastructure defined and managed by Terraform; zero manual portal configuration |
| Network baseline | Segmented virtual network with restrictive NSGs and subnet isolation |
| Identity framework | Azure AD groups and group-based RBAC ready for application onboarding |
| Governance | Azure Policy enforcement for tags, regions, and public IP controls |
| Observability | Centralized Log Analytics workspace with diagnostic routing |
| Cost controls | Budget alerts, short log retention, right-sized compute |
| Reproducibility | Environment is fully disposable and re-creatable from source |

---

## 3. Scope

### In scope
- Azure subscription configuration
- Management group hierarchy
- Terraform module structure (network, identity_rbac, policy, logging, app, data, storage, siem)
- Virtual network with three subnets (application, data, monitoring)
- Network Security Groups with restrictive defaults
- Azure AD groups for Administrator, Supervisor, and Responder roles
- Group-based RBAC assignments at subscription and resource group scopes
- Azure Policy: required tags, allowed regions, deny public IP
- Log Analytics workspace with diagnostic settings
- Azure App Service (F1 tier for development; B1 target for production)
- Azure Database for PostgreSQL Flexible Server
- Azure Key Vault with managed identity integration
- Azure Blob Storage account
- Budget alert at $75/month threshold
- Remote Terraform state backend

### Out of scope
- Application code deployment (Phase 2)
- Authentication configuration (Phase 3)
- CI/CD pipeline (Phase 3)
- Security Onion SIEM (optional, deferred)

---

## 4. Technical Decisions

### 4.1 Terraform modular architecture
All infrastructure organized into eight responsibility-aligned modules:
`network`, `identity_rbac`, `policy`, `logging`, `app`, `data`, `storage`, `siem`.
Each module has explicit inputs, outputs, and a single responsibility.
Thin root module orchestrates all modules with no business logic.

**Rationale:** Mirrors enterprise IaC practices. Each module is independently
reviewable and reusable. Flat configurations are rejected as they reduce
clarity and increase change blast radius.

Reference: ADR-004 — Terraform Module Structure

### 4.2 Single-region, single-subscription deployment
All resources deployed in one Azure region (North Central US) within one subscription.

**Rationale:** Multi-region adds cost and complexity unjustified for a
demonstration system. Single-region deployment is explicitly documented as a
known tradeoff, not an oversight.

Reference: ADR-001 — Overall System Architecture

### 4.3 Group-based RBAC (no user-level role assignments)
Three Azure AD groups provisioned (ems-readykit-administrators,
ems-readykit-supervisors, ems-readykit-responders). Role assignments target
groups exclusively.

**Rationale:** User-level role assignments are operationally unscalable and
difficult to audit. Group-based assignments reflect real enterprise and
public-sector identity management practices.

Reference: ADR-002 — Role-Based Access Control Model

### 4.4 App Service tier
Development: F1 (free tier). Known limitation: no VNet integration, no
Always On. Private endpoint infrastructure provisioned and ready for upgrade.

**Rationale:** F1 eliminates compute cost during development. SKU upgrade to
B1 is a single Terraform variable change. Architecture is not compromised.

### 4.5 PostgreSQL over SQL Server
Azure Database for PostgreSQL Flexible Server selected over Azure SQL.

**Rationale:** Open-source alignment with FastAPI/SQLAlchemy stack. Lower cost
at comparable performance for this workload. No vendor lock-in.

---

## 5. Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| Terraform modules (8) | `iac/Terraform/modules/` | ✅ Complete |
| Root Terraform configuration | `iac/Terraform/main.tf` | ✅ Complete |
| Remote state backend | Azure Blob Storage | ✅ Complete |
| Azure AD groups + RBAC | Via identity_rbac module | ✅ Complete |
| Azure Policy assignments | Via policy module | ✅ Complete |
| Log Analytics workspace | Via logging module | ✅ Complete |
| Network (VNet + subnets + NSGs) | Via network module | ✅ Complete |
| App Service + Key Vault | Via app module | ✅ Complete |
| PostgreSQL Flexible Server | Via data module | ✅ Complete |
| Budget alert | Via root module | ✅ Complete |
| Architecture diagram | `docs/architecture.md` | ✅ Complete |
| Architecture Decision Records | `docs/adr/` | ✅ Complete (ADR-001 through ADR-004) |
| Deployment runbook | `docs/runbook.md` | ✅ Complete |

---

## 6. Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Overall System Architecture | Accepted |
| ADR-002 | Role-Based Access Control Model | Accepted |
| ADR-003 | Logging and Audit Strategy | Accepted |
| ADR-004 | Terraform Module Structure | Accepted |

---

## 7. Testing and Validation

| Validation | Method | Result |
|------------|--------|--------|
| Terraform plan | `terraform plan` — no unexpected resources | ✅ Pass |
| Terraform apply | `terraform apply` — zero errors | ✅ Pass |
| Policy compliance | Azure Policy compliance view | ✅ Compliant |
| RBAC validation | Group assignments verified, no user-level assignments | ✅ Pass |
| Log Analytics | Basic KQL query returns results | ✅ Pass |
| Network baseline | NSGs reviewed, flow logs enabled | ✅ Pass |
| Budget alert | Configured at $75/month | ✅ Pass |

---

## 8. Known Issues and Tradeoffs

| Item | Detail | Resolution |
|------|--------|------------|
| F1 tier — no VNet integration | Public internet path between App Service and database | Upgrade to B1 to enable VNet integration. Private endpoints provisioned and ready. |
| F1 tier — no Always On | App cold-starts after idle | Upgrade to B1 resolves. Acceptable for development. |
| Single region | No geo-redundancy | Documented as intentional. Non-production system. |
| Short log retention | 7–14 days default | Appropriate for cost-controlled demo. Increase for production. |

---

## 9. Phase Dependencies

| Dependency | Direction |
|------------|-----------|
| Phase 2 (Backend API) | Requires: App Service, PostgreSQL, Key Vault, Log Analytics from Phase 1 |
| Phase 3 (Auth & CI/CD) | Requires: Azure AD App Registration and RBAC from Phase 1 |
| Phase 5 (Frontend) | Requires: Azure Static Web Apps module (added in Phase 5) |

---

## 10. Cost Summary

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| App Service (F1) | $0 (free tier) |
| PostgreSQL Flexible Server | ~$12–$18 |
| Log Analytics | ~$5–$15 |
| Key Vault | ~$1–$3 |
| Storage account | ~$1–$3 |
| Azure AD / RBAC / Policy | $0 |
| Budget alert | $0 |
| **Total estimate** | **~$19–$39/month** |

---

## 11. Next Phase

Phase 2 — Backend API: FastAPI application with data models, database
migrations, business logic, and REST endpoints.
