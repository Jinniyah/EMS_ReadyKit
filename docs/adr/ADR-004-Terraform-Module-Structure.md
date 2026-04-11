# ADR-004: Terraform Module Structure

**Status:** Accepted  
**Date:** 2026-04-11  
**Decision Owner:** EMS ReadyKit Project

---

## Context

EMS ReadyKit is intended to demonstrate **Infrastructure-as-Code (IaC) maturity**, not merely the ability to provision cloud resources.

The infrastructure must be:
- Fully reproducible and disposable
- Readable and reviewable
- Modular and reusable
- Secure and governed by default
- Aligned with enterprise and public-sector practices

Terraform was selected as the IaC tool, and its structure must reinforce:
- Separation of concerns
- Least-privilege access patterns
- Explicit architectural intent
- Cost and operational discipline

---

## Decision

Adopt a **modular Terraform architecture** organized by **architectural responsibility**, with a thin root module orchestrating well-defined, reusable child modules.

Key characteristics:
- One Terraform root per environment
- Independent, composable modules
- No hard-coded secrets
- Remote state backend
- Explicit inputs and outputs

Terraform modules map to **platform responsibilities**, not to domain entities such as vehicles or users.

---

## Terraform Directory Structure

```
terraform/
├── backend.tf
├── providers.tf
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── network/
│   ├── identity_rbac/
│   ├── policy/
│   ├── logging/
│   ├── app/
│   ├── data/
│   ├── storage/
│   └── siem/          # Optional
└── README.md
```

---

## Module Responsibilities

### network
Creates the virtual network baseline including subnets, NSGs, and traffic logging. Enforces a secure-by-default networking posture.

### identity_rbac
Defines Azure AD groups and group-based RBAC assignments. Implements the access model defined in ADR-002.

### policy
Defines and assigns Azure Policies enforcing required tags, region restrictions, and denial of public IPs.

### logging
Creates the Log Analytics workspace and configures diagnostic settings and retention limits. Implements ADR-003.

### app
Deploys the application hosting platform, managed identity, and Key Vault integration. Does not contain application code.

### data
Provisions the primary datastore with restricted network access and retention policies.

### storage
Creates blob storage for exports, artifacts, and supporting logs with lifecycle policies.

### siem (optional)
Deploys a Security Onion VM for detection validation only. Disabled by default.

---

## Alternatives Considered

### Single Flat Terraform Configuration
Rejected. Reduces clarity, reusability, and reviewability.

### Per-Domain or Per-Vehicle Infrastructure
Rejected. Vehicles are application-level concepts, not infrastructure tenants.

### Multiple Terraform Roots
Rejected. Adds unnecessary state management complexity.

---

## Consequences

### Positive
- Clear mapping between architecture and infrastructure
- Strong demonstration of IaC maturity
- Predictable deployments

### Tradeoffs
- Requires discipline to maintain module boundaries
- Slightly higher upfront structure

---

## Rationale

This Terraform structure reinforces architectural clarity, security discipline, and cost awareness. It mirrors real-world enterprise practices while remaining intentionally simple and defensible.

---

## Related ADRs

- ADR-001: Overall System Architecture
- ADR-002: Role-Based Access Control
- ADR-003: Logging and Audit Strategy

---

**Decision affirmed and approved.**
