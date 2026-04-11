# ADR-001: Overall System Architecture

**Status:** Accepted  
**Date:** 2026-04-11  
**Decision Owner:** EMS ReadyKit Project  

**Related Artifacts:**
- `docs/architecture.md` (Architecture Diagram)
- `Requirements.md`

---

## Context

EMS ReadyKit is a **non-production technical demonstration** designed to showcase cloud platform engineering judgment, Infrastructure-as-Code discipline, security-first thinking, and operational awareness within a realistic but constrained Fire & EMS domain.

The system models:
- A single EMS station
- A small, fixed vehicle fleet
- Vehicle-centric inventory and readiness workflows
- Strict auditability, especially for controlled substances

The project must be:
- Understandable at a glance
- Cost-controlled
- Fully reproducible
- Defensible during architectural review

The architecture must explicitly avoid over-engineering while still demonstrating professional-grade design decisions.

---

## Decision

Adopt a **simple, single-application, single-datastore architecture** deployed within a single Azure subscription, with **station-scoped resource isolation**, **group-based RBAC**, and **centralized logging**.

The system architecture consists of:
- One Web/API application responsible for all business logic
- One primary database for operational data
- Azure Active Directory-based authentication with group-scoped authorization
- Centralized logging via Log Analytics
- Optional SIEM integration (Security Onion) for detection validation
- Infrastructure fully provisioned and governed via Terraform

All resources are deployed in **one Azure region** and are treated as **disposable lab infrastructure**.

This architecture is visually documented in `docs/architecture.md`.

---

## Architecture Overview (Summary)

### Platform & Governance
- Azure Management Group for policy and RBAC inheritance
- Azure Policies enforcing:
  - Required tags
  - Allowed regions
  - Denial of public IP creation
- Azure Budget alerts for cost control

### Resource Organization
- One Azure subscription
- One **station-scoped resource group** containing:
  - Web/API application
  - Database
  - Key Vault
  - Storage account
- Virtual Network with segmented subnets:
  - Application
  - Data
  - Monitoring

### Identity & Access
- Authentication via Azure Active Directory
- Authorization via Azure AD groups
- No user-level role assignments
- Role scopes:
  - Global (Administrator)
  - Station-scoped (Supervisor)
  - Application-enforced vehicle scoping (Responder)

### Observability & Security
- Centralized application and audit logs in Log Analytics
- Explicit audit events for all material actions
- Optional log forwarding to a Security Onion VM for correlation and detection testing

---

## Alternatives Considered

### Microservices Architecture
**Rejected**

Microservices would increase operational complexity, cost, and failure modes without adding value for a small, tightly-scoped domain. A monolithic application better demonstrates architectural restraint and operational clarity.

---

### Multi-Region Deployment
**Rejected**

Multi-region architecture adds cost and complexity that are unjustified for a non-production, demonstration-scale system.

---

### Managed SIEM (Azure Sentinel)
**Rejected**

Fully managed SIEM solutions obscure detection logic, increase cost, and reduce hands-on validation signal. Security Onion provides transparency and explicit control suitable for this project.

---

### Per-Vehicle Infrastructure Isolation
**Rejected**

Vehicles are operational entities, not infrastructure tenants. Per-vehicle resource isolation would add cost and complexity without security benefit.

---

## Consequences

### Positive
- Clear and reviewable system design
- Low, predictable cost
- Fully reproducible via Terraform
- Strong alignment with real EMS operations
- High signal for portfolio and interview review

### Tradeoffs
- Limited scalability by design
- No production-grade high availability
- Not suitable for immediate production deployment

These tradeoffs are intentional and appropriate for project goals.

---

## Rationale

This architecture prioritizes:
- Clarity over cleverness
- Operational realism over theoretical scale
- Security and auditability over feature breadth
- Explicit tradeoffs over implicit assumptions

The resulting system:
- Can be explained quickly
- Can be defended deeply
- Demonstrates senior-level engineering judgment

---

## Related ADRs

- ADR-002: Role-Based Access Control Model
- ADR-003: Logging and Audit Strategy
- ADR-004: Terraform Module Structure

---

**Decision affirmed and approved.**
